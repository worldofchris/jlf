# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

from datetime import date
from jira_stats.jira_wrapper import JiraWrapper
from jira_stats.jira_wrapper import fill_in_blanks, week_start_date

from pandas.util.testing import assert_frame_equal

from mockito import when, any, unstub


class MockProject(object):

    def __init__(self, name):
        self.name = name


class MockIssueType(object):

    def __init__(self, name):
        self.name = name


class MockFields(object):

    def __init__(self, resolutiondate, project_name, issuetype_name):
        self.issuetype = MockIssueType(issuetype_name)
        self.resolutiondate = resolutiondate
        self.project = MockProject(project_name)
        self.components = []


class MockIssue(object):

    def __init__(self,
                 key,
                 resolution_date,
                 project_name,
                 issuetype_name):

        self.key = key
        self.fields = MockFields(resolution_date, project_name, issuetype_name)
        self.project = MockProject(project_name)
        self.category = None


class TestGetMetrics(unittest.TestCase):

    categories = {
        'Portal':  'project = Portal',
        'Reports': 'component = Report',
        'Ops Tools': 'project = OPSTOOLS'
    }

    cycles = {
        "develop": {"start":  "In Progress",
                    "end":    "Customer Approval",
                    "ignore": "Reopened"},
        "approve": {"start":  "In Progress",
                    "end":    "Closed",
                    "ignore": "Reopened"}
    }

    types = {
        "value": ['Data Request', 'Improve Feature'],
        "failure": ['Defect'],
        "overhead": ['Task', 'Infrastructure']
    }

    jira_config = {
        'server': 'jiratron.worldofchris.com',
        'username': 'mrjira',
        'password': 'foo',
        'categories': categories,
        'cycles': cycles,
        'types': types
    }

    dummy_issues_1 = [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect'),
                      MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect'),
                      MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Defect')]

    dummy_issues_2 = [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect'),
                      MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Improve Feature'),
                      MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Defect')]

    dummy_issues_3 = [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect'),
                      MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect'),
                      MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Defect')]

    def setUp(self):

        unstub()
        import jira.client

        self.mock_jira = jira.client.JIRA()

        when(self.mock_jira).search_issues(any(),
                                      startAt=any(),
                                      maxResults=any()).thenReturn(self.dummy_issues_1).thenReturn(self.dummy_issues_2).thenReturn(self.dummy_issues_3)


        when(jira.client).JIRA(any(), basic_auth=any()).thenReturn(self.mock_jira)


    def testGetCumulativeThroughputTable(self):
        """
        The Cumulative Throughput Table is what we use to create the graph in
        Excel
        """

        expected = {'Ops Tools': pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']),
                    'Portal':    pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']),
                    'Reports':   pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12'])}


        expected_frame = pd.DataFrame(expected)

        expected_frame.index.name = 'week'
        expected_frame.columns.name = 'swimlane'

        our_jira = JiraWrapper(config=self.jira_config)

        work = our_jira.issues()

        actual_frame = work.throughput(cumulative=True,
                                       from_date=date(2012, 01, 01),
                                       to_date=date(2012, 12, 31))


        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame

    def testFillInTheBlanks(self):
        """
        If we didn't complete any work in a given week then we will have a missing row in our data frame.
        This is going to make the graph inconsistent so we re-index to add in the missing weeks.
        """

        expected = {'Ops Tools': pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12']),
                    'Portal':    pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12']),
                    'Reports':   pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12'])}

        expected_frame = pd.DataFrame(expected)
        actual_index = fill_in_blanks(expected_frame.index)

        expected_index = ['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']

        assert actual_index == expected_index, actual_index

    def testGetWeekIdentifier(self):
        """
        We graph throughput on a weekly basis so for a given issue we need to know which week it was completed in.
        """

        issues = [{'year': 2012, 'week': 1, 'week_start': date(2012, 01, 02)}]

        for issue in issues:
            actual_week_start = week_start_date(issue['year'], issue['week'])
            assert issue['week_start'] == actual_week_start, actual_week_start


    def testGetDifferentWorkTypes(self):
        """
        In order to see how our throughput is split across value work, failure work and operational
        overhead we want to be able to specify the work type we are interested in when we ask for throughput.
        """

        expected = {'Ops Tools-value': pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']),
                    'Ops Tools-failure':    pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']),
                    'Ops Tools-overheard':   pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12'])}


        expected_frame = pd.DataFrame(expected)

        our_jira = JiraWrapper(config=self.jira_config)

        work = our_jira.issues()

        # We typically are not interested in this data cumulatively as we want to compare how we are split on a week by week basis

        actual_frame = work.throughput(cumulative=False,
                                       from_date=date(2012, 01, 01),
                                       to_date=date(2012, 12, 31),
                                       types=["value", "failure", "overhead"]
                                       )

        # assert False, actual_frame

        # assert expected_frame == actual_frame, actual_frame


    def testGetMitchells(self):

        """
        After Benjamin Mitchell's item history tracking:
        http://blog.benjaminm.net/2012/06/26/how-to-study-the-flow-or-work-with-kanban-cards

        and our own

        Very Hungry Catapiller

        """

        expected = {'FEATURE-1': pd.Series(['2012-10-10', 
                                            'open', np.int64(10), 
                                            'closed', np.int64(3),
                                            None, None],
                                            index=['start-date', 
                                                   'state', 'duration',
                                                   'state', 'duration',
                                                   'state', 'duration',]),
                    'FEATURE-2': pd.Series(['2012-10-10', 
                                            'open', np.int64(10),
                                            'in progress', np.int64(2), 
                                            'closed', np.int64(3)],
                                            index=['start-date', 
                                                   'state', 'duration',
                                                   'state', 'duration',
                                                   'state', 'duration',])}

        expected_frame = pd.DataFrame(expected)
