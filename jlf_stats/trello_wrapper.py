"""
Wrapper around the Trello API to get data out and into a
common format for reporting on.
"""

from datetime import datetime
from dateutil.tz import tzutc

from jlf_stats.work import WorkItem


class TrelloWrapper(object):
    """
    Wrapper around a the Trolly/Trello API
    """

    def work_item_from_card(self, card):
        """
        Get a work item from a Trello card
        """
        print card
        work_item = WorkItem(id="1838",
                             state="Closed (Fixed)",
                             title="Engine not working, throwing up this for no reason",
                             type="Bug",
                             category="wat",
                             date_created=datetime(2015, 03, 04, 12, 15, 41, tzinfo=tzutc()),
                             history=None)

        return work_item
