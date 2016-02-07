# -*- coding: utf-8 -*-
"""
Test the Trello API Wrapper
"""

import unittest
from datetime import datetime
from dateutil.tz import tzutc

import trello
from mock import patch, Mock
import copy

from jlf_stats.trello_wrapper import TrelloWrapper
from jlf_stats.work import WorkItem


class TestGetMetrics(unittest.TestCase):

    def setUp(self):

        self.key = 'my_key'
        self.token = 'my_token'

        self.config = {'source': {'member': 'worldofchris',
                                  'key': 'my_key',
                                  'token': 'my_token'},
                       'types':  {'value': ['Data Request', 'Improve Feature'],
                                  'failure': ['Defect'],
                                  'overhead': ['Task',
                                               'Infrastructure',
                                               'Operational Overhead']}}

    @patch('jlf_stats.trello_wrapper.TrelloApi')
    def testGetWorkItemsFromTrelloBoardActions(self, TrelloApi):
        """
        To get the complete history of a Trello card you have to use the Board actions
        rather than the Card Actions.  This is because Trello re-writes the card history
        when it transitions from one Board to another.
        """

        mock_api = Mock(spec=trello.TrelloApi)
        mock_members = Mock(spec=trello.members)
        mock_members.get_board = Mock(return_value=[{'name': 'my_board', 'id': 'my_id'}])
        mock_api.members = mock_members

        mock_cards = Mock(spec=trello.cards)
        mock_cards.get = Mock(return_value={u'labels': [],
                                            u'pos': 16384,
                                            u'manualCoverAttachment': False,
                                            u'id': u'56ae35346b23ea1d6843a67f',
                                            u'badges': {u'votes': 0, u'attachments': 0, u'subscribed': False, u'due': None, u'comments': 0, u'checkItemsChecked': 0, u'fogbugz': u'', u'viewingMemberVoted': False, u'checkItems': 0, u'description': False},
                                            u'idBoard': u'56ae35260b361ede7bfbb1ba',
                                            u'idShort': 1,
                                            u'due': None,
                                            u'shortUrl': u'https://trello.com/c/J6st5pG8',
                                            u'closed': False,
                                            u'email': u'worldofchris+559248f3a0cca5aeb0277db6+56ae35346b23ea1d6843a67f+30732777657422f6175f86dd9f66194338bb7c60@boards.trello.com',
                                            u'dateLastActivity': u'2016-01-31T16:24:36.264Z',
                                            u'idList': u'56ae352bee563becb21b3b82',
                                            u'idLabels': [],
                                            u'idMembers': [],
                                            u'checkItemStates': [],
                                            u'desc': u'',
                                            u'descData': None,
                                            u'name': u'Card One',
                                            u'url': u'https://trello.com/c/J6st5pG8/1-card-one',
                                            u'idAttachmentCover': None,
                                            u'idChecklists': []})
        mock_api.cards = mock_cards

        mock_boards = Mock(spec=trello.boards)
        mock_boards.get_action = Mock(return_value=[{u'type': u'updateCard', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:36.269Z', u'data': {u'listBefore': {u'name': u'Three', u'id': u'56ae35296061372e997c0321'}, u'old': {u'idList': u'56ae35296061372e997c0321'}, u'board': {u'id': u'56ae35260b361ede7bfbb1ba', u'name': u'API Test 001', u'shortLink': u'l4YiX1fv'}, u'card': {u'idShort': 1, u'id': u'56ae35346b23ea1d6843a67f', u'name': u'Card One', u'idList': u'56ae352bee563becb21b3b82', u'shortLink': u'J6st5pG8'}, u'listAfter': {u'name': u'Four', u'id': u'56ae352bee563becb21b3b82'}}, u'id': u'56ae35444acfaca041099908'},
                                                    {u'type': u'moveCardToBoard', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:29.768Z', u'data': {u'boardSource': {u'name': u'API Test 000', u'id': u'56ae351097460cd456a5f323'}, u'list': {u'name': u'Three', u'id': u'56ae35296061372e997c0321'}, u'board': {u'id': u'56ae35260b361ede7bfbb1ba', u'name': u'API Test 001', u'shortLink': u'l4YiX1fv'}, u'card': {u'idShort': 1, u'id': u'56ae35346b23ea1d6843a67f', u'name': u'Card One', u'shortLink': u'J6st5pG8'}}, u'id': u'56ae353d1fd6686e1baa1d93'},
                                                    {u'type': u'createCard', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:20.398Z', u'data': {u'list': {u'name': u'List One', u'id': u'56ae3514326fd4436da31bbf'}, u'board': {u'name': u'API Test 001', u'id': u'56ae35260b361ede7bfbb1ba'}, u'card': {u'idShort': 1, u'id': u'56ae35346b23ea1d6843a67f', u'name': u'Card One', u'shortLink': u'J6st5pG8'}}, u'id': u'56ae35346b23ea1d6843a680'},
                                                    {u'type': u'createList', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:11.845Z', u'data': {u'list': {u'name': u'Four', u'id': u'56ae352bee563becb21b3b82'}, u'board': {u'id': u'56ae35260b361ede7bfbb1ba', u'name': u'API Test 001', u'shortLink': u'l4YiX1fv'}}, u'id': u'56ae352bee563becb21b3b83'},
                                                    {u'type': u'createList', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:09.766Z', u'data': {u'list': {u'name': u'Three', u'id': u'56ae35296061372e997c0321'}, u'board': {u'id': u'56ae35260b361ede7bfbb1ba', u'name': u'API Test 001', u'shortLink': u'l4YiX1fv'}}, u'id': u'56ae35296061372e997c0322'},
                                                    {u'type': u'createBoard', u'idMemberCreator': u'559248f3a0cca5aeb0277db6', u'memberCreator': {u'username': u'worldofchris', u'fullName': u'Chris Young', u'initials': u'CY', u'id': u'559248f3a0cca5aeb0277db6', u'avatarHash': u'1171b29b10de82b6a77187b79d8b9a41'}, u'date': u'2016-01-31T16:24:06.359Z', u'data': {u'board': {u'id': u'56ae35260b361ede7bfbb1ba', u'name': u'API Test 001', u'shortLink': u'l4YiX1fv'}}, u'id': u'56ae35260b361ede7bfbb1bc'}])

        mock_api.boards = mock_boards

        mock_lists = Mock(spec=trello.lists)
        mock_lists.get = Mock(return_value={u'pos': 131071,
                                            u'idBoard': u'56ae35260b361ede7bfbb1ba',
                                            u'id': u'56ae352bee563becb21b3b82',
                                            u'closed': False,
                                            u'name':
                                            u'Four'})
        mock_api.lists = mock_lists

        TrelloApi.return_value = mock_api

        our_trello = TrelloWrapper(self.config)

        expected_history = [{'from': u'Open',
                             'to':   u'Develop',
                             'timestamp': datetime(2015, 11, 01, 15, 26, 37, 204000, tzinfo=tzutc())},
                            {'from': u'Develop',
                             'to':   u'Review',
                             'timestamp': datetime(2016, 01, 10, 15, 26, 37, 204000, tzinfo=tzutc())}]

        expected = [WorkItem(id=237,
                             state="Closed",
                             title="Engine not working, throwing up this for no reason",
                             type="Operational Overhead",
                             category="Awesome Software",
                             date_created=datetime(2015, 11, 11, 18, 9, 0),
                             history=expected_history)]

        actual = our_trello.work_items_from_board_actions('my_board')

        self.assertEqual(actual[0].to_JSON(),
                         expected[0].to_JSON(),
                         msg="{0}\n{1}".format(actual[0].to_JSON(),
                                               expected[0].to_JSON()))


    def testAddStateTransitionsToExistingWorkItem(self):
        pass


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

    def testGetStateTransitionAcrossBoardBoundary(self):
        pass

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
