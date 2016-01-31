# -*- coding: utf-8 -*-
"""
Test the Trello API Wrapper
"""

import unittest
from datetime import datetime
from dateutil.tz import tzutc

import trello
import mock
import copy

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
        mock_cards.get_action = mock.Mock()

        mock_api = mock.Mock(spec=trello.TrelloApi)
        mock_api.cards = mock_cards

        self.mock_trello.TrelloApi.return_value = mock_api

        self.config = {'source': {'member': 'worldofchris',
                                  'key': 'my_key',
                                  'token': 'my_token'},
                       'types':  {'value': ['Data Request', 'Improve Feature'],
                                  'failure': ['Defect'],
                                  'overhead': ['Task',
                                               'Infrastructure',
                                               'Operational Overhead']}}

    def testGetWorkItemFromTrelloCard(self):

        our_trello = TrelloWrapper(self.config)

        expected = WorkItem(id=237,
                            state="Closed",
                            title="Engine not working, throwing up this for no reason",
                            type="Operational Overhead",
                            category="Awesome Software",
                            date_created=datetime(2015, 11, 11, 18, 9, 0),
                            history=[])

        card = {u'labels': [{u'name': u'Operational Overhead'}],
                u'id': u'5643843c0c7f274e44f18961',
                u'idBoard': u'55a524e0efbb13f4109fb5ed',
                u'idShort': 237,
                u'name': u'Engine not working, throwing up this for no reason'}

        our_trello.trello.cards.get_list.return_value = {'name': "Closed"}
        our_trello.trello.cards.get_action.return_value = None

        actual = our_trello.work_item_from_card(card)

        self.assertEqual(actual.to_JSON(),
                         expected.to_JSON(),
                         msg="{0}\n{1}".format(actual.to_JSON(),
                                               expected.to_JSON()))


    def testGetStateTransitionFromTrelloUpdateAction(self):

        update_action = {u'type': u'updateCard',
                         u'date': u'2016-01-28T15:26:37.204Z',
                         u'data': {u'listBefore': {u'name': u'Open',
                                                   u'id': u'56937b57bed0c1a3c6360ac4'},
                                   u'old': {u'idList': u'56937b57bed0c1a3c6360ac4'},
                                   u'listAfter': {u'name': u'Closed',
                                                  u'id': u'55b8a37e6cbc1c471cf77b13'}}}

        expected = {'from': u'Open',
                    'to':   u'Closed',
                    'timestamp':  datetime(2016, 01, 28, 15, 26, 37, 204000, tzinfo=tzutc())}

        actual = TrelloWrapper.state_transition(update_action)

        self.assertEqual(actual, expected)

    def testGetWorkItemWithHistory(self):
        """
        Create a work item with its history from a Trello card
        """
        our_trello = TrelloWrapper(self.config)

        actions = [{u'type': u'commentCard'},
                   {u'type': u'updateCard',
                    u'date': u'2016-01-10T15:26:37.204Z',
                    u'data': {u'listBefore': {u'name': u'In Progress',
                                              u'id': u'56937b57bed0c1a3c6360ac4'},
                              u'old': {u'idList': u'56937b57bed0c1a3c6360ac4'},
                              u'listAfter': {u'name': u'Closed',
                                             u'id': u'55b8a37e6cbc1c471cf77b13'}}},
                   {u'type': u'updateCard',
                    u'date': u'2016-01-28T15:26:37.204Z',
                    u'data': {u'listBefore': {u'name': u'Closed',
                                              u'id': u'56937b57bed0c1a3c6360ac4'},
                              u'old': {u'idList': u'56937b57bed0c1a3c6360ac4'},
                              u'listAfter': {u'name': u'Re Opened',
                                             u'id': u'55b8a37e6cbc1c471cf77b13'}}},
                   {u'type': u'updateCard',
                    u'date': u'2015-11-01T15:26:37.204Z',
                    u'data': {u'listBefore': {u'name': u'Open',
                                              u'id': u'56937b57bed0c1a3c6360ac4'},
                              u'old': {u'idList': u'56937b57bed0c1a3c6360ac4'},
                              u'listAfter': {u'name': u'In Progress',
                                             u'id': u'55b8a37e6cbc1c471cf77b13'}}}]

        expected_history = [{'from': u'Open',
                             'to':   u'In Progress',
                             'timestamp':  datetime(2015, 11, 01, 15, 26, 37, 204000, tzinfo=tzutc())},
                            {'from': u'In Progress',
                             'to':   u'Closed',
                             'timestamp':  datetime(2016, 01, 10, 15, 26, 37, 204000, tzinfo=tzutc())},
                            {'from': u'Closed',
                             'to':   u'Re Opened',
                             'timestamp':  datetime(2016, 01, 28, 15, 26, 37, 204000, tzinfo=tzutc())}]

        expected = WorkItem(id=237,
                            state="Closed",
                            title="Engine not working, throwing up this for no reason",
                            type="Operational Overhead",
                            category="Awesome Software",
                            date_created=datetime(2015, 11, 11, 18, 9, 0),
                            history=expected_history)

        card = {u'labels': [{u'name': u'Operational Overhead'}],
                u'id': u'5643843c0c7f274e44f18961',
                u'idBoard': u'55a524e0efbb13f4109fb5ed',
                u'idShort': 237,
                u'name': u'Engine not working, throwing up this for no reason'}

        our_trello.trello.cards.get_list.return_value = {'name': "Closed"}
        our_trello.trello.cards.get_action.return_value = actions

        actual = our_trello.work_item_from_card(card)

        our_trello.trello.cards.get_action.assert_called_once_with(card['id'])
        self.assertEqual(actual.history, expected_history)

        self.assertEqual(actual.to_JSON(), expected.to_JSON())

    def testGetCardsFromBoard(self):

        config = copy.copy(self.config)
        config['categories'] = {"Work": ["My Board"]}

        our_trello = TrelloWrapper(config)
        actual = our_trello.work_items()

    @unittest.skip("FIXME")
    def testConnectToTrello(self):
        """
        Make sure we can connect to Trello itself
        """
        our_trello = TrelloWrapper(self.config)
        pass
