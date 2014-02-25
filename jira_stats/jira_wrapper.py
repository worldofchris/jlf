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
import math

"""States between which we consider an issue to be being worked on
   for the purposes of calculating cycletime"""

START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'


def fill_in_blanks(index):

    index_list = index.tolist()

    start_date = datetime.strptime(index_list[0][:10], '%Y-%m-%d')

    end_date = datetime.strptime(index_list[-1][:10], '%Y-%m-%d')

    num_weeks = rrule.rrule(rrule.WEEKLY,
                            dtstart=start_date,
                            until=end_date).count()

    new_index = [week_start_date((start_date + timedelta(weeks=i)).isocalendar()[0],
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


def get_cycle_time(histories,
                   start_state=START_STATE,
                   end_state=END_STATE,
                   reopened_state=REOPENED_STATE):

    """Calculate how long it has taken an issue to get from START_STATE
       to END_STATE"""

    start_date = None
    end_date = None

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                new_start_date = None

                if item.toString == start_state:

                    new_start_date = datetime.strptime(history.created[:10],
                                                       '%Y-%m-%d')

                if item.fromString == start_state:

                    new_start_date = datetime.strptime(history.created[:10],
                                                       '%Y-%m-%d')

                if new_start_date is not None:

                    if start_date is None:
                        start_date = new_start_date
                    else:
                        if new_start_date < start_date:
                            start_date = new_start_date

                if item.toString == end_state:

                    # We ignore transitions to end_state if
                    # they are from reopened.
                    # This is because we sometime have to re-open
                    # tickets just to fix
                    # details of ownership, component, type or resolution.
                    if item.fromString != reopened_state:
                        end_date = datetime.strptime(history.created[:10],
                                                     '%Y-%m-%d')

    if start_date is None or end_date is None:
        return None

    return ((end_date - start_date).days) + 1


def get_time_in_states(histories, from_date=None, until_date=None):
    """
    How long did an issue spend in each state in its history.

    For the first state it was in count 'from' the start of the period we
    are interested in, typically when the issue was created

    For the last state it was in count from the time the state was entered
    until the date specified in 'until' - typically today's date
    """

    time_in_states = []

    current_state = None

    if from_date is None:
        from_date = date(1970, 01, 01)

    if hasattr(from_date, 'date'):
        prev_state_change_date = from_date.date()
    else:
        prev_state_change_date = from_date

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                state_change_date = datetime.strptime(history.created[:10],
                                                      '%Y-%m-%d').date()

                days_in_state = state_change_date - prev_state_change_date

                if current_state is None:
                    current_state = item.fromString

                time_in_states.append({'state': current_state,
                                       'days': days_in_state.days})

                current_state = item.toString
                prev_state_change_date = state_change_date

    if until_date is not None:
        final_state_days = until_date - prev_state_change_date

        time_in_states.append({'state': current_state,
                               'days':  final_state_days.days})
    else:
        time_in_states.append({'state': current_state,
                               'days':  1})

    return time_in_states


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

        try:
            self.categories = config['categories']
            self.cycles = config['cycles']
            self.types = config['types']
            self.ongoing_states = config['ongoing']
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

    def get_issues_from_jira(self, jira, filter=None, filter_by_category=None):
        """
        Get the actual issues from Jira itself via the Jira REST API
        """

        batch_size = 100
        issues = []

        for category in self.categories:

            # This bit stinks - we are confusing getting the data from Jira with filtering it
            # _after_ we've got it from Jira.
            
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
                            setattr(issue,
                                    cycle,
                                    get_cycle_time(issue.changelog.histories,
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

    def issues_as_rows(self, issues, types=None):

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
                time_in_states = get_time_in_states(issue.changelog.histories,
                                                    datetime.strptime(f.created[:10],
                                                                      '%Y-%m-%d'),
                                                    date.today())

                since = time_in_states[-1]['days']

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

    @property
    def ongoing(self):
        """
        All issues that are still in flight
        """
        if self.ongoing_issues is None:
            filter = 'and (status in ({status_list})) and issuetype in standardIssueTypes()'.format(status_list = ', '.join('"{status}"'.format(status=status) for status in self.ongoing_states))
            self.ongoing_issues = self.get_issues_from_jira(self.jira, filter=filter)

        issue_rows = self.issues_as_rows(self.ongoing_issues)
        df = pd.DataFrame(issue_rows)
        return df

    @property
    def done(self):
        """
        All issues that have been completed
        """
        if self.done_issues is None:
            self.get_done_issues()

        issue_rows = self.issues_as_rows(self.done_issues) 
        df = pd.DataFrame(issue_rows)
        return df

    def history(self, from_date=None, until_date=None):

        if self.issue_history is None:

            if self.done_issues is None:
                self.get_done_issues()

            history = {}

            for issue in self.done_issues:

                created_date = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')

                issue_history = get_time_in_states(issue.changelog.histories, from_date=created_date, until_date=until_date)

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
                    states = ['Open',
                              'Horizon',
                              'Queued',
                              'In Progress',
                              'Blocked',
                              'Awaiting Review',
                              'Peer Review',
                              'pending',
                              'Customer Approval',
                              'Ready for Release',
                              'Closed',
                              'Resolved']
                    return states.index(state)
                except ValueError:
                    if type(state) == float:
                        if math.isnan(state):
                            return -1
                    raise
            
            days[day] = sorted(tickets, key=state_order)

        return pd.DataFrame(days)

    def created(self,
                from_date,
                to_date,
                cumulative=True,
                category=None,
                types=None):
        """
        Return the number of issues created each week
        """

        if self.all_issues is None:
            self.all_issues = self.get_issues_from_jira(self.jira)

        issue_rows = self.issues_as_rows(self.all_issues, types)

        # Does ongoing exclude done in its query?
        df = pd.DataFrame(issue_rows)
        table = pd.tools.pivot.pivot_table(df, rows=['week_created'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

        reindexed = table.reindex(index=fill_in_blanks(table.index), fill_value=np.int64(0))
        return reindexed


    def get_done_issues(self, category=None):

        """
        We want to exclude subtasks and anything that was not resolved as fixed
        """
        counts_towards_throughput = ' AND issuetype in standardIssueTypes() AND resolution = Fixed AND status in (Resolved, Closed)'

        self.done_issues = self.get_issues_from_jira(self.jira,
                                                     counts_towards_throughput,
                                                     category)



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
            self.get_done_issues(category=category)

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

            reindexed = table.reindex(index=fill_in_blanks(table.index), fill_value=np.int64(0))
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
