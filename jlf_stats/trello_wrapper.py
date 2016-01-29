"""
Wrapper around the Trello API to get data out and into a
common format for reporting on.
"""

from datetime import datetime
from trello import TrelloApi
import dateutil.parser

from jlf_stats.work import WorkItem


class TrelloWrapper(object):
    """
    Wrapper around a the Trolly/Trello API
    """

    def __init__(self, config):

        self.trello = TrelloApi(config['source']['key'],
                                token=config['source']['token'])

        self.types = config['types']

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

        work_item = WorkItem(id=card['idShort'],
                             state=current_list_name,
                             title=card['name'],
                             type=work_item_type,
                             category="Awesome Software",
                             date_created=date_created,
                             history=None)

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
