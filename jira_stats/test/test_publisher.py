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
import xlrd

def serve_dummy_results(*args, **kwargs):

    return pd.DataFrame([1,2,3])


def serve_dummy_throughput(*args, **kwargs):

    try:

        if kwargs['types'] == ['failure', 'value', 'operational overhead']:

            return pd.DataFrame([4, 5, 6])

        else:

            dummy = pd.DataFrame([[1,2,3],[4,5,6]])
            dummy.columns = ['one', 'two', 'three']
            return dummy

    except KeyError:

        return pd.DataFrame({'one': [1, 2, 3]})


class TestGetOutput(unittest.TestCase):

    def setUp(self):
          
        self.mock_jira_wrapper = mock.Mock(spec=JiraWrapper)
        self.mock_jira_wrapper.throughput.side_effect = serve_dummy_throughput
        self.mock_jira_wrapper.demand.side_effect = serve_dummy_results
        self.mock_jira_wrapper.done.side_effect = serve_dummy_results
        self.mock_jira_wrapper.cycle_time = serve_dummy_results        
        
        self.workspace = tempfile.mkdtemp()

    def testSmokeOutCommandLine(self):
        """
        Smoke test to ensure we have not broken running from the command line
        """

        expected_filename = 'reports.xlsx'
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
                         'location': self.workspace,
                         'types': {
                            'failure': ['Bug', 'Fault'],
                            'value': ['New Feature', 'Story', 'Improvement'],
                            'oo': ['Task', 'Decision', 'User Support', 'Spike']
                        }
        }

        # Specify categories and types to report on or:
        # foreach - to report on each category separately
        # combine - to aggregate totals together

        # when we publish the metrics for the data in our jira

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))

        # Then we should get an Excel workbook

        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

        workbook = xlrd.open_workbook(actual_output)
        self.assertEqual('throughput', workbook.sheet_names()[0])

    def testOutputCumulativeThroughputToExcel(self):

        report_config = {'name':     'reports',
                         'reports':  [{'metric':     'cumulative-throughput',
                                       'categories': 'foreach',
                                       'types':      'foreach'}],
                        'format':   'xlsx',
                        'location': self.workspace,
                         'types': {
                            'failure': ['Bug', 'Fault'],
                            'value': ['New Feature', 'Story', 'Improvement'],
                            'oo': ['Task', 'Decision', 'User Support', 'Spike']
                        }}

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        


        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

        workbook = xlrd.open_workbook(actual_output)
        self.assertEqual('cumulative-throughput', workbook.sheet_names()[0])


    def testOutputFailureDemandToExcel(self):

        report_config = {'name':     'reports',
                         'reports':  [{'metric':     'demand',
                                       'categories': 'foreach',
                                       'types':      ['failure']}],
                         'format':   'xlsx',
                         'location': self.workspace,
                         'types': {
                            'failure': ['Bug', 'Fault'],
                            'value': ['New Feature', 'Story', 'Improvement'],
                            'oo': ['Task', 'Decision', 'User Support', 'Spike']
                        }
        }

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        


        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

        workbook = xlrd.open_workbook(actual_output)
        self.assertEqual('failure-demand', workbook.sheet_names()[0])

    def testOutputDoneToExcel(self):

        report_config = {'name':     'reports',
                         'reports':  [{'metric':     'done',
                                       'categories': 'foreach',
                                       'types':      'foreach',
                                       'sort':       'week-done'}],
                         'format':   'xlsx',
                         'location': self.workspace,
                            'types': {
                            'failure': ['Bug', 'Fault'],
                            'value': ['New Feature', 'Story', 'Improvement'],
                            'oo': ['Task', 'Decision', 'User Support', 'Spike']
                        }
        }

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        


        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

        workbook = xlrd.open_workbook(actual_output)
        self.assertEqual('done', workbook.sheet_names()[0])

        # and sorted by week-done...


    def testOutputCycleTimeToExcel(self):

        report_config = {'name':    'reports',
                         'reports': [{'metric':     'cycle-time',
                                       'categories': 'foreach',
                                       'types':      ['value'],
                                       'cycles':     ['develop']}],
                         'format':   'xlsx',
                         'location': self.workspace}

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        


        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        # with a sheet containing the throughput data

        workbook = xlrd.open_workbook(actual_output)
        self.assertEqual('value-develop-cycle-time', workbook.sheet_names()[0])


    def testMakeValidSheetTitle(self):

        titles = [('failure-value-operational overhead-demand', 'failure-value-operatio-demand'),
                  ('aa-bb-cc-dd-ee-ff-gg-hh-ii-jj-kk-ll-mm-nn-oo-pp-qq-rr-ss-tt-uu-vv-ww-demand', 'a-b-c-d-e-f-g-h-i-j-k-l-demand')]

        for title in titles:
            actual_title = publisher.worksheet_title(title[0])

        expected_title = title[1]

        self.assertEqual(actual_title, expected_title)


    def testOutputMultipleTypesOfThroughput(self):

        report_config = {'name':     'reports',
                         'reports':  [{'metric':     'throughput',
                                       'categories': 'foreach',
                                       'types':      'foreach'}],
                         'format':   'xlsx',
                         'location': self.workspace,
                         'categories': {
                            'one': 'project = "one"',
                            'two': 'project = "two"',
                            'three': 'project = "three"'
                         },
                         'types': {
                            'failure': ['Bug', 'Fault'],
                            'value': ['New Feature', 'Story', 'Improvement'],
                            'oo': ['Task', 'Decision', 'User Support', 'Spike']
                        }
        }

        publisher.publish(report_config,
                          self.mock_jira_wrapper,
                          from_date=date(2012, 10, 8),
                          to_date=date(2012, 11, 12))        


        expected_filename = 'reports.xlsx'
        actual_output = os.path.join(self.workspace, expected_filename)

        self.assertTrue(os.path.isfile(actual_output), "Spreadsheet not published:{spreadsheet}".format(spreadsheet=actual_output))

        workbook = xlrd.open_workbook(actual_output)

        expected_sheet_name = 'throughput'
        self.assertEqual(expected_sheet_name, workbook.sheet_names()[0])
        worksheet = workbook.sheet_by_name(expected_sheet_name)
        header_row = worksheet.row(0)
        expected_headers = ['one', 'two', 'three']

        for cell in header_row[1:]:
            self.assertEqual(cell.value, expected_headers[header_row[1:].index(cell)])
