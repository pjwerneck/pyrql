class RQLError(Exception):
    pass


class RQLSyntaxError(RQLError):
    pass


class RQLQueryError(RQLError):
    pass
