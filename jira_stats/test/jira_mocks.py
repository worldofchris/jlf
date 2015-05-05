class mockHistory(object):

        def __init__(self, created, items):
                self.created = created
                self.items = items


class mockItem(object):

        def __init__(self, field, fromString, toString):
                self.field = field
                self.fromString = fromString
                self.toString = toString


class mockChangelog(object):

    def __init__(self, histories):
        self.histories = histories

CREATED_STATE = 'Open'
START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'
