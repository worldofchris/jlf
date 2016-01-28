# -*- coding: utf-8 -*-
"""
Test the Trello API Wrapper
"""

import unittest
from datetime import datetime
from dateutil.tz import tzutc

import mock
import trolly

from jlf_stats.trello_wrapper import TrelloWrapper
from jlf_stats.work import WorkItem


class TestGetMetrics(unittest.TestCase):

    def setUp(self):

        self.key = 'my_key'
        self.token = 'my_token'

        self.patcher = mock.patch('trolly.client')
        self.mock_trolly = self.patcher.start()

        mock_client = mock.Mock(spec=trolly.client.Client)
        self.mock_trolly.Client.return_value = mock_client

    def testGetWorkItemFromTrelloCard(self):

        our_trello = TrelloWrapper()

        client = trolly.client.Client(self.key, self.token)
        card_id = '55a113FFFFFa5c9b5150e79'
        card_name = 'Paint Castle'
        card_kwargs = {'data': {u'labels': [{u'color': u'purple',
                                             u'uses': 68, u'id': u'55a524e019ad3a5dc2cd00d3',
                                             u'idBoard': u'55a524e0efbb13f4109fb5ed', u'name': u'Operational Overhead'}],
                                u'idList': u'55b8807b43e41cda58ee361b',
                                u'name': u'Sending SD Material to HD Destinations - SKY UPDATE'}}

        expected = WorkItem(id="1838",
                            state="Closed (Fixed)",
                            title="Engine not working, throwing up this for no reason",
                            type="Bug",
                            category="wat",
                            date_created=datetime(2015, 03, 04, 12, 15, 41, tzinfo=tzutc()),
                            history=None)

        card = trolly.card.Card(client,
                                card_id,
                                card_name,
                                **card_kwargs)

        actual = our_trello.work_item_from_card(card)

        self.assertEqual(actual.to_JSON(), expected.to_JSON())

        # trolly.client.Client


    # def testGetStateTransitionFromTrelloUpdateAction(self):
    #     pass
