import json


class WorkItem(object):

    def __init__(self, id, state, history):
        self.id = id
        self.state = state
        self.history = history

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.state, self.history)

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
