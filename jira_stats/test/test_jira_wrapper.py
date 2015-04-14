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

import os

# Shell Mocks to deal with the indirection needed to get us down to the
# things we actually want to mock


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
                 created=None,
                 change_log=None):

        self.key = key
        self.fields = MockFields(resolution_date,
                                 project_name,
                                 issuetype_name,
                                 created)
        self.project = MockProject(project_name)
        self.category = None
        self.changelog = change_log
        self.created = created


class TestGetMetrics(unittest.TestCase):

    categories = {
        'Portal':    'project = Portal',
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

    states = ['In Progress', 'pending', 'Customer Approval']

    jira_config = {
        'server': 'jiratron.worldofchris.com',
        'authentication': {
            'username': 'mrjira',
            'password': 'foo'
        },
        'categories': categories,
        'cycles': cycles,
        'types': types,
        'states': states,
        'counts_towards_throughput': [END_STATE],
        'throughput_dow': 0
    }

    # There are the sets of issues to match the categories that get searched for in the tests

    default_queries = {"project = OPSTOOLS AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)": "Ops Tools",
                       "project = Portal AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)": "Portal",
                       "component = Report AND issuetype in standardIssueTypes() AND resolution in (Fixed) AND status in (Closed)": "Reports",
                       "project = PORTAL-FAIL": "Demand Test",
                       "totals_test": "totals_test"}

    default_dummy_issues = {
        'Ops Tools':   [MockIssue(key='OPSTOOLS-1',
                                  resolution_date='2012-11-10',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='OPSTOOLS-2',
                                  resolution_date='2012-11-12',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='OPSTOOLS-3',
                                  resolution_date='2012-10-10',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]))],
        'Portal':      [MockIssue(key='PORTAL-1',
                                  resolution_date='2012-11-10',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='PORTAL-2',
                                  resolution_date='2012-11-12',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='PORTAL-3',
                                  resolution_date='2012-10-10',
                                  project_name='Portal',
                                  issuetype_name='Defect',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]))],
        'Reports':     [MockIssue(key='REPORTS-1',
                                  resolution_date='2012-11-10',
                                  project_name='Portal',
                                  issuetype_name='Data Request',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-10-08T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='REPORTS-2',
                                  resolution_date='2012-11-12',
                                  project_name='Portal',
                                  issuetype_name='Improve Feature',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-04T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])),
                        MockIssue(key='REPORTS-3',
                                  resolution_date='2012-10-10',
                                  project_name='Portal',
                                  issuetype_name='Improve Feature',
                                  created='2012-01-01',
                                  change_log=MockChangelog([mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                            mockHistory(u'2012-11-12T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])]))],
        'Demand Test': [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2011-12-26'),
                        MockIssue(key='PORTAL-2', resolution_date='2012-11-12', project_name='Portal', issuetype_name='Defect', created='2012-01-02')],
        'totals_test': [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2011-12-26')]
    }

    def set_dummy_issues(self, issues=None, queries=None, config=None):

        print "Setting dummy issues"
        # If no issues are specified use the default set
        if issues is not None:
            self.dummy_issues = issues
        else:
            self.dummy_issues = self.default_dummy_issues

        # If no queries are specified use the default mappings:
        if queries is not None:
            self.queries = queries
        else:
            self.queries = self.default_queries

        if config is None:
            config = self.jira_config

        for category, query in config['categories'].iteritems():
            self.queries[query] = category

    def serve_dummy_issues(self, *args, **kwargs):

        category = None

        try:
            category = self.queries[args[0]]

        except ValueError:
            print "Failed with:"
            print args[0]
            return None

        return self.dummy_issues[category]

    def setUp(self):

        mock_jira_client = mock.Mock(spec=jira.client.JIRA)
        mock_jira_client.search_issues.side_effect = self.serve_dummy_issues
        self.set_dummy_issues()

        self.patcher = mock.patch('jira.client')
        self.mock_jira = self.patcher.start()
        self.mock_jira.JIRA.return_value = mock_jira_client

    def tearDown(self):
        self.patcher.stop()

    def testGetIssueByKey(self):
        """
        Issues can be queried by key
        """

        our_jira = JiraWrapper(config=self.jira_config)
        issue = our_jira.issue('OPSTOOLS-1')

        self.assertEqual(issue.category, "Ops Tools")

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
                                           to_date=date(2012, 11, 13))

        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame

    def testGetThroughputMultipleCategories(self):
        """
        Cumulative Throughput Table - Multiple Categories
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
                                             to_date=date(2012, 11, 13),
                                             category="Ops Tools")

        assert_frame_equal(actual_frame_1.astype(np.int64), expected_frame_1), actual_frame_1

        expected_2 = {'Portal':        pd.Series([np.int64(1),
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
                                             to_date=date(2012, 11, 13),
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

        # Given these issue in Jira

        # For our test data we want to cover value and failure demand and operational overhead.
        # We are only interested in the week that each issue was resolved.

        issue_types = {'Defect':            ['2012-10-08',
                                             '2012-10-15',
                                             '2012-10-22', '2012-10-22',
                                             '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29', '2012-10-29',
                                             '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05',
                                             '2012-11-12'],
                       'Task':              ['2012-10-08',
                                             '2012-10-15', '2012-10-15',
                                             '2012-10-22', '2012-10-22', '2012-10-22',
                                             '2012-10-29',
                                             '2012-11-05', '2012-11-05', '2012-11-05',
                                             '2012-11-12', '2012-11-12'],
                       'Improve Feature':   ['2012-10-08',
                                             '2012-10-15', '2012-10-15', '2012-10-15', '2012-10-15', '2012-10-15',
                                             '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22', '2012-10-22',
                                             '2012-10-29', '2012-10-29',
                                             '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05', '2012-11-05',
                                             '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12', '2012-11-12']}

        dummy_issues = {'THINGY': []}
        n = 0

        for issue_type in issue_types:
            for resolved in issue_types[issue_type]:
                dummy_issues['THINGY'].append(MockIssue(key='THINGY-{n}'.format(n=n),
                                                        resolution_date=resolved,
                                                        project_name='Portal',
                                                        issuetype_name=issue_type,
                                                        created='2012-01-01',
                                                        change_log=MockChangelog([mockHistory(u'{date}T09:54:29.284+0000'.format(date=resolved),
                                                                                              [mockItem('status',
                                                                                                        'queued',
                                                                                                        END_STATE)])])))

                n += 1

        expected = {'THINGY-value':    pd.Series([np.int64(1),
                                                  np.int64(5),
                                                  np.int64(7),
                                                  np.int64(2),
                                                  np.int64(6),
                                                  np.int64(6)],
                                                 index=pd.to_datetime(['2012-10-08',
                                                        '2012-10-15',
                                                        '2012-10-22',
                                                        '2012-10-29',
                                                        '2012-11-05',
                                                        '2012-11-12'])),
                    'THINGY-failure':  pd.Series([np.int64(1),
                                                  np.int64(1),
                                                  np.int64(2),
                                                  np.int64(10),
                                                  np.int64(4),
                                                  np.int64(1)],
                                                 index=pd.to_datetime(['2012-10-08',
                                                        '2012-10-15',
                                                        '2012-10-22',
                                                        '2012-10-29',
                                                        '2012-11-05',
                                                        '2012-11-12'])),
                    'THINGY-overhead': pd.Series([np.int64(1),
                                                  np.int64(2),
                                                  np.int64(3),
                                                  np.int64(1),
                                                  np.int64(3),
                                                  np.int64(2)],
                                                 index=pd.to_datetime(['2012-10-08',
                                                        '2012-10-15',
                                                        '2012-10-22',
                                                        '2012-10-29',
                                                        '2012-11-05',
                                                        '2012-11-12']))}

        expected_frame = pd.DataFrame(expected)
        expected_frame.index.name = 'week'
        expected_frame.columns.name = 'swimlane'

        # We are only test one category here so override the default test config
        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'THINGY': 'THINGY'}

        self.set_dummy_issues(issues=dummy_issues, queries=jira_config['categories'], config=jira_config)

        our_jira = JiraWrapper(config=jira_config)

        # We typically are not interested in this data cumulatively as we want to compare how we are split on a week by week basis

        actual_frame = our_jira.throughput(cumulative=False,
                                           from_date=date(2012, 01, 01),
                                           to_date=date(2012, 11, 13),
                                           types=["value", "failure", "overhead"])

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    def testGetFailureDemandCreatedOverTime(self):

        """
        How much failure demand are we creating? Is it going up or down?
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

        expected = {'REPORTS-1': pd.Series(['In Progress',
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
                    'REPORTS-2': pd.Series(['In Progress',
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
                    'REPORTS-3': pd.Series(['In Progress',
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

        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'Reports': 'Reports'}
        jira_config['counts_towards_throughput'] = ''
        jira_config['cycles'] = {'develop': {
            'start': START_STATE,
            'exit': 'Customer Approval'
            }
        }

        dummy_issues = {'Reports': [MockIssue(key='REPORTS-1',
                                              resolution_date='2012-11-10',
                                              project_name='Portal',
                                              issuetype_name='Data Request',
                                              created='2012-01-01'),
                                    MockIssue(key='REPORTS-2',
                                              resolution_date='2012-11-12',
                                              project_name='Portal',
                                              issuetype_name='Improve Feature',
                                              created='2012-01-01'),
                                    MockIssue(key='REPORTS-3',
                                              resolution_date='2012-10-10',
                                              project_name='Portal',
                                              issuetype_name='Improve Feature',
                                              created='2012-01-01')]}

        dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.set_dummy_issues(issues=dummy_issues, queries=jira_config['categories'], config=jira_config)

        our_jira = JiraWrapper(config=jira_config)
        expected_frame = pd.DataFrame(expected)

        actual_frame = our_jira.history(until_date=date(2012, 1, 8))

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    def testCreateCFD(self):
        """
        If we sort the Mitchells by day and then by state then we get a
        Cumulative Flow Diagram
        """

        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'Reports': 'Reports'}
        jira_config['counts_towards_throughput'] = ''
        jira_config['cycles'] = {'develop': {
            'start': START_STATE,
            'exit': 'Customer Approval'
            }
        }

        dummy_issues = {'Reports': [MockIssue(key='REPORTS-1',
                                              resolution_date='2012-11-10',
                                              project_name='Portal',
                                              issuetype_name='Data Request',
                                              created='2012-01-01'),
                                    MockIssue(key='REPORTS-2',
                                              resolution_date='2012-11-12',
                                              project_name='Portal',
                                              issuetype_name='Improve Feature',
                                              created='2012-01-01'),
                                    MockIssue(key='REPORTS-3',
                                              resolution_date='2012-10-10',
                                              project_name='Portal',
                                              issuetype_name='Improve Feature',
                                              created='2012-01-01')]}

        dummy_issues['Reports'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-03T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-04T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', START_STATE)]),
                                                              mockHistory(u'2012-01-06T09:54:29.284+0000', [mockItem('status', START_STATE, 'pending')]),
                                                              mockHistory(u'2012-01-07T09:54:29.284+0000', [mockItem('status', 'pending', END_STATE)])])

        self.set_dummy_issues(issues=dummy_issues, queries=jira_config['categories'], config=jira_config)

        expected = {pd.to_datetime('2012-01-01'): pd.Series([START_STATE, START_STATE, START_STATE], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-02'): pd.Series([START_STATE, START_STATE, START_STATE], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-03'): pd.Series([START_STATE, START_STATE, 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-04'): pd.Series([START_STATE, 'pending', 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-05'): pd.Series([START_STATE, 'pending', 'pending'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-06'): pd.Series(['pending', 'pending', 'Customer Approval'], index=[0, 1, 2]),
                    pd.to_datetime('2012-01-07'): pd.Series(['Customer Approval', 'Customer Approval', 'Customer Approval'], index=[0, 1, 2])}

        our_jira = JiraWrapper(config=jira_config)

        expected_frame = pd.DataFrame(expected)
        actual_frame = our_jira.cfd(until_date=date(2012, 1, 8))

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    @unittest.skip("FIXME")
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
        actual_frame = our_jira.arrival_rate(date(2012, 1, 1), date(2012, 1, 3)).sort_index(axis=1)

        assert_frame_equal(actual_frame.astype(np.int64), expected_frame), actual_frame

    @unittest.skip("This is hard coded now as only needed on one project")
    def testGetCustomFields(self):
        # To get custom fields you need to know what they are called
        # by looking thme up in https://instance/rest/api/2/field
        # e.g.
        # {"id":"customfield_10002","name":"Story Points","custom":true,"orderable":true,"navigable":true,"searchable":true,"schema":{"type":"number","custom":"com.atlassian.jira.plugin.system.customfieldtypes:float","customId":10002}},{"id":"customfield_10003","name":"Business Value","custom":true,"orderable":true,"navigable":true,"searchable":true,"schema":{"type":"number","custom":"com.atlassian.jira.plugin.system.customfieldtypes:float","customId":10003}}
        # These are going to need to be specified in the config file and mapped to their internal Jira names
        # MVP would be for this mapping to be provided in the config file
        pass

    @unittest.skip("FIXME")
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

        # 11-12

        self.dummy_issues['Reports'][1].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                                   mockHistory(u'2012-01-10T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        self.dummy_issues['Reports'][2].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'queued', 'In Progress')]),
                                                                   mockHistory(u'2012-01-15T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')])])

        our_jira = JiraWrapper(config=self.jira_config)
        actual_frame = our_jira.cycle_time_histogram(cycle='develop', buckets=[0, 6, 11, 'max'])

        expected = [
            {'bucket': '0-5',     'develop': 2},
            {'bucket': '6-10',    'develop': 6},
            {'bucket': '11-15', 'develop': 1}
        ]

        expected_frame = pd.DataFrame(expected).set_index('bucket')

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    @unittest.skip("FIXME")
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
        actual_frame = our_jira.cycle_time_histogram(cycle='develop', buckets=[0, 2, 4])

        expected = [
            {'bucket': '0-1',    'develop': 0},
            {'bucket': '2-4',    'develop': 1}
        ]

        expected_frame = pd.DataFrame(expected).set_index('bucket')

        assert_frame_equal(actual_frame, expected_frame), actual_frame

    @unittest.skip("FIXME")
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

        actual_frame = our_jira.cycle_time_histogram(cycle='develop', types=['value', 'failure'], buckets=[0, 2, 5, 6])

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

    @unittest.skip("FIXME")
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

    @unittest.skip("Skipping so I can commit the mock refactoring")
    def testGetTotalsInStates(self):
        """
        We just want the headline figures on our WIP levels and queue lengths across the Project Portfolio.
        """

        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'totals_test': 'totals_test'}

        our_jira = JiraWrapper(config=jira_config)

        expected = [
            {'Ops Tools': {'queued': 10, 'in progress': 5, 'customer queue': 1},
             'Portal':    {'queued':  0, 'in progress': 2, 'customer queue': 5},
             'Reports':   {'queued':  2, 'in progress': 4, 'customer queue': 5}}
        ]

        actual = our_jira.totals()

        self.assertEqual(expected, actual)

    def testConfigureWithBasicAuth(self):
        """
        In adding oauth we are changing the way authentication is stored in the config.    It is now
        encapsulated in its own dict.
        """

        basic_jira_config = {
            "server": "https://worldofchris.atlassian.net",
            "categories": [],
            "cycles": [],
            "types": [],
            "counts_towards_throughput": [],
            "authentication": {
                "username": "mrjira",
                "password": "234214234324"
            }
        }

        our_jira = JiraWrapper(config=basic_jira_config)

        self.mock_jira.JIRA.assert_called_with({'server': basic_jira_config['server']},
                                               basic_auth=(basic_jira_config['authentication']['username'],
                                                           basic_jira_config['authentication']['password']))

        # What can we meaningfully assert here?

    def testConfigureWithOauth(self):
        """
        We want to be able to connect to JIRA with Oauth and not just basic auth esp. if we want to make this
        available as a web service.
        """

        key_cert = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'key.pem')

        oauth_jira_config = {
            "server": "https://worldofchris.atlassian.net",
            "categories": [],
            "cycles": [],
            "types": [],
            "counts_towards_throughput": [END_STATE],
            "authentication": {
                'access_token': 'In3d5YsFmqRTDJah2gg5sNH0WM2ekKzA',
                'access_token_secret': '9COeo40njrZGgMU8GjqjdEpKye6TLDXJ',
                'consumer_key': 'jlf',
                'key_cert': key_cert
            }
        }

        with open(key_cert, 'r') as key_cert_file:
            key_cert_data = key_cert_file.read()

        our_jira = JiraWrapper(config=oauth_jira_config)

        self.mock_jira.JIRA.assert_called_with({'server': oauth_jira_config['server']},
                                               oauth={'access_token': oauth_jira_config['authentication']['access_token'],
                                                      'access_token_secret': oauth_jira_config['authentication']['access_token_secret'],
                                                      'consumer_key': oauth_jira_config['authentication']['consumer_key'],
                                                      'key_cert': key_cert_data})

    def testMissingKeyCertFile(self):

        missing_key_cert = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'missing_key.pem')

        oauth_jira_config = {
            "server": "https://worldofchris.atlassian.net",
            "categories": [],
            "cycles": [],
            "types": [],
            "counts_towards_throughput": [END_STATE],
            "authentication": {
                'access_token': 'In3d5YsFmqRTDJah2gg5sNH0WM2ekKzA',
                'access_token_secret': '9COeo40njrZGgMU8GjqjdEpKye6TLDXJ',
                'consumer_key': 'jlf',
                'key_cert': missing_key_cert
            }
        }

        self.assertRaises(MissingConfigItem, JiraWrapper, config=oauth_jira_config)

    def testGetDetail(self):
        """
        Get details of all issues - this is where cycle time currently appears.
        Might want to factor that out...
        """

        jira_config = copy.copy(self.jira_config)
        jira_config['categories'] = {'done': 'done'}
        jira_config['counts_towards_throughput'] = ''
        jira_config['cycles'] = {'develop': {
            'start': START_STATE,
            'exit': 'Customer Approval'
            }
        }

        dummy_issues = {'done': [MockIssue(key='PORTAL-1', resolution_date='2012-11-10', project_name='Portal', issuetype_name='Defect', created='2012-01-01')]}
        dummy_issues['done'][0].changelog = MockChangelog([mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', START_STATE, 'In Progress')]),
                                                           mockHistory(u'2012-01-01T09:54:29.284+0000', [mockItem('status', 'In Progress', 'Customer Approval')]),
                                                           mockHistory(u'2012-01-02T09:54:29.284+0000', [mockItem('status', 'Customer Approval', 'Done')])])

        self.set_dummy_issues(issues=dummy_issues, queries=jira_config['categories'], config=jira_config)

        our_jira = JiraWrapper(config=jira_config)

        expected = [{'id': 'PORTAL-1', 'develop': 1}]
        expected_frame = pd.DataFrame(expected).sort_index(axis=1, ascending=False)

        actual_frame = our_jira.issues(fields=['id', 'develop'])

        assert_frame_equal(actual_frame, expected_frame), actual_frame
