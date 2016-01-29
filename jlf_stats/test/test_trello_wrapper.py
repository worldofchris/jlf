# -*- coding: utf-8 -*-
"""
Test the Trello API Wrapper
"""

import unittest
from datetime import datetime
from dateutil.tz import tzutc

import trello
import mock

from jlf_stats.trello_wrapper import TrelloWrapper
from jlf_stats.work import WorkItem


class TestGetMetrics(unittest.TestCase):

    def setUp(self):

        self.key = 'my_key'
        self.token = 'my_token'

        self.patcher = mock.patch('jlf_stats.trello_wrapper.TrelloApi')
        self.mock_trello = self.patcher.start()

        mock_cards = mock.Mock(spec=trello.cards)
        mock_cards.get_list = mock.Mock()

        mock_api = mock.Mock(spec=trello.TrelloApi)
        mock_api.cards = mock_cards

        self.mock_trello.TrelloApi.return_value = mock_api

    def testGetWorkItemFromTrelloCard(self):

        config = {'source': {'member': 'worldofchris',
                             'key': 'my_key',
                             'token': 'my_token'},
                  'types':  {'value': ['Data Request', 'Improve Feature'],
                             'failure': ['Defect'],
                             'overhead': ['Task', 'Infrastructure', 'Operational Overhead']}}

        our_trello = TrelloWrapper(config)

        expected = WorkItem(id=237,
                            state="Closed",
                            title="Engine not working, throwing up this for no reason",
                            type="Operational Overhead",
                            category="Awesome Software",
                            date_created=datetime(2015, 11, 11, 18, 9, 0),
                            history=None)

        card = {u'labels': [{u'name': u'Operational Overhead'}],
                u'id': u'5643843c0c7f274e44f18961',
                u'idBoard': u'55a524e0efbb13f4109fb5ed',
                u'idShort': 237,
                u'name': u'Engine not working, throwing up this for no reason'}

        our_trello.trello.cards.get_list.return_value = {'name': "Closed"}
        actual = our_trello.work_item_from_card(card)

        self.assertEqual(actual.to_JSON(), expected.to_JSON(), msg="{0}\n{1}".format(actual.to_JSON(), expected.to_JSON()))


    # def testGetStateTransitionFromTrelloUpdateAction(self):
    #     pass
