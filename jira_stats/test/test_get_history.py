# -*- coding: utf-8 -*-
from jira_stats.jira_wrapper import get_cycle_time

import unittest

START_STATE = 'In Progress'
END_STATE = 'Closed'
REOPENED_STATE = 'Reopened'


class mockHistory(object):

    def __init__(self, created, items):
        self.created = created
        self.items = items


class mockItem(object):

    def __init__(self, field, fromString, toString):
        self.field = field
        self.fromString = fromString
        self.toString = toString


class TestIssueHistory(unittest.TestCase):

    def testGetCycleTime(self):

        histories = [mockHistory(u'2012-11-18T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                     mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]

        self.assertEquals(get_cycle_time(histories), 13)

    def testGetCycleTimeWithDropOuts(self):

        histories = [mockHistory(u'2012-11-27T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', 'pending', START_STATE)]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', START_STATE, END_STATE)])]

        self.assertEquals(get_cycle_time(histories), 4)

    def testGetCycleTimeIsStillOpen(self):

        histories = [mockHistory(u'2012-11-27T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')])]

        self.assertEquals(get_cycle_time(histories), None)

    def testGetCycleTimeIncRepopenedToClosed(self):

        histories = [mockHistory(u'2012-11-28T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                     mockHistory(u'2012-11-30T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)]),
                     mockHistory(u'2013-10-30T09:54:29.284+0000', [mockItem('status', REOPENED_STATE, END_STATE)])]

        self.assertEquals(get_cycle_time(histories), 3)
