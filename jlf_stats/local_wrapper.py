import json
from dateutil import parser
from work import WorkItem

class LocalWrapper(object):

    def __init__(self, config):

        try:
            self.source = config['source']
        except KeyError as e:
            raise MissingConfigItem(e, "Missing Config Item:{0}".format(e))

        self.work_item_data = None

    def work_items(self):

        if self.work_item_data is None:

            with open(self.source['file']) as local_file:    
                work_item_raw_data = json.load(local_file)

            self.work_item_data = []

            for item in work_item_raw_data:
                wi = WorkItem(id=item['id'],
                              title=item['title'],
                              state=item['state'],
                              type=item['type'],
                              history=item['history'],
                              date_created=parser.parse(item['date_created']),
                              category=item['category'])

                self.work_item_data.append(wi)

        return self.work_item_data