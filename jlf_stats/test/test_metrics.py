# -*- coding: utf-8 -*-

import unittest
import os
import tempfile

from jlf_stats.metrics import Metrics


class TestMetrics(unittest.TestCase):

    def testDumpWorkItemsToFile(self):

        workspace = tempfile.mkdtemp()
        local_data_config = {'source': {'type': 'local',
                                        'file': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'dummy.json')},
                             'categories': {'Portal':    'project = Portal',
                                            'Reports': 'component = Report',
                                            'Ops Tools': 'project = OPSTOOLS'},
                             'cycles': {'develop': {'start':  'In Progress',
                                                    'end':    'Customer Approval',
                                                    'ignore': 'Reopened'},
                                        'approve': {'start':  'In Progress',
                                                    'end':    'Closed',
                                                    'ignore': 'Reopened'}},
                             'types': {'value': ['Data Request', 'Improve Feature'],
                                       'failure': ['Defect'],
                                       'overhead': ['Task', 'Infrastructure']},
                             'states': ['In Progress', 'pending', 'Customer Approval'],
                             'counts_towards_throughput': 'Customer Approval'}

        save_path = os.path.join(workspace, "local.json")

        our_metrics = Metrics(config=local_data_config)
        our_metrics.save_work_items(save_path)
        import pdb; pdb.set_trace()
        # Reload

        # Confirm they match
