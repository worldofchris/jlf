import unittest
import xlrd
import pandas as pd


def output_to_excel(workbook, dataframes):
    """
    Given an array of dictionaries, each giving a Data frame
    and a name for that Data Frame, outputs these to a single
    Excel workbook
    """
    writer = pd.ExcelWriter(workbook)

    for df in dataframes:
        df['frame'].to_excel(writer, df['name'])

    writer.save()


class TestOutputToExcel(unittest.TestCase):

    @unittest.skip('No Internet!')
    def testOutputMultipleDataFramesToSingleWorkbook(self):

        expected_worksheets = ['one', 'two', 'three']

        one = pd.DataFrame({'one': pd.Series([1., 2., 3.],
                            index=['a', 'b', 'c']),
                            'two': pd.Series([1., 2., 3., 4.],
                            index=['a', 'b', 'c', 'd'])})

        two = pd.DataFrame({'three': pd.Series([1., 2., 3.],
                            index=['a', 'b', 'c']),
                            'four': pd.Series([1., 2., 3., 4.],
                            index=['a', 'b', 'c', 'd'])})

        three = pd.DataFrame({'five': pd.Series([1., 2., 3.],
                              index=['a', 'b', 'c']),
                              'six': pd.Series([1., 2., 3., 4.],
                              index=['a', 'b', 'c', 'd'])})

        output_to_excel('test_workbook.xlsx',
                        [{'name': 'one', 'frame': one},
                         {'name': 'two', 'frame': two},
                         {'name': 'three', 'frame': three}])

        book = xlrd.open_workbook('test_workbook.xlsx')

        i = 0
        for sheet in expected_worksheets:
            assert book.sheet_names()[i] == sheet
            i += 1
