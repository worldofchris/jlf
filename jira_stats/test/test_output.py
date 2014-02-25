"""
What output do we expect from JLF?

Tables and Graphs in Excel for:

-Cumulative Throughput
-Ratio of Work Types (i.e. Value/Failure/Overhead)
-Introduction of Defects
-Cycle Time
"""

import unittest


class TestGeOutput(unittest.TestCase):

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
