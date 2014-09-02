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
from history import time_in_states, cycle_time, arrivals
from bucket import bucket_labels

from collections import Counter

class MissingState(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class MissingConfigItem(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class JiraWrapper(object):
    """
    Wrapper around our JIRA instance
    """

    def __init__(self, config):

        self.jira = jira.client.JIRA({'server': config['server']},
                                     basic_auth=(config['username'], config['password']))

        self.categories = None
        self.cycles = None
        self.types = None
        self.ongoing_states = None
        self.states = []

        try:
            self.categories = config['categories']
            self.cycles = config['cycles']
            self.types = config['types']
        except KeyError as e:
            raise MissingConfigItem(e, "Missing Config Item:{0}".format(e))
        try:
            self.counts_towards_throughput = config['counts_towards_throughput']
        except KeyError:
            self.counts_towards_throughput = ' AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)'

        # Optional

        try:
            self.ongoing_states = config['ongoing']
        except KeyError:
            pass

        try:
            self.states = config['states']
            self.states.append(None)
        except KeyError:
            pass

        self.done_issues = None
        self.ongoing_issues = None
        self.all_issues = None
        self.issue_history = None

    def __str__(self):
        issues_as_string = "Jira Issues\ndone:\n{done}\nongoing:\n{ongoing}". format(done=self.done,
                                                                                     ongoing=self.ongoing)
        return issues_as_string

    @property
    def ongoing(self):
        """
        All issues that are still in flight
        """
        if self.ongoing_issues is None:
            self._populate_ongoing_issues_from_jira()

        issue_rows = self._issues_as_rows(self.ongoing_issues)
        df = pd.DataFrame(issue_rows)
        return df

    def done(self):
        """
        All issues that have been completed
        """
        if self.done_issues is None:
            self._populate_done_issues_from_jira()

        issue_rows = self._issues_as_rows(self.done_issues) 
        df = pd.DataFrame(issue_rows)
        return df

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

                    dates = [ created_date + timedelta(days=x) for x in range(0, total_days) ]

                    try:
                        history[issue.key] = pd.Series(issue_day_history, index=dates)
                    except AssertionError as e:
                        print e
                        print dates
                        print issue_day_history

                except AttributeError as e:
                    print e

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
                """
                Order of states for CFD.
                TODO: take from config
                """
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

        # Does ongoing exclude done in its query?
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
        Return the throughput for our issues
        """

        if self.done_issues is None:
            self._populate_done_issues_from_jira()

        issue_rows = []

        for issue in self.done_issues:
            if category is not None:
                if category != issue.category:
                    continue
            f = issue.fields

            resolution_date_str = f.resolutiondate

            if resolution_date_str is not None:

                resolution_date = datetime.strptime(resolution_date_str[:10], '%Y-%m-%d')

                if (resolution_date.date() >= from_date) and (resolution_date.date() <= to_date):

                    swimlane = issue.category

                    # Are we grouping by work type?

                    if types is not None:
                        for type_grouping in types:
                            if f.issuetype.name in self.types[type_grouping]:
                                swimlane = swimlane + '-' + type_grouping
                            else:
                                pass # print "Not counting " + f.issuetype.name 

                    issue_row = {'swimlane':   swimlane,
                                 'id':         issue.key,
                                 'week':       week_start_date(resolution_date.isocalendar()[0],
                                                               resolution_date.isocalendar()[1]).strftime('%Y-%m-%d'),
                                 'project':    f.project.name,
                                 'type':       f.issuetype.name,
                                 'components': [],
                                 'count':      1}

                    for component in f.components:
                        issue_row['components'].append(component.name)

                    issue_rows.append(issue_row)

        df = pd.DataFrame(issue_rows)

        if len(df.index) > 0:

            table = pd.tools.pivot.pivot_table(df, rows=['week'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

            reindexed = table.reindex(index=fill_date_index_blanks(table.index), fill_value=np.int64(0))
            noncum = reindexed.fillna(0)
            if cumulative:
                cumtab = noncum.cumsum(axis=0)

                # For some reason the name of the index gets blown away by the reindex
                cumtab.index.name = table.index.name

                return cumtab

            else:

                return noncum

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
            except AttributeError:
                pass

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
                    try:
                        for cycle in self.cycles:
                            setattr(issue,
                                    cycle,
                                    cycle_time(issue.changelog.histories,
                                               start_state=self.cycles[cycle]['start'],
                                               end_state=self.cycles[cycle]['end'],
                                               reopened_state=self.cycles[cycle]['ignore']))

                    except AttributeError:

                        pass

                    issues.append(issue)

                if len(issue_batch) < batch_size:
                    break
                n += batch_size
                sys.stdout.write('.')
                sys.stdout.flush()

        return issues

    def _populate_ongoing_issues_from_jira(self):
        filter = 'and (status in ({status_list})) and issuetype in standardIssueTypes()'.format(status_list = ', '.join('"{status}"'.format(status=status) for status in self.ongoing_states))
        self.ongoing_issues = self._issues_from_jira(filter=filter)

    def _populate_done_issues_from_jira(self):

        """
        We want to exclude subtasks and anything that was not resolved as fixed
        """
        self.done_issues = self._issues_from_jira(filter=self.counts_towards_throughput)

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

                for component in f.components:
                    if issue_row['components'] is None:
                        issue_row['components'] = []
                    issue_row['components'].append(component.name)

                issue_rows.append(issue_row)

        return issue_rows
