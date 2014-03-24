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


class TestGetOutput(unittest.TestCase):

    def testSmokeOutCommandLine(self):
        """
        Smoke test to ensure we have not broken running from the command line
        """

        workspace = tempfile.mkdtemp()
        expected_filename = 'config.xlsx'
        pwd = os.path.dirname(os.path.abspath(__file__))
        bin_dir = '../../bin'
        jlf = os.path.join(pwd, bin_dir, 'jlf')
        config_file = os.path.join(pwd, bin_dir, 'config.json')

        saved_path = os.getcwd()
        os.chdir(workspace)
        call([jlf, '-c', config_file])
        os.chdir(saved_path)

        actual_output = os.path.join(workspace, expected_filename)
        self.assertTrue(actual_output)

    @unittest.skip("WIP")
    def testOutputCumulativeThroughputToExcel(self):

        # Given this config:

        report_config = {'type':    'cumulative-throughput',
                         'format':  'xlsx',
                         'foreach': 'category'}

        # How do we distinguish between a report for all categories
        # and a report per category?

        # foreach
        # all

        # And this data:

        # When we run JLF

        # Then we should get an Excel sheet with a table and a graph

        pass
