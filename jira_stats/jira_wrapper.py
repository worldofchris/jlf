"""
Wrapper around the JIRA API to allow us to categorize issues by
project/component/label etc

Also abstracts away from batch searching and other implementation
details we don't want to present to the user.
"""

import jira.client
import sys

from datetime import date, timedelta, datetime
from dateutil import rrule

import pandas as pd
import numpy as np

"""States between which we consider an issue to be being worked on
   for the purposes of calculating cycletime"""

START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'


def fill_in_blanks(index):

    index_list = index.tolist()

    start_date = datetime.strptime(index_list[0][:10], '%Y-%m-%d')
    end_date = datetime.strptime(index_list[-1][:10], '%Y-%m-%d')

    num_weeks = rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=end_date).count()

    new_index = [week_start_date((start_date + timedelta(weeks=i)).year,
                                 (start_date + timedelta(weeks=i)).isocalendar()[1]).strftime('%Y-%m-%d') for i in range(0, num_weeks)]

    return new_index


def week_start_date(year, week):
    """
    Taken from http://stackoverflow.com/a/1287862/1064619
    """
    d = date(year, 1, 1)
    delta_days = d.isoweekday() - 1
    delta_weeks = week
    if year == d.isocalendar()[0]:
        delta_weeks -= 1
    delta = timedelta(days=-delta_days, weeks=delta_weeks)
    return d + delta


def get_cycle_time(histories, start_state=START_STATE, end_state=END_STATE, reopened_state=REOPENED_STATE):
    """Calculate how long it has taken an issue to get from START_STATE
       to END_STATE"""

    start_date = None
    end_date = None

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                new_start_date = None

                if item.toString == start_state:

                    new_start_date = datetime.strptime(history.created[:10], '%Y-%m-%d')

                if item.fromString == start_state:

                    new_start_date = datetime.strptime(history.created[:10], '%Y-%m-%d')

                if new_start_date is not None:

                    if start_date is None:
                        start_date = new_start_date
                    else:
                        if new_start_date < start_date:
                            start_date = new_start_date

                if item.toString == end_state:

                    # We ignore transitions to end_state if they are from reopened.
                    # This is because we sometime have to re-open tickets just to fix
                    # details of ownership, component, type or resolution.
                    if item.fromString != reopened_state:
                        end_date = datetime.strptime(history.created[:10], '%Y-%m-%d')

    if start_date is None or end_date is None:
        return None

    return ((end_date - start_date).days) + 1


def get_time_in_states(histories, from_date, until_date):
    """
    How long did an issue spend in each state in its history.

    For the first state it was in count 'from' the start of the period we
    are interested in, typically when the issue was created

    For the last state it was in count from the time the state was entered
    until the date specified in 'until' - typically today's date
    """

    time_in_states = []

    current_state = None
    prev_state_change_date = from_date.date()

    for history in histories:
        for item in history.items:
            if item.field == 'status':
                                
                state_change_date = datetime.strptime(history.created[:10], '%Y-%m-%d').date()

                days_in_state = state_change_date - prev_state_change_date

                if current_state is None:
                    current_state = item.fromString

                time_in_states.append({'state': current_state,
                                       'days': days_in_state.days})

                current_state = item.toString
                prev_state_change_date = state_change_date

    final_state_days = until_date - prev_state_change_date

    time_in_states.append({'state': current_state,
                           'days':  final_state_days.days})

    return time_in_states


