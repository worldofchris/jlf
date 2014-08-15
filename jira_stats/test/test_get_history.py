# -*- coding: utf-8 -*-
from jira_stats.history import cycle_time, time_in_states, arrivals
from jira_stats.test.jira_mocks import mockHistory, mockItem, START_STATE, END_STATE, REOPENED_STATE

import unittest
from datetime import date


class TestIssueHistory(unittest.TestCase):

    def testGetCycleTime(self):

        histories = [mockHistory(u'2012-11-18T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                     mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]

        self.assertEquals(cycle_time(histories), 13)

    def testGetCycleTimeWithDropOuts(self):

        histories = [mockHistory(u'2012-11-27T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', 'pending', START_STATE)]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', START_STATE, END_STATE)])]

        self.assertEquals(cycle_time(histories), 4)

    def testGetCycleTimeIsStillOpen(self):

        histories = [mockHistory(u'2012-11-27T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')])]

        self.assertEquals(cycle_time(histories), None)

    def testGetCycleTimeIncRepopenedToClosed(self):

        histories = [mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)]),
                     mockHistory(u'2013-10-30T09:54:29.284+0000', [mockItem('status', REOPENED_STATE, END_STATE)])]

        self.assertEquals(cycle_time(histories), 3)

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

        expected = [{'state': 'queued',
                     'days' : 2},
                    {'state': START_STATE,
                     'days' : 10},
                    {'state': 'pending',
                     'days' : 2},
                    {'state': END_STATE,
                     'days' : 2}]

        assert actual == expected, actual

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