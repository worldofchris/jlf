"""
Wrapper around the Trello API to get data out and into a
common format for reporting on.
"""

from datetime import datetime, date, timedelta
from trello import TrelloApi
import dateutil.parser
import operator

from jlf_stats.history import remove_gaps_from_state_transitions
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

        self.boards = self.trello.members.get_board(self.member)

        self.from_date = date(2015, 5, 1)
        self.until_date = date(2016, 2, 1)

    def work_items(self):
        """
        Get work items from the Trello boards that make up the category
        """
        cards = []
        for category in self.categories:
            for board_name in self.categories[category]:
                board = next((board for board in self.boards if board['name'] == board_name), None)
                self.work_items_from_board_actions(board['name'], category=category)

        for work_item in self._work_items:
            work_item.history = remove_gaps_from_state_transitions(work_item.history)

        return self._work_items

    def work_items_from_board_actions(self, board_name, category="all"):
        """
        Get all the work items in a boards history of actions
        """
        board = next((board for board in self.boards if board['name'] == board_name), None)

        actions = []
        limit = 1000
        since = self.from_date
        before = since + timedelta(days=1)
        while before < self.until_date:
            for filter in ['createCard', 'updateCard', 'moveCardToBoard', 'moveCardFromBoard']:
                batch = self.trello.boards.get_action(board['id'], limit=limit, filter=filter, since=str(since), before=str(before))
                actions.extend(batch)
                print len(actions)

            since = since + timedelta(days=1)
            before = before + timedelta(days=1)

        print board['name'] + ' has ' + str(len(actions)) + ' actions.'
        for action in actions:
            if action['type'] in ['updateCard', 'moveCardToBoard', 'createCard']:
                card_id = action['data']['card']['id']

                work_item = next((work_item for work_item in self._work_items if work_item.id == card_id), None)

                state_transition = TrelloWrapper.state_transition(action)

                if work_item is not None:
                    if state_transition is not None:
                        work_item.history.append(state_transition)
                        work_item.history.sort(key=operator.itemgetter('timestamp'))

                else:
                    card = self.trello.cards.get(card_id)

                    # Add the action
                    history = []
                    if state_transition is not None:
                        history = [state_transition]

                    date_created = datetime.fromtimestamp(int(card['id'][0:8], 16))
                    card_list = self.trello.lists.get(card['idList'])

                    work_item_type = None

                    for work_types in self.types:
                        for type_label in self.types[work_types]:
                            for label in card['labels']:
                                if label['name'] == type_label:
                                    work_item_type = label['name']

                    work_item = WorkItem(id=card['id'],
                                         state=card_list['name'],
                                         title=card['name'],
                                         type=work_item_type,
                                         category=category,
                                         date_created=date_created,
                                         history=history)

                    self._work_items.append(work_item)

                if action['type'] == 'createCard':
                    # Update the Created Date from the Create Action
                    date_created = state_transition['timestamp']
                    work_item.date_created = date_created

        return self._work_items

    @classmethod
    def state_transition(cls, action):
        """
        Get a state transition from an action
        """

        if action['type'] == 'updateCard':
            if 'listAfter' in action['data']:
                to_state = action['data']['listAfter']['name']
            else:
                return None
            from_state = action['data']['listBefore']['name']
        elif action['type'] == 'moveCardToBoard':
            to_state = action['data']['list']['name']
            from_state = None
        elif action['type'] == 'moveCardFromBoard':
            to_state = None
            from_state = action['data']['list']['name']
        elif action['type'] == 'createCard':
            from_state = 'CREATED'
            to_state = action['data']['list']['name']
        else:
            return None

        state_transition = {'from':      from_state,
                            'to':        to_state,
                            'timestamp': dateutil.parser.parse(action['date'])}

        return state_transition
