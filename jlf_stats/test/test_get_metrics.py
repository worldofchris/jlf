# -*- coding: utf-8 -*-

import unittest
import os
import pandas as pd
import numpy as np
from datetime import date, datetime

from jlf_stats.metrics import Metrics

from pandas.util.testing import assert_frame_equal

CREATED_STATE = 'Open'
START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'

def data_file(filename):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)

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
                       'file': data_file('data/no_work_items.json')},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        metrics = Metrics(config=config)
        work_item = metrics.work_item('OPSTOOLS-1')
        self.assertEqual(work_item, None)

    def testGetCumulativeThroughputTable(self):
        """
        The Cumulative Throughput Table is what we use to create the graph in
        Excel
        """

        expected_frame = pd.read_json(data_file('data/expected/cumulative_throughput.json'))

        expected_frame.index.name = 'week'
        expected_frame.columns.name = 'swimlane'

        config = {
            'source': {'type': 'local',
                       'file': data_file('data/dummy.json')},
            'categories': {
                'Portal':    'project = Portal',
                'Reports': 'component = Report',
                'Ops Tools': 'project = OPSTOOLS'
            },
            'cycles': None,
            'types': None,
            'counts_towards_throughput': END_STATE,
            'until_date': '2012-11-13'
        }

        metrics = Metrics(config=config)

        actual_frame = metrics.throughput(cumulative=True,
                                          from_date=date(2012, 01, 01),
                                          to_date=date(2012, 11, 13))

        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame


    def testGetDemand(self):

        config = {
            'source': {'type': 'local',
                       'file': data_file('data/dummy.json')},
            'categories': {
                'Portal':    'project = Portal',
                'Reports': 'component = Report',
                'Ops Tools': 'project = OPSTOOLS'
            },
            'cycles': None,
            'types': None,
            'counts_towards_throughput': END_STATE,
            'until_date': '2012-11-13'
        }

        metrics = Metrics(config=config)
        actual_frame = metrics.demand(from_date=date(2012, 01, 01),
                                      to_date=date(2012, 12, 31),
                                      types=["failure"])

        print actual_frame
