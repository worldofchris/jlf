# -*- coding: utf-8 -*-
"""
Given a History
When we create a work item with a history (but for the time being no cycles)
We should expect its cycles to be populated from that History
We can then move responsibility for creating the cycles into the work item itself
"""

from jlf_stats.work_item import WorkItem

import unittest
from datetime import datetime, date
from dateutil.tz import tzutc

class TestWorkItem(unittest.TestCase):

    def testCreateCyclesFromHistory(self):

        cycle_config = {
            "develop": {"start":  "In Progress",
                        "end":    "Customer Approval",
                        "ignore": "Reopened"},
            "approve": {"start":  "In Progress",
                        "end":    "Closed",
                        "ignore": "Reopened"}
        }

        state_transitions = [{u'from': u'queued',
                              u'to':   u'In Progress',
                              u'timestamp': datetime(2012, 11, 12, 9, 54, 29, 284000, tzinfo=tzutc())},
                             {u'from': u'In Progress',
                              u'to':   u'Pending',
                              u'timestamp': datetime(2012, 11, 14, 9, 54, 29, 284000, tzinfo=tzutc())},
                             {u'from': u'Pending',
                              u'to':   u'Customer Approval',
                              u'timestamp': datetime(2012, 11, 16, 9, 54, 29, 284000, tzinfo=tzutc())}]

        work_item = WorkItem(id=u'OPSTOOLS-1',
                             state=u'Customer Approval',
                             title=u'Engine not working, throwing up this for no reason',
                             type=u'Defect',
                             category=u'Awesome Software',
                             date_created=date(2012, 11, 11),
                             until_date=date(2012, 11, 16),
                             state_transitions=state_transitions,
                             cycle_config=cycle_config)

        self.assertEquals(work_item.cycles['develop'], 5)

