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


class JiraIssues(object):
    """
    A set of categorised issues from which we can extract our standard metrics
    """

    def __init__(self, jira, categories, cycles):

        self.jira = jira
        self.categories = categories
        self.cycles = cycles

        self.queued = None
        self.wip = None
        self.done = None

    def get_issues(self, jira, filter, filter_by_category=None):
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
                jql = self.categories[category] + filter

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

    @property
    def issues(self):

        issue_rows = []

        for issue in self.done:
            f = issue.fields

            resolution_date_str = f.resolutiondate
            resolution_date = datetime.strptime(resolution_date_str[:10], '%Y-%m-%d')

            issue_row = {'swimlane':   issue.category,
                         'id':         issue.key,
                         'name':       f.summary,
                         'project':    f.project.name,
                         'type':       f.issuetype.name,
                         'components': [],
                         'week':       week_start_date(resolution_date.isocalendar()[0],
                                       resolution_date.isocalendar()[1]).strftime('%Y-%m-%d')}

            for cycle in self.cycles:
                issue_row[cycle] = getattr(issue, cycle)

            for component in f.components:
                issue_row['components'].append(component.name)

            issue_rows.append(issue_row)

        df = pd.DataFrame(issue_rows)

        return df

    def throughput(self, from_date, to_date, cumulative=True, category=None):
        """
        Return the throughput for our issues
        """

        if self.done is None:

            jql = ' AND issuetype in standardIssueTypes() AND resolution = Fixed AND status in (Resolved, Closed)'
            self.done = self.get_issues(self.jira, jql, category)

        issue_rows = []

        for issue in self.done:
            f = issue.fields

            resolution_date_str = f.resolutiondate

            if resolution_date_str is not None:

                resolution_date = datetime.strptime(resolution_date_str[:10], '%Y-%m-%d')

                if (resolution_date.date() >= from_date) and (resolution_date.date() <= to_date):

                    issue_row = {'swimlane':   issue.category,
                                 'id':         issue.key,
                                 'week':       week_start_date(resolution_date.isocalendar()[0],
                                                               resolution_date.isocalendar()[1]).strftime('%Y-%m-%d'),
                                 'project':    f.project.name,
                                 'type':       f.issuetype.name,
                                 'components': [],
                                 'count':   1}

                    for component in f.components:
                        issue_row['components'].append(component.name)

                    issue_rows.append(issue_row)

        df = pd.DataFrame(issue_rows)

        table = pd.tools.pivot.pivot_table(df, rows=['week'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

        reindexed = table.reindex(index=fill_in_blanks(table.index), fill_value=np.int64(0))
        noncum = reindexed.fillna(0)
        cumtab = noncum.cumsum(axis=0)

        # For some readon the name of the index gets blown away by the reindex
        cumtab.index.name = table.index.name

        return cumtab


class JiraWrapper(object):
    """
    Wrapper around our JIRA instance
    """

    def __init__(self, config):

        self.issue_collection = None

        self.jira = jira.client.JIRA({'server': config['server']},
                                     basic_auth=(config['username'], config['password']))

        self.categories = config['categories']
        self.cycles = config['cycles']

    def issues(self):
        """
        Issues for a given set of categories or all if no categories specified
        """
        if self.issue_collection is None:
            self.issue_collection = JiraIssues(self.jira, self.categories, self.cycles)
        return self.issue_collection
