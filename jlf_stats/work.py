import json
from datetime import datetime
import pandas as pd


class WorkItem(object):

    def __init__(self,
                 id,
                 title,
                 state,
                 type,
                 history,
                 date_created,
                 state_transitions=None,
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
        self.state_transitions = state_transitions

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.state, self.history)

    def detail(self):

        detail = {'id': self.id,
                  'title': self.title,
                  'state': self.state,
                  'type': self.type,
                  'date_created': self.date_created.replace(tzinfo=None)}  # HACK HACK HACK - for excel's benefit

        if self.cycles is not None:
            for cycle in self.cycles:
                detail[cycle] = self.cycles[cycle]

        return detail

    def to_JSON(self):

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""

            if isinstance(obj, datetime):
                serial = obj.isoformat()
                return serial

            elif isinstance(obj, pd.Series):
                d1 = obj.to_dict()
                d2 = {}
                for k, v in d1.items():
                    d2[k.strftime("%Y-%m-%d")] = v
                return d2
            else:
                return obj.__dict__

        output = json.dumps(self, default=json_serial,
                                  sort_keys=True, indent=4)

        return output
