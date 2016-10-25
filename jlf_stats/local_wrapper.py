# -*- coding: utf-8 -*-
"""
Get metrics from a JSON format file in the local filesystem.
"""

import json
from dateutil import parser
from jlf_stats.exceptions import MissingConfigItem
from jlf_stats.work_item import WorkItem


class LocalWrapper(object):

    def __init__(self, config):

        try:
            self.source = config['source']
            self.cycles = config['cycles']
        except KeyError as exception:
            raise MissingConfigItem(exception,
                                    "Missing Config Item:{0}".format(exception))

        self.work_item_data = None

    def work_items(self):

        if self.work_item_data is None:

            with open(self.source['file']) as local_file:
                work_item_raw_data = json.load(local_file)

            self.work_item_data = []

            for item in work_item_raw_data:

                if item['state_transitions'] is not None:
                    for transition in item['state_transitions']:
                        transition['timestamp'] = parser.parse(transition['timestamp'])

                wi = WorkItem(id=item['id'],
                              title=item['title'],
                              state=item['state'],
                              type=item['type'],
                              date_created=parser.parse(item['date_created']).date(),
                              state_transitions=item['state_transitions'],
                              category=item['category'],
                              cycle_config=self.cycles)

                self.work_item_data.append(wi)

        return self.work_item_data
