import json
from datetime import datetime


class WorkItem(object):

    def __init__(self,
                 id,
                 title,
                 state,
                 type,
                 history,
                 date_created,
                 category=None,
                 cycles=None):
        self.id = id
        self.title = title
        self.state = state
        self.type = type
        self.history = history
        self.date_created = date_created
        self.category = category
        self.cycles = cycles

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.state, self.history)

    def detail(self):

        detail = {'id': self.id,
                  'title': self.title,
                  'state': self.state,
                  'type': self.type,
                  'date_created': self.date_created}

        for cycle in self.cycles:
            detail[cycle] = self.cycles[cycle]

        return detail

    def to_JSON(self):

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""

            if isinstance(obj, datetime):
                serial = obj.isoformat()
                return serial

            else:
                return obj.__dict__

        return json.dumps(self, default=json_serial,
                          sort_keys=True, indent=4)
