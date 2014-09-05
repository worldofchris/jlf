# -*- coding: utf-8 -*-

import unittest
import pandas as pd
import numpy as np

from datetime import date
from jira_stats.jira_wrapper import JiraWrapper
from jira_stats.index import fill_date_index_blanks, week_start_date
from jira_stats.bucket import bucket_labels
from jira_stats.jira_wrapper import MissingState, MissingConfigItem

from pandas.util.testing import assert_frame_equal

import mock
from mockito import when, any, unstub
from jira_stats.test.jira_mocks import mockHistory, mockItem, START_STATE, END_STATE
import copy

import jira.client


class MockProject(object):

    def __init__(self, name):
        self.name = name


class MockIssueType(object):

    def __init__(self, name):
        self.name = name


class MockStatus(object):

    def __init__(self, name):
        self.name = name


class MockFields(object):

    def __init__(self,
                 resolutiondate,
                 project_name,
                 issuetype_name,
                 created=None):
        self.issuetype = MockIssueType(issuetype_name)
        self.resolutiondate = resolutiondate
        self.project = MockProject(project_name)
        self.components = []
        self.created = created
        self.summary = None
        self.status = MockStatus(name='In Progress')


class MockChangelog(object):

    def __init__(self, histories):
        self.histories = histories


class MockIssue(object):

    def __init__(self,
                 key,
                 resolution_date,
                 project_name,
                 issuetype_name,
                 created=None):

        self.key = key
        self.fields = MockFields(resolution_date,
                                 project_name,
                                 issuetype_name,
                                 created)
        self.project = MockProject(project_name)
        self.category = None
        self.changelog = None
        self.created = created


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

    ongoing = ["In Progress", "Awaiting Review", "Peer Review", "Awaiting Customer Approval", "Customer Approval"]
    states = ['In Progress', 'pending','Customer Approval']

    jira_config = {
        'server': 'jiratron.worldofchris.com',
        'username': 'mrjira',
        'password': 'foo',
        'categories': categories,
        'cycles': cycles,
        'types': types,
        'ongoing': ongoing,
        'states': states
    }

    # There are three sets of issues to match the three categories that get searched for in the tests

    dummy_issues = {
        'Portal':   [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2012-01-01'),
                     MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect', created='2012-01-01'),
                     MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Defect', created='2012-01-01')],
        'Reports':  [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Data Request', created='2012-01-01'),
                     MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Improve Feature', created='2012-01-01'),
                     MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Improve Feature', created='2012-01-01')],
        'Ops Tools':[MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2012-01-01'),
                     MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect', created='2012-01-01'),
                     MockIssue(key='PORTAL-3', resolution_date='2012-10-10', project_name='Portal', issuetype_name='Defect', created='2012-01-01')],
        'Demand Test': [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2011-12-26'),
                        MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect', created='2012-01-02')]
    }

    def serve_dummy_issues(self, *args, **kwargs):

        try:
            category = self.jira_config['categories'].keys()[self.jira_config['categories'].values().index(args[0])]
            
        except ValueError:
            if args[0] == "project = OPSTOOLS AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)":
                category = 'Ops Tools'
            elif args[0] == "project = Portal AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)":
                category = 'Portal'
            elif args[0] == "component = Report AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)":
                category = 'Reports'
            elif args[0] == "project = PORTAL-FAIL":
                category = 'Demand Test'
            else:
                print "Failed with:"
                print args[0]
                print self.jira_config['categories']

        return self.dummy_issues[category]

    def setUp(self):       

        mock_jira_client = mock.Mock(spec=jira.client.JIRA)
        mock_jira_client.search_issues.side_effect = self.serve_dummy_issues

        self.patcher = mock.patch('jira.client')
        self.mock_jira = self.patcher.start()
        self.mock_jira.JIRA.return_value = mock_jira_client

    def tearDown(self):
        self.patcher.stop()

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

        actual_frame = our_jira.throughput(cumulative=True,
                                           from_date=date(2012, 01, 01),
                                           to_date=date(2012, 12, 31))


        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame


    def testGetThroughputMultipleCategories(self):
        """
        The Cumulative Throughput Table is what we use to create the graph in
        Excel
        """

        our_jira = JiraWrapper(config=self.jira_config)

        expected_1 = {'Ops Tools': pd.Series([np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(1),
                                            np.int64(2),
                                            np.int64(3)],
                                            index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12'])}

        expected_frame_1 = pd.DataFrame(expected_1)

        expected_frame_1.index.name = 'week'
        expected_frame_1.columns.name = 'swimlane'

        actual_frame_1 = our_jira.throughput(cumulative=True,
                                             from_date=date(2012, 01, 01),
                                             to_date=date(2012, 12, 31),
                                             category="Ops Tools")

        assert_frame_equal(actual_frame_1.astype(np.int64), expected_frame_1), actual_frame_1

        expected_2 = {'Portal':    pd.Series([np.int64(1),
                                              np.int64(1),
                                              np.int64(1),
                                              np.int64(1),
                                              np.int64(2),
                                              np.int64(3)],
                                              index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12'])}

        expected_frame_2 = pd.DataFrame(expected_2)

        expected_frame_2.index.name = 'week'
        expected_frame_2.columns.name = 'swimlane'

        actual_frame_2 = our_jira.throughput(cumulative=True,
                                             from_date=date(2012, 01, 01),
                                             to_date=date(2012, 12, 31),
                                             category="Portal")

        assert_frame_equal(actual_frame_2.astype(np.int64), expected_frame_2), actual_frame_2


    def testFillInTheBlanks(self):
        """
        If we didn't complete any work in a given week then we will have a missing row in our data frame.
        This is going to make the graph inconsistent so we re-index to add in the missing weeks.
        """

        expected = {'Ops Tools': pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12']),
                    'Portal':    pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12']),
                    'Reports':   pd.Series([np.int64(1), np.int64(2), np.int64(3)], index=['2012-10-8', '2012-11-5', '2012-11-12'])}

        expected_frame = pd.DataFrame(expected)
        actual_index = fill_date_index_blanks(expected_frame.index)

        expected_index = ['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29', '2012-11-05', '2012-11-12']

        assert actual_index == expected_index, actual_index


    def testFillInTheBlanksOverYearEnd(self):
        """
        This is not working for the week commencing 2013-12-30.
        """

        expected = {'bi-value': pd.Series([np.int64(1)], index=['2013-12-30'])}

        expected_frame = pd.DataFrame(expected)
        actual_index = fill_date_index_blanks(expected_frame.index)

        expected_index = ['2013-12-30']

        self.assertEqual(actual_index, expected_index)


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

        unstub()
        # Given these issue in Jira

        # For our test data we want to cover value and failure demand and operational overhead.
        # We are only interested in the week that each issue was resolved.

        issue_types = {'Defect':          ['2012-10-08',
                                           '2012-10-15',
                                           '2012-10-22', '2012-10-22',
                                           '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29',
                                           '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05',
                                           '2012-11-12'],
                       'Task':            ['2012-10-08',
                                           '2012-10-15', '2012-10-15',
                                           '2012-10-22', '2012-10-22', '2012-10-22',
                                           '2012-10-29',
                                           '2012-11-05', '2012-11-05', '2012-11-05',
                                           '2012-11-12', '2012-11-12'],
                       'Improve Feature': ['2012-10-08',
                                           '2012-10-15', '2012-10-15', '2012-10-15', '2012-10-15', '2012-10-15',
                                           '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22',
                                           '2012-10-29', '2012-10-29',
                                           '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05',
                                           '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12']}

        dummy_issues = []
        n = 0

        for issue_type in issue_types:
            for resolved in issue_types[issue_type]:
                dummy_issues.append(MockIssue(key='PORTAL-{n}'.format(n=n),
                                              resolution_date=resolved,
                                              project_name='Portal',
                                              issuetype_name=issue_type,
                                              created='2012-01-01'))
                n += 1

        mock_jira = jira.client.JIRA()

        when(mock_jira).search_issues(any(),
                                      startAt=any(),
                                      maxResults=any()).thenReturn(dummy_issues)

        when(jira.client).JIRA(any(), basic_auth=any()).thenReturn(mock_jira)



        expected = {'PORTAL-value':    pd.Series([ np.int64(1),  np.int64(5),  np.int64(7),  np.int64(2),   np.int64(6),  np.int64(6)],
                                           index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29',  '2012-11-05', '2012-11-12']),
                    'PORTAL-failure':  pd.Series([ np.int64(1),  np.int64(1),  np.int64(2),  np.int64(10),  np.int64(4),  np.int64(1)],
                                           index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29',  '2012-11-05', '2012-11-12']),
                    'PORTAL-overhead': pd.Series([ np.int64(1),  np.int64(2),  np.int64(3),  np.int64(1),   np.int64(3),  np.int64(2)],
                                           index=['2012-10-08', '2012-10-15', '2012-10-22', '2012-10-29',  '2012-11-05', '2012-11-12'])}

        expected_frame = pd.DataFrame(expected)
        expected_frame.index.name = 'week'
        expected_frame.columns.name = 'swimlane'

        # We are only test one category here so override the default test config
        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'PORTAL': 'project = PORTAL'}

        our_jira = JiraWrapper(config=jira_config)

        # We typically are not interested in this data cumulatively as we want to compare how we are split on a week by week basis

        actual_frame = our_jira.throughput(cumulative=False,
                                           from_date=date(2012, 01, 01),
                                           to_date=date(2012, 12, 31),
                                           types=["value", "failure", "overhead"])

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    def testGetFailureDemandCreatedOverTime(self):

        """
        How much failure demand are we creating?  Is it going up or down?
        """

        # We are only test one category here so override the default test config
        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'Demand Test': 'project = PORTAL-FAIL'}

        expected = {'Demand Test-failure': pd.Series([np.int64(1),
                                      np.int64(1)],
                                      index=['2011-12-26', '2012-01-02'])}

        expected_frame = pd.DataFrame(expected)
        expected_frame.index.name = 'week_created'
        expected_frame.columns.name = 'swimlane'

        our_jira = JiraWrapper(config=jira_config)

        actual_frame = our_jira.demand(from_date=date(2012, 01, 01),
                                       to_date=date(2012, 12, 31),
                                       types=["failure"])


        assert_frame_equal(actual_frame, expected_frame), actual_frame

        # needs to deal with blanks!

    def testGetMitchells(self):

        """
        After Benjamin Mitchell's item history tracking:
        http://blog.benjaminm.net/2012/06/26/how-to-study-the-flow-or-work-with-kanban-cards
        """

        expected = {'PORTAL-1': pd.Series(['In Progress',
                                           'In Progress',
                                           'pending',
                                           'pending',
                                           'pending',
                                           'pending',
                                           'Customer Approval'], 
                                          index=pd.to_datetime(['2012-01-01',
                                                 '2012-01-02',
                                                 '2012-01-03',
                                                 '2012-01-04',
                                                 '2012-01-05',
                                                 '2012-01-06',
                                                 '2012-01-07'])),
                    'PORTAL-2': pd.Series(['In Progress',
                                           'In Progress',
                                           'In Progress',
                                           'pending',
                                           'pending',
                                           'Customer Approval',
                                           'Customer Approval'], 
                                          index=pd.to_datetime(['2012-01-01',
                                                 '2012-01-02',
                                                 '2012-01-03',
                                                 '2012-01-04',
                                                 '2012-01-05',
                                                 '2012-01-06',
                                                 '2012-01-07'])),
                    'PORTAL-3': pd.Series(['In Progress',
                                           'In Progress',
                                           'In Progress',
                                           'In Progress',
                                           'In Progress',
                                           'pending',
                                           'Customer Approval'], 
                                          index=pd.to_datetime(['2012-01-01',
                                                 '2012-01-02',
                                                 '2012-01-03',
                                                 '2012-01-04',
                                                 '2012-01-05',
                                                 '2012-01-06',
                                                 '2012-01-07']))}

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                   mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                   mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                          mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                          mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                          mockHistory(u'2012-01-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                          mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                          mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                          mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        our_jira = JiraWrapper(config=self.jira_config)
        expected_frame = pd.DataFrame(expected)

        actual_frame = our_jira.history(until_date=date(2012, 1, 8))

        assert_frame_equal(actual_frame, expected_frame), actual_frame


    def testCreateCFD(self):
        """
        If we sort the Mitchells by day and then by state then we get a
        Cumulative Flow Diagram
        """

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                   mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                   mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                                   mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                                   mockHistory(u'2012-01-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                                   mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                                   mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                                   mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        expected = {pd.to_datetime('2012-01-01'): pd.Series([START_STATE, START_STATE, START_STATE], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-02'): pd.Series([START_STATE, START_STATE, START_STATE], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-03'): pd.Series([START_STATE, START_STATE, 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-04'): pd.Series([START_STATE, 'pending', 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-05'): pd.Series([START_STATE, 'pending', 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-06'): pd.Series(['pending', 'pending', 'Customer Approval'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-07'): pd.Series(['Customer Approval', 'Customer Approval', 'Customer Approval'], index=[0, 1, 2])}

        our_jira = JiraWrapper(config=self.jira_config)

        expected_frame = pd.DataFrame(expected)

        actual_frame = our_jira.cfd(until_date=date(2012, 1, 8))
        # actual_frame = our_jira._issues_from_jira()

        assert_frame_equal(actual_frame, expected_frame), actual_frame



      # Test get done_value - done_value = our_jira.done[our_jira.done['type'].isin(["New Feature", "Story", "Improvement"])]


    def testGetArrivalRate(self):
        """
        What rate does work transition into a specific state?
        e.g. arrive at the customer review queue.

        This is to deal with situations where work is not being closed and so does not have a resoultion date and
        so cannot be counted towards throughput
        """

        our_jira = JiraWrapper(config=self.jira_config)

        # Set up the dummy issue history to give us our expected arrival rate

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Reports']:
            dummy_issue.changelog = None

        self.dummy_issues['Ops Tools'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'QA Queue')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'QA Queue', 'Customer Approval')])])

        expected = {
            pd.to_datetime('2012-01-02'): {'QA Queue': np.int64(1), 'Customer Approval': np.int64(1)}
        }

        expected_frame = pd.DataFrame.from_dict(expected, orient='index').sort_index(axis=1)
        actual_frame = our_jira.arrival_rate(date(2012,1,1), date(2012,1,3)).sort_index(axis=1)

        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame

    @unittest.skip("We need to be able to deal with workflows where there is no queue before work actually starts")
    def testCycleStartsWithOpen(self):
        pass


    @unittest.skip("Warning Yak Shaving Ahead")
    def testGetCustomFields(self):
        # To get custom fields you need to know what they are called
        # by looking thme up in https://instance/rest/api/2/field
        # e.g.
        # {"id":"customfield_10002","name":"Story Points","custom":true,"orderable":true,"navigable":true,"searchable":true,"schema":{"type":"number","custom":"com.atlassian.jira.plugin.system.customfieldtypes:float","customId":10002}},{"id":"customfield_10003","name":"Business Value","custom":true,"orderable":true,"navigable":true,"searchable":true,"schema":{"type":"number","custom":"com.atlassian.jira.plugin.system.customfieldtypes:float","customId":10003}}
        # These are going to need to be specified in the config file and mapped to their internal Jira names
        # MVP would be for this mapping to be provided in the config file
        pass

    @unittest.skip("Pass the clippers")
    def testSpecifyDoneState(self):
        # Depending on the workflow 'Done' will have a different definition - i.e. is it 'Done', 'Closed', 'Resolved' etc
        pass

    def testGetSingleCycleAsHistogram(self):
        """
        Get Cycle Time as Histogram for a single cycle
        """

        # We need some issues with start and end dates that fall into different buckets
        # TODO: Refactor this to remove duplication in other tests

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Reports']:
            dummy_issue.changelog = None

        # 0-5

        self.dummy_issues['Ops Tools'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])


        self.dummy_issues['Ops Tools'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        # 6-10

        self.dummy_issues['Ops Tools'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Portal'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Portal'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-08T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Portal'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-09T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-09T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-10T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])


        # 11-20

        self.dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-15T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])


        our_jira = JiraWrapper(config=self.jira_config)
        actual_frame = our_jira.cycle_time_histogram(cycle='develop', buckets=[0, 6, 11, 'max'])

        expected = [
            {'bucket': '0-5',   'develop': 2},
            {'bucket': '6-10',  'develop': 6},
            {'bucket': '11-15', 'develop': 1}
        ]

        expected_frame = pd.DataFrame(expected).set_index('bucket')

        assert_frame_equal(actual_frame, expected_frame), actual_frame


    def testCycleTimeHistogramsWithNones(self):
        """
        Deal with cycle time data containing Nones - i.e. work item has not gone through cycle we are reporting on
        """

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Reports']:
            dummy_issue.changelog = None

        # 0-5

        self.dummy_issues['Ops Tools'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])


        self.dummy_issues['Portal'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', 'In Progress', 'pending')])])


        our_jira = JiraWrapper(config=self.jira_config)
        actual_frame = our_jira.cycle_time_histogram(cycle='develop', buckets=[0,2,4])

        expected = [
            {'bucket': '0-1',  'develop': 0},
            {'bucket': '2-4',  'develop': 1}
        ]

        expected_frame = pd.DataFrame(expected).set_index('bucket')

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    def testGetMultipleTypesCycleTime(self):
        """
        Get histogram for multiple types.  
        """

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Reports']:
            dummy_issue.changelog = None

        # Failure

        self.dummy_issues['Ops Tools'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Ops Tools'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        # Value

        self.dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        our_jira = JiraWrapper(config=self.jira_config)

        actual_frame = our_jira.cycle_time_histogram(cycle='develop', types=['value', 'failure'], buckets=[0,2,5,6])

        expected = [
            {'bucket': '0-1', 'failure-develop': 1, 'value-develop': 0},
            {'bucket': '2-4', 'failure-develop': 0, 'value-develop': 2},
            {'bucket': '5-6', 'failure-develop': 1, 'value-develop': 1}
        ]

        expected_frame = pd.DataFrame(expected).set_index('bucket')

        assert_frame_equal(actual_frame, expected_frame), actual_frame


    def testMakeHistogramBucketLabels(self):
        """
        Make histogram bucket labels based on the bin edges used
        """

        expected = ['0-5', '6-10', '11-20']

        actual = bucket_labels([0, 6, 11, 20])

        self.assertEqual(actual, expected)



    def testFailGracefullyIfMissingStates(self):
        """
        If we are missing states in the CFD report then exit and tell user which state is missing
        """
        jira_config = copy.copy(self.jira_config)
        jira_config['states'] = []
        our_jira = JiraWrapper(config=jira_config)

        for dummy_issue in self.dummy_issues['Ops Tools']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Portal']:
            dummy_issue.changelog = None

        for dummy_issue in self.dummy_issues['Reports']:
            dummy_issue.changelog = None

        self.dummy_issues['Ops Tools'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                          mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.assertRaises(MissingState, our_jira.cfd, until_date=date(2012, 1, 8))

    def testFailGracefullyIfMissingConfigParams(self):

        jira_config = copy.copy(self.jira_config)
        jira_config.pop('types', None)
        self.assertRaises(MissingConfigItem, JiraWrapper, config=jira_config)

    def testGetTotalsInStates(self):
        """
        We just want the headline figures on our WIP levels and queue lengths across the Project Portfolio.
        """

        expected = [
            {'Ops Tools': { 'queued': 10, 'in progress': 5, 'customer queue': 1},
             'Portal':    { 'queued':  0, 'in progress': 2, 'customer queue': 5},
             'Reports':   { 'queued':  2, 'in progress': 4, 'customer queue': 5}}
        ]