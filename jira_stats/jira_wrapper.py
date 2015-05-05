"""
Wrapper around the JIRA API to allow us to categorize issues by
project/component/label etc and report on:

- Work in Progress
- Work completed - including Cycle Time
- Work history
- Cumulative Flow
- Throughput
- Rate at which types of work are created

Also abstracts away from batch searching and other implementation
details we don't want to present to the user.
"""

import jira.client
import sys

from datetime import date, timedelta, datetime

import pandas as pd
import numpy as np
import math

from index import fill_date_index_blanks, week_start_date
from history import time_in_states, cycle_time, arrivals, history_from_jira_changelog
from bucket import bucket_labels

from collections import Counter


class MissingState(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

    def __str__(self):

        return self.msg


class MissingConfigItem(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

    def __str__(self):

        return self.msg


class JiraWrapper(object):
    """
    Wrapper around our JIRA instance
    """

    def __init__(self, config):

        authentication = None

        try:
            authentication = config['authentication']
        except KeyError as e:
            raise MissingConfigItem(e, "Missing Config Item:{0}".format(e))

        self.jira = None

        if 'username' in authentication and 'password' in authentication:
            self.jira = jira.client.JIRA({'server': config['server']},
                                         basic_auth=(authentication['username'], 
                                                     authentication['password']))
        elif ('access_token' in authentication and
              'access_token_secret' in authentication and
              'consumer_key' in authentication and
              'key_cert'):

            try:
                with open(authentication['key_cert'], 'r') as key_cert_file:
                    key_cert_data = key_cert_file.read()
            except IOError:
                raise MissingConfigItem('key_cert', "key_cert not found:{0}". format(authentication['key_cert']))

            self.jira = jira.client.JIRA({'server': config['server']},
                                         oauth={'access_token': authentication['access_token'],
                                                'access_token_secret': authentication['access_token_secret'],
                                                'consumer_key': authentication['consumer_key'],
                                                'key_cert': key_cert_data})
        else:
            raise MissingConfigItem('authentication', "Authentication misconfigured")

        self.categories = None
        self.cycles = None
        self.types = None
        self.states = []

        if 'throughput_dow' in config:
            self.throughput_dow = config['throughput_dow']
        else:
            self.throughput_dow = 4

        try:
            self.categories = config['categories']
            self.cycles = config['cycles']
            self.types = config['types']
            self.counts_towards_throughput = config['counts_towards_throughput']
        except KeyError as e:
            raise MissingConfigItem(e.message, "Missing Config Item:{0}".format(e.message))

        # Optional

        try:
            self.states = config['states']
            self.states.append(None)
        except KeyError:
            pass

        self.all_issues = None
        self.issue_history = None

    def issue(self, key):
        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        matches = [issue for issue in self.all_issues if issue.key == key]
        return matches[0]

    def issues(self, fields=None):
        """
        All issues
        """
        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        issue_rows = self._issues_as_rows(self.all_issues)
        df = pd.DataFrame(issue_rows)

        if fields is None:
            return df
        else:
            return df.filter(fields)

    def history(self, from_date=None, until_date=None):

        if self.issue_history is None:

            if self.all_issues is None:
                self.all_issues = self._issues_from_jira()

            history = {}

            for issue in self.all_issues:

                created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')

                try:

                    issue_history = time_in_states(issue.changelog.histories, from_date=created_date, until_date=until_date)

                    issue_day_history = []
                    total_days = 0

                    for state_days in issue_history:

                        state = state_days['state']
                        days = state_days['days']

                        days_in_state = [state] * days

                        issue_day_history += days_in_state
                        total_days += days

                    dates = [created_date + timedelta(days=x) for x in range(0, total_days)]

                    try:
                        history[issue.key] = pd.Series(issue_day_history, index=dates)
                    except AssertionError as e:
                        print e
                        print dates
                        print issue_day_history

                except AttributeError as e:
                    pass

            self.issue_history = history

        df = pd.DataFrame(self.issue_history)

        return df

    def cfd(self, from_date=None, until_date=None):
        """
        Cumulative Flow Diagram
        """

        if self.issue_history is None:

            self.history(from_date, until_date)

        cfd = pd.DataFrame(self.issue_history)

        days = {}

        for day in cfd.index:
            tickets = []
            for ticket in cfd.ix[day]:
                tickets.append(ticket)

            def state_order(state):

                try:
                    return self.states.index(state)
                except ValueError:
                    if type(state) == float:
                        if math.isnan(state):
                            return -1
                    if type(state) == np.float64:
                        if math.isnan(state):
                            return -1

                    raise MissingState(state, "Missing state:{0}".format(state))

            days[day] = sorted(tickets, key=state_order)

        return pd.DataFrame(days)

    def demand(self,
               from_date,
               to_date,
               types=None):
        """
        Return the number of issues created each week - i.e. the demand on the system
        """

        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        issue_rows = self._issues_as_rows(self.all_issues, types)

        df = pd.DataFrame(issue_rows)
        table = pd.tools.pivot.pivot_table(df, rows=['week_created'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

        reindexed = table.reindex(index=fill_date_index_blanks(table.index), fill_value=np.int64(0))
        return reindexed

    def throughput(self,
                   from_date,
                   to_date,
                   cumulative=True,
                   category=None,
                   types=None):
        """
        Return throughput for all issues in a state where they are considered
        to count towards throughput.

        Might want to add some additional conditions other than state but state
        allows us the most options as to where to place the 'finishing line'
        """

        if self.issue_history is None:
            self.history(from_date, to_date)

        issue_rows = []

        for issue_key in self.issue_history:

            issue = self.issue(issue_key)

            if category is not None:

                if category != issue.category:
                    continue

            swimlane = issue.category

            # Are we grouping by work type?
            f = issue.fields

            if types is not None:
                for type_grouping in types:
                    if f.issuetype.name in self.types[type_grouping]:
                        swimlane = swimlane + '-' + type_grouping
                    else:
                        pass
                        # print "Not counting " + f.issuetype.name

            for day, state in self.issue_history[issue_key].iteritems():
                if day.weekday() == self.throughput_dow:

                    if state in self.counts_towards_throughput:

                        issue_row = {'swimlane': swimlane,
                                     'id':       issue_key,
                                     'week':     day,
                                     'count':    1}
                        issue_rows.append(issue_row)

        df = pd.DataFrame(issue_rows)

        if len(df.index) > 0:

            table = pd.tools.pivot.pivot_table(df, rows=['week'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

            if cumulative:
                return table

            else:

                def foo_func(x):
                    for i in range(x.size-1, 0, -1):
                        x[i] = x[i] - x[i-1]
                    return x

                table = table.apply(foo_func)

                return table

        else:

            return None

    def arrival_rate(self,
                     from_date,
                     to_date):
        """
        So that we can get an idea of the flow of work that has not been completed and so does not have a resolution date
        and so does not count towards throughput, what is the rate at which that work arrived at states further up the 
        value chain?
        """

        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        arrivals_count = {}

        for issue in self.all_issues:
            try:
                arrivals_count = arrivals(issue.changelog.histories, arrivals_count)
            except AttributeError as e:
                print e

        df = pd.DataFrame.from_dict(arrivals_count, orient='index')
        df.index = pd.to_datetime(df.index)
        wf = df.resample('W-MON', how='sum')

        return wf

    def cycle_time_histogram(self,
                             cycle,
                             types=None,
                             buckets=None):
        """
        Time taken for work to complete one or more 'cycles' - i.e. transitions from a start state to an end state
        """

        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        rows = self._issues_as_rows(self.all_issues)

        cycle_time_data = {}

        for row in rows:

            if types is not None:

                include = False

                for type_grouping in types:

                    if row['type'] in self.types[type_grouping]:
                        include = True
                        key = "{0}-{1}".format(type_grouping, cycle)
                        break

                if not include:
                    continue

            else:
                key = cycle

            try:
                if row[cycle] is not None:
                    if key not in cycle_time_data:
                        cycle_time_data[key] = [row[cycle]]
                    else:
                        cycle_time_data[key].append(row[cycle])
            except KeyError:
                continue

        histogram = None

        for cycle in cycle_time_data:
            if buckets is not None:

                try:
                    li = buckets.index('max')
                    buckets[li] = max(cycle_time_data[cycle])

                except ValueError:
                    pass

                labels = bucket_labels(buckets)
                count, division = np.histogram(cycle_time_data[cycle], bins=buckets)
            else:

                count, division = np.histogram(cycle_time_data[cycle])
                labels = bucket_labels(division)

            cycle_histogram = pd.DataFrame(count, index=labels, columns=[cycle])
            cycle_histogram.index.name = 'bucket'

            if histogram is None:
                histogram = cycle_histogram.copy(deep=True)
            else:
                old_histogram = histogram.copy(deep=True)
                histogram = old_histogram.join(cycle_histogram, how='outer')

        return histogram

    def totals(self):
        """
        What are current totals of work in our various states
        """

        # We can get this by doing a count of the last day of the CFD

        cfd = self.cfd()

        return None


###############################################################################
# Internal methods
###############################################################################

    def _issues_from_jira(self, filter=None):
        """
        Get the actual issues from Jira itself via the Jira REST API
        """

        batch_size = 100
        issues = []

        for category in self.categories:

            n = 0
            while 1:

                jql = self.categories[category]
                if filter is not None:
                    jql = jql + filter

                issue_batch = self.jira.search_issues(jql,
                                                      startAt=n,
                                                      maxResults=batch_size,
                                                      expand='changelog')

                if issue_batch is None:
                    #TODO: Fix mocking so we can get rid of this.
                    # 'expand' seems to have some magic meaning in Mockito...
                    issue_batch = self.jira.search_issues(jql,
                                                          startAt=n,
                                                          maxResults=batch_size)

                for issue in issue_batch:

                    issue.category = category

                    created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')
                    if issue.changelog is not None:
                        issue.history = history_from_jira_changelog(issue.changelog, created_date)

                    try:
                        for cycle in self.cycles:
                            reopened_state = None
                            after_state = None
                            start_state = None

                            if 'ignore' in self.cycles[cycle]:
                                reopened_state = self.cycles[cycle]['ignore']

                            if 'after' in self.cycles[cycle]:
                                after_state = self.cycles[cycle]['after']

                            if 'start' in self.cycles[cycle]:
                                start_state = self.cycles[cycle]['start']

                            if 'exit' in self.cycles[cycle]:

                                setattr(issue,
                                        cycle,
                                        cycle_time(issue.history,
                                                   start_state=start_state,
                                                   after_state=after_state,
                                                   exit_state=self.cycles[cycle]['exit'],
                                                   reopened_state=reopened_state))
                            else:
                                setattr(issue,
                                        cycle,
                                        cycle_time(issue.history,
                                                   start_state=start_state,
                                                   after_state=after_state,
                                                   end_state=self.cycles[cycle]['end'],
                                                   reopened_state=reopened_state))

                    except AttributeError:

                        pass

                    issues.append(issue)

                if len(issue_batch) < batch_size:
                    break
                n += batch_size
                sys.stdout.write('.')
                sys.stdout.flush()

        return issues

    def _issues_as_rows(self, issues, types=None):

        """
        Get issues into a state where we can stick them into a Pandas dataframe
        """

        # TODO: Decide if this should be a class / helper method?
        # TODO: See if has any overlap with throughput function

        issue_rows = []

        for issue in issues:
            f = issue.fields

            resolution_date_str = f.resolutiondate

            if resolution_date_str is not None:
                resolution_date = datetime.strptime(resolution_date_str[:10],
                                                    '%Y-%m-%d')

                week = week_start_date(resolution_date.isocalendar()[0],
                                       resolution_date.isocalendar()[1]).strftime('%Y-%m-%d')

            else:

                week = None

            date_created = datetime.strptime(f.created[:10], '%Y-%m-%d')
            week_created = week_start_date(date_created.isocalendar()[0],
                                           date_created.isocalendar()[1]).strftime('%Y-%m-%d')

            if issue.changelog is not None:
                tis = time_in_states(issue.changelog.histories,
                                     datetime.strptime(f.created[:10],
                                                       '%Y-%m-%d'),
                                     date.today())

                since = tis[-1]['days']

            else:

                since = None

            include = True

            # TODO: This looks like a bit of a hack.
            # Can we do without iterating over loop, seeing as we
            # only ever want one swimlane/category combination?

            swimlane = issue.category

            if types is not None and self.types is not None:
                include = False
                for type_grouping in types:
                    if f.issuetype.name in self.types[type_grouping]:
                        swimlane = swimlane + '-' + type_grouping
                        include = True

            if include:

                try:
                    story_points = f.customfield_10002
                except AttributeError:
                    story_points = None

                try:
                    epic_link = f.customfield_10200
                except AttributeError:
                    epic_link = None

                # TODO: Fields need to come out of config too.

                issue_row = {'swimlane':     swimlane,
                             'type':         f.issuetype.name,
                             'id':           issue.key,
                             'name':         f.summary,
                             'status':       f.status.name,
                             'project':      f.project.name,
                             'components':   None,
                             'week':         week,
                             'since':        since,
                             'created':      f.created,
                             'week_created': week_created,
                             'story_points': story_points,
                             'epic_link':    epic_link,
                             'count':        1}

                for cycle in self.cycles:
                    try:
                        issue_row[cycle] = getattr(issue, cycle)
                    except AttributeError:
                        pass

                components = []

                for component in f.components:
                    components.append(component.name)

                issue_row['components'] = ",".join(components)

                issue_rows.append(issue_row)

        return issue_rows
