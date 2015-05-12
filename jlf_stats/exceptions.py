class MissingState(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

    def __str__(self):

        return self.msg


class MissingConfigItem(Exception):

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

    def __str__(self):

        return self.msg
