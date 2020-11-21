# -*- coding: utf-8 -*-

import datetime
import decimal
import uuid


class Unparser:
    def unparse(self, expr):
        name = expr.get("name")

        args = []

        for a in expr.get("args", []):
            if isinstance(a, dict):
                arg = self.unparse(a)

            elif isinstance(a, tuple):
                arg = self.unparse_tuple(a)

            else:
                arg = self.unparse_token(a)

            args.append(arg)

        return "{}({})".format(name, ",".join(map(str, args)))

    def unparse_tuple(self, arg):
        prefix = ""
        tokens = []

        if arg[0] in {"+", "-"}:
            prefix = arg[0]
            arg = arg[1:]

        for a in arg:
            if isinstance(a, tuple):
                tokens.append(self.unparse_tuple(a))
            else:
                tokens.append(self.unparse_token(a))

        return prefix + "(" + ",".join(tokens) + ")"

    def unparse_token(self, arg):
        if arg is None:
            return "null"

        elif isinstance(arg, bool):
            return str(arg).lower()

        elif isinstance(arg, decimal.Decimal):
            return "decimal:%s" % arg

        elif isinstance(arg, float):
            # repr(float) returns the shortest decimal representation
            # for the same binary float
            return repr(arg)

        elif isinstance(arg, uuid.UUID):
            return "uuid:%s" % arg.hex

        elif isinstance(arg, datetime.datetime):
            return "datetime:%s" % arg.isoformat()

        elif isinstance(arg, datetime.date):
            return "date:%s" % arg.isoformat()

        return str(arg)
