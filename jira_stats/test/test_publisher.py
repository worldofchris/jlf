"""
What output do we expect from JLF?

Tables and Graphs in Excel for:

-Cumulative Throughput
-Ratio of Work Types (i.e. Value/Failure/Overhead)
-Introduction of Defects
-Cycle Time
"""

import unittest
import tempfile
import os
from subprocess import call
import mock
from jira_stats.jira_wrapper import JiraWrapper
from jira_stats import publisher
from datetime import date
import pandas as pd

def serve_dummy_results(*args, **kwargs):

    return pd.DataFrame([1,2,3])


class TestGetOutput(unittest.TestCase):

    def setUp(self):
          
        self.mock_jira_wrapper = mock.Mock(spec=JiraWrapper)
        self.mock_jira_wrapper.throughput.side_effect = serve_dummy_results
        
        self.workspace = tempfile.mkdtemp()

    def testSmokeOutCommandLine(self):
        """
        Smoke test to ensure we have not broken running from the command line
        """

        expected_filename = 'config.xlsx'
        pwd = os.path.dirname(os.path.abspath(__file__))
        bin_dir = '../../bin'
        jlf = os.path.join(pwd, bin_dir, 'jlf')
        config_file = os.path.join(pwd, bin_dir, 'config.json')

        saved_path = os.getcwd()
        os.chdir(self.workspace)
        call([jlf, '-c', config_file])
        os.chdir(saved_path)

        actual_output = os.path.join(self.workspace, expected_filename)
        self.assertTrue(os.path.isfile(actual_output))

    def testOutputThroughputToExcel(self):

        # Given this report config:

        report_config = {'name':     'reports',
                         'reports':  [{'metric':    'throughput',
                                      'categories': 'foreach',
                                      'types':      'foreach'}],
                         'format':   'xlsx',
                         'location': self.workspace}

        # Specify categories and types to report on or:
        # foreach - to report on each category separately
        # combine - to aggregate totals together

        # And this data:

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        

        # Then we should get an Excel workbook

        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

    @unittest.skip('wip')
    def testOutputStandardMetricsToExcel(self):

        report_config = {'name':     'reports',
                         'reports':  [{'metric':     'throughput',
                                       'categories': 'foreach',
                                       'types':      'foreach'},
                                      {'metric':     'cumulative-throughput',
                                       'categories': 'foreach',
                                       'types':      'foreach'},
                                      {'metric':     'demand',
                                       'categories': 'foreach',
                                       'types':      'failure'},
                                      {'metric':     'done',
                                       'categories': 'foreach',
                                       'types':      'foreach',
                                       'sort':       'week-done'},
                                      {'metric':     'cycle-time',
                                       'categories': 'foreach',
                                       'types':      'foreach'}],
                         'format':   'xlsx',
                         'location': self.workspace}

