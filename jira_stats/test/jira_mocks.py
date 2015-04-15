class mockHistory(object):

        def __init__(self, created, items):
                self.created = created
                self.items = items


class mockItem(object):

        def __init__(self, field, fromString, toString):
                self.field = field
                self.fromString = fromString
                self.toString = toString


START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'