class JiraIssues(object):
    """
    A set of categorised issues from which we can extract our standard metrics
    """

    def __init__(self, jira, categories, cycles, types):

        self.jira = jira
        self.categories = categories
        self.cycles = cycles
        self.types = types

        self.done_issues = None
        self.ongoing_issues = None

    def get_issues_from_jira(self, jira, filter=None, filter_by_category=None):
        """
        Get the actual issues out of jira
        """

        batch_size = 100
        issues = []

        for category in self.categories:

            if filter_by_category is not None:

                if category != filter_by_category:
                    continue

            n = 0
            while 1:

                jql = self.categories[category]
                if filter is not None:
                    jql = jql + filter

                issue_batch = jira.search_issues(jql,
                                                 startAt=n,
                                                 maxResults=batch_size,
                                                 expand='changelog')

                if issue_batch is None:
                    #TODO: Fix mocking so we can get rid of this.
                    # 'expand' seems to have some magic meaning in Mockito...
                    issue_batch = jira.search_issues(jql,
                                                     startAt=n,
                                                     maxResults=batch_size)

                for issue in issue_batch:

                    issue.category = category
                    try:
                        for cycle in self.cycles:
                            setattr(issue, cycle, get_cycle_time(issue.changelog.histories,
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

    def issues_as_rows(self, issues):

        issue_rows = []

        for issue in issues:
            f = issue.fields

            resolution_date_str = f.resolutiondate

            if resolution_date_str is not None:
                resolution_date = datetime.strptime(resolution_date_str[:10], '%Y-%m-%d')

                week = week_start_date(resolution_date.isocalendar()[0],
                                       resolution_date.isocalendar()[1]).strftime('%Y-%m-%d')

            else:

                week = None

            time_in_states = get_time_in_states(issue.changelog.histories, 
                                                datetime.strptime(f.created[:10], '%Y-%m-%d'),
                                                date.today())

            since = time_in_states[-1]['days']

            issue_row = {'swimlane':   issue.category,
                         'id':         issue.key,
                         'name':       f.summary,
                         'project':    f.project.name,
                         'type':       f.issuetype.name,
                         'components': [],
                         'week':       week,
                         'since':      since}

            for cycle in self.cycles:
                issue_row[cycle] = getattr(issue, cycle)

            for component in f.components:
                issue_row['components'].append(component.name)

            issue_rows.append(issue_row)

        return issue_rows

    @property
    def ongoing(self):
        """
        All issues that are still in flight
        """
        if self.ongoing_issues is None:
            self.ongoing_issues = self.get_issues_from_jira(self.jira)

        issue_rows = self.issues_as_rows(self.ongoing_issues)
        df = pd.DataFrame(issue_rows)
        return df

    @property
    def done(self):
        """
        All issues that have been completed
        """
        if self.done_issues is None:
            assert False, "Need to go and get these..."

        issue_rows = self.issues_as_rows(self.done_issues)
        df = pd.DataFrame(issue_rows)
        return df

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

            """
            We want to exclude subtasks and anything that was not resolved as fixed
            """
            counts_towards_throughput = ' AND issuetype in standardIssueTypes() AND resolution = Fixed AND status in (Resolved, Closed)'
            self.done_issues = self.get_issues_from_jira(self.jira,
                                                         counts_towards_throughput,
                                                         category)

        issue_rows = []

        for issue in self.done_issues:
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

            reindexed = table.reindex(index=fill_in_blanks(table.index), fill_value=np.int64(0))
            noncum = reindexed.fillna(0)
            if cumulative:
                cumtab = noncum.cumsum(axis=0)

                # For some readon the name of the index gets blown away by the reindex
                cumtab.index.name = table.index.name

                return cumtab

            else:

                return noncum

        else:

            return None


class JiraWrapper(object):
    """
    Wrapper around our JIRA instance
    """

    def __init__(self, config):

        self.issue_collection = None

        self.jira = jira.client.JIRA({'server': config['server']},
                                     basic_auth=(config['username'], config['password']))

        self.categories = None
        self.cycles = None
        self.types = None

        try:
            self.categories = config['categories']
            self.cycles = config['cycles']
            self.types = config['types']
        except KeyError:
            pass

    def issues(self):
        """
        Issues for a given set of categories or all if no categories specified
        """
        if self.issue_collection is None:
            self.issue_collection = JiraIssues(self.jira,
                                   self.categories,
                                   self.cycles,
                                   self.types)

        return self.issue_collection
