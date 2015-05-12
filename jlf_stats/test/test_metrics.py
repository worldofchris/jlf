from jlf_stats.fogbugz_wrapper import FogbugzWrapper
from jlf_stats.jira_wrapper import JiraWrapper

from jlf_stats.metrics import Metrics
import unittest


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
                       'server': 'http://jiratron.worldofchris.com',
                       'authentication': {'username': 'mrjira',
                                          'password': 'foo'}},
            'categories': None,
            'cycles': None,
            'types': None,
            'counts_towards_throughput': None
        }

        our_metrics = Metrics(config)
        self.assertIsInstance(our_metrics.source, JiraWrapper)
