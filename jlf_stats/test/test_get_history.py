# -*- coding: utf-8 -*-
from jlf_stats.history import cycle_time, time_in_states, arrivals, history_from_jira_changelog, history_from_state_transitions
from jlf_stats.test.jira_mocks import mockHistory, mockItem, mockChangelog, CREATED_STATE, START_STATE, END_STATE, REOPENED_STATE

import unittest
from datetime import date
import dateutil.parser

import pandas as pd
from pandas.util.testing import assert_series_equal


class TestIssueHistory(unittest.TestCase):

    def testGetCycleTime(self):

        history = pd.Series([CREATED_STATE,
                             CREATED_STATE,
                             START_STATE,
                             'pending',
                             'pending',
                             'pending',
                             'Customer Approval',
                             'Customer Approval',
                             'pending',
                             'pending',
                             'Customer Approval',
                             'Customer Approval',
                             'Customer Approval',
                             'Customer Approval',
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04',
                                                  '2012-01-05',
                                                  '2012-01-06',
                                                  '2012-01-07',
                                                  '2012-01-08',
                                                  '2012-01-09',
                                                  '2012-01-10',
                                                  '2012-01-11',
                                                  '2012-01-12',
                                                  '2012-01-13',
                                                  '2012-01-14',
                                                  '2012-01-15']))

        self.assertEquals(cycle_time(history), 13)

    def testGetCycleTimeWithDropOuts(self):

        history = pd.Series([START_STATE,
                             'pending',
                             START_STATE,
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04']))

        self.assertEquals(cycle_time(history), 4)

    def testGetCycleTimeIsStillOpen(self):

        history = pd.Series([START_STATE,
                             'pending'],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02']))

        self.assertEquals(cycle_time(history), None)

    def testGetCycleTimeIncRepopenedToClosed(self):

        history = pd.Series([START_STATE,
                             END_STATE,
                             REOPENED_STATE,
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04']))

        self.assertEquals(cycle_time(history), 4)

    def testCycleStartsWithOpen(self):
        """We need to be able to deal with workflows where there is no queue before work actually starts"""

        history = pd.Series(['Open',
                             'Awaiting Review',
                             'Reviewing',
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04']))

        self.assertEquals(cycle_time(history,
                                     start_state='Open',
                                     end_state='Reviewing'), 3)

    def testCycleEndsWithExitingAState(self):
        """In some workflows, the cycle we are interested in can end with a transition to more than one state so
           we measure to the exit from the last state rather than the arrival at the end state."""

        history = pd.Series([CREATED_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             'pending'],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04',
                                                  '2012-01-05',
                                                  '2012-01-06',
                                                  '2012-01-07',
                                                  '2012-01-08',
                                                  '2012-01-09',
                                                  '2012-01-10',
                                                  '2012-01-11',
                                                  '2012-01-12']))

        self.assertEquals(cycle_time(history, exit_state=START_STATE), 10)

    def testCycleStartsWithExitingAState(self):
        """In some workflows, the cycle we are intertested in can start with a transition into a number of states
            so we measure from the exit of the previous state rather than the arrival at a specific state."""

        history = pd.Series([CREATED_STATE,
                             'queued',
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04',
                                                  '2012-01-05',
                                                  '2012-01-06',
                                                  '2012-01-07',
                                                  '2012-01-08',
                                                  '2012-01-09',
                                                  '2012-01-10',
                                                  '2012-01-11',
                                                  '2012-01-12',
                                                  '2012-01-13']))

        self.assertEquals(cycle_time(history,
                                     after_state='queued'), 11)

    def testGetCycleTimeForIncludedStates(self):
        """
        For cases where cycle starts by exiting one or more states and
        ends by entering one or more states we measure the cycle by recording
        number of days in the states we are interested in.
        """

        history = pd.Series([CREATED_STATE,
                             'queued',
                             'one',
                             'two',
                             'two',
                             'three',
                             'three',
                             'three',
                             END_STATE,
                             'two',
                             'four',
                             'five',
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04',
                                                  '2012-01-05',
                                                  '2012-01-06',
                                                  '2012-01-07',
                                                  '2012-01-08',
                                                  '2012-01-09',
                                                  '2012-01-10',
                                                  '2012-01-11',
                                                  '2012-01-12',
                                                  '2012-01-13']))

        self.assertEquals(cycle_time(history,
                                     include_states=['one', 'two', 'three']), 7)

    def testGetCycleTimeForExcludedStates(self):
        """
        Like included states above but expressed as the inverse - i.e. the states
        we are not interested in.
        """

        history = pd.Series([CREATED_STATE,
                             'queued',
                             'one',
                             'two',
                             'two',
                             'three',
                             'three',
                             'three',
                             END_STATE,
                             'two',
                             'four',
                             'five',
                             END_STATE],
                            index=pd.to_datetime(['2012-01-01',
                                                  '2012-01-02',
                                                  '2012-01-03',
                                                  '2012-01-04',
                                                  '2012-01-05',
                                                  '2012-01-06',
                                                  '2012-01-07',
                                                  '2012-01-08',
                                                  '2012-01-09',
                                                  '2012-01-10',
                                                  '2012-01-11',
                                                  '2012-01-12',
                                                  '2012-01-13']))

        self.assertEquals(cycle_time(history,
                                     exclude_states=[CREATED_STATE,
                                                     'queued',
                                                     'four',
                                                     'five',
                                                     END_STATE]), 7)

    def testGetDaysInStates(self):
        """
        Work is getting stuck in CA for ages.  We want to see for how long.
        To start with we'll just find out how long has something been in its current state
        """

        histories = [mockHistory(u'2012-11-18T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                     mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]

        created = date(2012, 11, 16)
        today = date(2012, 12, 02)

        actual = time_in_states(histories, created, today)

        expected = [{'state': 'Open',
                     'days':  2},
                    {'state': START_STATE,
                     'days':  10},
                    {'state': 'pending',
                     'days':  2},
                    {'state': END_STATE,
                     'days':  2}]

        assert actual == expected, actual

    def testGetTimeInStatesWithNoHistory(self):

        """
        If a ticket has not left its initial state then it has no explict history so we need to
        create one for it based on how long it has been in this initial state.
        """

        created = date(2012, 11, 16)
        today = date(2012, 12, 02)

        expected = [{'state': 'Open',
                     'days': 16}]

        actual = time_in_states([], created, today)

        assert actual == expected, actual

    def testGetHistoryFromJiraChangeLog(self):

        """
        Generate the internal daily history of a Jira issue from its ChangeLog

        As part of the refactoring to make Cycle Time and Throughput use the internal
        representation of history rather than the Jira ChangeLog Histories we want the
        internal representation of an issue to contain its history in this form.

        This also sets us up for the FogBugz integration which will see us decouple all
        the Jira specific stuff from the internal data wrangling.
        """

        source = mockChangelog([mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', CREATED_STATE, 'queued')]),
                                mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                mockHistory(u'2012-01-13T09:54:29.284+0000', [mockItem('status', START_STATE, END_STATE)])])

        expected = pd.Series([CREATED_STATE,
                             'queued',
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             START_STATE,
                             END_STATE],
                             index=pd.to_datetime(['2012-01-01',
                                                   '2012-01-02',
                                                   '2012-01-03',
                                                   '2012-01-04',
                                                   '2012-01-05',
                                                   '2012-01-06',
                                                   '2012-01-07',
                                                   '2012-01-08',
                                                   '2012-01-09',
                                                   '2012-01-10',
                                                   '2012-01-11',
                                                   '2012-01-12',
                                                   '2012-01-13']))

        actual = history_from_jira_changelog(source, date(2012, 01, 01))

        assert_series_equal(actual, expected)

    def testGetArrivals(self):
        """
        In order to work out the arrival rate we need to be able to get the days a ticket arrived
        in each of the states in its history.
        """

        histories = [mockHistory(u'2012-11-18T09:54:29.284+0000', [mockItem('status', 'start', 'QA Queue')]),
                     mockHistory(u'2012-11-18T09:54:29.284+0000', [mockItem('status', 'QA Queue', 'Customer Queue')]),
                     mockHistory(u'2012-11-22T09:54:29.284+0000', [mockItem('status', 'Customer Queue', 'Customer Review')])]

        expected = {date(2012, 11, 18): {'QA Queue': 1, 'Customer Queue': 1},
                    date(2012, 11, 22): {'Customer Review': 1}}

        actual = arrivals(histories)

        self.assertEquals(actual, expected)

        actual = arrivals(histories, actual)

        expected_twice = {date(2012, 11, 18): {'QA Queue': 2, 'Customer Queue': 2},
                          date(2012, 11, 22): {'Customer Review': 2}}

        self.assertEquals(actual, expected_twice)

    def testGetHistoryWithNoStateTransitions(self):
    	foo

    def testGetHistoryFromStateTransitions(self):

        state_transitions = [{'from': "Open",
                                      'timestamp': dateutil.parser.parse("2015-02-26T10:02:06+00:00"),
                                      'to': "Insane"},
                             {'from': "Insane",
                                      'timestamp': dateutil.parser.parse("2015-02-26T10:02:06+00:00"),
                                      'to': "Active"},
                             {'from': "Active",
                                      'timestamp': dateutil.parser.parse("2015-03-07T10:02:06+00:00"),
                                      'to': "Resolved (Fixed)"},
                             {'from': "Resolved (Fixed)",
                                      'timestamp': dateutil.parser.parse("2015-03-12T10:02:06+00:00"),
                                      'to': "Closed"}]

        expected = pd.Series(['Open',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Active',
                              'Resolved (Fixed)',
                              'Resolved (Fixed)',
                              'Resolved (Fixed)',
                              'Resolved (Fixed)',
                              'Resolved (Fixed)',
                              'Closed'],                           
                             index=pd.to_datetime(['2015-02-25',
                                                   '2015-02-26',
                                                   '2015-02-27',
                                                   '2015-02-28',
                                                   '2015-03-01',
                                                   '2015-03-02',
                                                   '2015-03-03',
                                                   '2015-03-04',
                                                   '2015-03-05',
                                                   '2015-03-06',
                                                   '2015-03-07',
                                                   '2015-03-08',
                                                   '2015-03-09',
                                                   '2015-03-10',
                                                   '2015-03-11',
                                                   '2015-03-12']))

        actual = history_from_state_transitions(dateutil.parser.parse("2015-02-25T10:02:06+00:00").date(),
                                                state_transitions,
                                                dateutil.parser.parse("2015-03-12T10:02:06+00:00").date())

        assert_series_equal(actual, expected)
