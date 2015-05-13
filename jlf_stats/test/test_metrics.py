from jlf_stats.fogbugz_wrapper import FogbugzWrapper
from jlf_stats.jira_wrapper import JiraWrapper

from jlf_stats.metrics import Metrics
import unittest
import os

class TestMetrics(unittest.TestCase):

    def testConfigureWithFogBugz(self):
        """
        Configure Metrics so it gets its data from FogBugz
        """

        config = {
            'source': {'type': 'fogbugz',
                       'url': 'https://worldofchris.fogbugz.com',
                       'token': '33vvjghjeis7439a29qqg29azqq8q1'},
            'categories': None,
            'types': None,
            'counts_towards_throughput': None
        }

        our_metrics = Metrics(config)
        self.assertIsInstance(our_metrics.source, FogbugzWrapper)

    def testConfigureWithJira(self):

        config = {
            'source': {'type': 'jira',
                       'server': 'https://worldofchris.atlassian.net',
                       'authentication': {'username': 'readonly',
                                          'password': 'WTFFTW!'}},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        our_metrics = Metrics(config)
        self.assertIsInstance(our_metrics.source, JiraWrapper)

    def testGetPasswordFromEnvVar(self):
        """
        So we don't have to put passwords into SCM
        """

        env_var = 'TEST_PASSWORD'
        password = 'foobar123'
        os.environ[env_var] = password

        config = {
            'source': {'type': 'jira',
                       'server': 'https://worldofchris.atlassian.net',
                       'authentication': {'username': 'readonly',
                                          'password': 'ENV({0})'.format(env_var)}},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        our_metrics = Metrics(config)
        self.assertEqual(password, our_metrics.config['source']['authentication']['password'])
