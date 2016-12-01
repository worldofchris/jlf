"""
Wrapper around the Trello API to get data out and into a
common format for reporting on.
"""

from datetime import datetime, date, timedelta
from trello import TrelloApi
import dateutil.parser
import operator
import os
import sys
import requests

from jlf_stats.history import remove_gaps_from_state_transitions
from jlf_stats.work_item import WorkItem

class TrelloWrapper(object):
    """
    Wrapper around a the Trolly/Trello API
    """

    def __init__(self, config):

        self.transition_actions = ['createCard', 'updateCard', 'moveCardToBoard', 'moveCardFromBoard', 'copyCard', 'copyCommentCard']
        self.trello = TrelloApi(config['source']['key'],
                                token=config['source']['token'])

        self.member = config['source']['member']
        self.types = config['types']
        self.cycle_config = config['cycles']
        if 'categories' in config:
            self.categories = config['categories']
        self._work_items = []

        self.boards = self.trello.members.get_board(self.member)

        self.from_date = datetime.strptime(config['from_date'], '%Y-%m-%d')
        self.until_date = datetime.strptime(config['until_date'], '%Y-%m-%d').date()
 
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
            work_item.state_transitions = remove_gaps_from_state_transitions(work_item.state_transitions)

            work_item.set_history(self.until_date)
            work_item.set_cycles(self.cycle_config)

        return self._work_items

    def work_items_from_board_actions(self, board_name, category="all"):
        """
        Get all the work items in a boards history of actions
        """
        board = next((board for board in self.boards if board['name'] == board_name), None)

        actions = []
        limit = 1000
        since = self.from_date
        before = None
        filter = self.transition_actions
        while (before is None) or (before > self.from_date.date()):

            while True:
                try:
                    batch = self.trello.boards.get_action(board['id'], limit=limit, filter=filter, since=str(since), before=before)
                    break
                except requests.exceptions.HTTPError as exception:
                    print exception

            actions.extend(batch)
            if len(batch) > 0:
                id_time = int(batch[-1]['id'][0:8], 16)
                before=date.fromtimestamp(id_time)
            else:
                break
            sys.stdout.write(".")
            sys.stdout.flush()

        sys.stdout.write("\n")
        print board['name'] + ' has ' + str(len(actions)) + ' actions.'

        for action in actions:
            try:
                card_id = action['data']['card']['id']
            except KeyError as exception:
                continue

            work_item = next((work_item for work_item in self._work_items if work_item.id == card_id), None)

            state_transition = self.state_transition(action)

            if work_item is not None:
                if state_transition is not None:
                    work_item.state_transitions.append(state_transition)
                    work_item.state_transitions.sort(key=operator.itemgetter('timestamp'))

                    # History and Cycles need to be updated here too.

            else:
                while True:
                    try:
                        card = self.trello.cards.get(card_id)
                        break
                    except requests.exceptions.HTTPError as exception:
                        if exception.response.status_code == 404:
                            sys.stdout.write("_")
                            sys.stdout.flush()
                            card = None
                            break
                        print exception

                # Add the action
                state_transitions = []
                if state_transition is not None:
                    state_transitions = [state_transition]

                work_item_type = None

                if card is not None:
                    date_created = datetime.fromtimestamp(int(card['id'][0:8], 16))
                    while True:
                        try:
                            card_list = self.trello.lists.get(card['idList'])
                            break
                        except requests.exceptions.HTTPError as exception:
                            print exception

                    for work_types in self.types:
                        for type_label in self.types[work_types]:
                            for label in card['labels']:
                                if label['name'].lower().strip() == type_label.lower().strip():
                                    work_item_type = label['name']

                    work_item = WorkItem(id=card['id'],
                                         state=card_list['name'],
                                         title=card['name'],
                                         type=work_item_type,
                                         category=category,
                                         date_created=date_created.date(),
                                         state_transitions=state_transitions)

                    self._work_items.append(work_item)

            if action['type'] == 'createCard':

                # Update the Created Date from the Create Action
                date_created = state_transition['timestamp']
                work_item.date_created = date_created.date()

            sys.stdout.write(".")
            sys.stdout.flush()

        return self._work_items

    def state_transition(self, action):
        """
        Get a state transition from an action
        """

        while True:
            try:
                if action['type'] == 'updateCard':
                    if 'listAfter' in action['data']:
                        to_state = action['data']['listAfter']['name']
                    else:
                        return None
                    from_state = action['data']['listBefore']['name']
                    break
                elif action['type'] == 'moveCardToBoard':
                    list_details = self.trello.lists.get(action['data']['list']['id'])
                    to_state = list_details['name']
                    from_state = None
                    break
                elif action['type'] == 'moveCardFromBoard':
                    to_state = None
                    list_details = self.trello.lists.get(action['data']['list']['id'])
                    from_state = list_details['name']
                    break
                elif action['type'] == 'createCard':
                    from_state = 'CREATED'
                    list_details = self.trello.lists.get(action['data']['list']['id'])
                    to_state = list_details['name']
                    break
                elif action['type'] in ['addAttachmentToCard',
                                        'commentCard',
                                        'addMemberToCard',
                                        'updateCheckItemStateOnCard',
                                        'addChecklistToCard',
                                        'removeMemberFromCard',
                                        'deleteCard',
                                        'deleteAttachmentFromCard',
                                        'removeChecklistFromCard']:
                    # Do we want to do something different with deleteCard?
                    return None
                elif action['type'] in ['copyCard', 'copyCommentCard']:
                    # Grab history from previous card and add it to this one?
                    return None
                else:
                    print "Found Action Type:" + action['type']
                    return None
            except requests.exceptions.HTTPError as exception:
                print exception

        state_transition = {'from':      from_state,
                            'to':        to_state,
                            'timestamp': dateutil.parser.parse(action['date'])}

        return state_transition
