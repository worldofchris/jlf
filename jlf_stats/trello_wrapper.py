"""
Wrapper around the Trello API to get data out and into a
common format for reporting on.
"""

from datetime import datetime
from trello import TrelloApi
import dateutil.parser
import operator

from jlf_stats.work import WorkItem


class TrelloWrapper(object):
    """
    Wrapper around a the Trolly/Trello API
    """

    def __init__(self, config):

        self.trello = TrelloApi(config['source']['key'],
                                token=config['source']['token'])

        self.member = config['source']['member']
        self.types = config['types']
        if 'categories' in config:
            self.categories = config['categories']
        self._work_items = []

    def work_items(self):
        """
        Get work items from the Trello boards that make up the category
        """
        cards = []
        boards = self.trello.members.get_board(self.member)
        for category in self.categories:
            for board_name in self.categories[category]:
                print board_name
                board = next((board for board in boards if board['name'] == board_name), None)
                board_cards = self.trello.boards.get_card(board['id'])
                cards.extend(board_cards)

        for card in cards:
            work_item = self.work_item_from_card(card)
            self._work_items.append(work_item)

        return self._work_items

    def work_item_from_card(self, card):
        """
        Get a work item from a Trello card
        """

        current_list_name = self.trello.cards.get_list(card['id'])['name']

        work_item_type = None

        for work_types in self.types:
            for type_label in self.types[work_types]:
                for label in card['labels']:
                    if label['name'] == type_label:
                        work_item_type = label['name']

        date_created = datetime.fromtimestamp(int(card['id'][0:8], 16))

        actions = self.trello.cards.get_action(card['id'])
        history = []
        if actions is not None:
            for action in actions:
                if action['type'] == u'updateCard':
                    history.append(TrelloWrapper.state_transition(action))

        history.sort(key=operator.itemgetter('timestamp'))

        work_item = WorkItem(id=card['idShort'],
                             state=current_list_name,
                             title=card['name'],
                             type=work_item_type,
                             category="Awesome Software",
                             date_created=date_created,
                             history=history)

        return work_item

    @classmethod
    def state_transition(cls, update_action):
        """
        Get a state transition from an update action
        """
        state_transition = {'from': update_action['data']['listBefore']['name'],
                            'to':   update_action['data']['listAfter']['name'],
                            'timestamp':  dateutil.parser.parse(update_action['date'])}

        return state_transition
