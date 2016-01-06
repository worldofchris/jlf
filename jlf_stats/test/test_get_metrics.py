# -*- coding: utf-8 -*-

import unittest
import os
from jlf_stats.metrics import Metrics


class TestGetMetrics(unittest.TestCase):

    def testGetWorkItemByID(self):
        """
        Work Items can be queried by ID
        """

        config = {
            'source': {'type': 'local',
                       'file': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data/single_work_item.json')},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        metrics = Metrics(config=config)
        work_item = metrics.work_item('OPSTOOLS-1')

        self.assertEqual(work_item.category, "Ops Tools")

    def testGetNonExistantIssue(self):
        """
        Fails gracefully if no work item can be found
        """

        config = {
            'source': {'type': 'local',
                       'file': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data/no_work_items.json')},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        metrics = Metrics(config=config)
        work_item = metrics.work_item('OPSTOOLS-1')
        self.assertEqual(work_item, None)