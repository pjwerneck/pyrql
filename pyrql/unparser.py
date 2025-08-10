import datetime
import decimal
import uuid

from pyrql.parser import epoch_datetime


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

    def unparse_token(self, arg):  # noqa: PLR0911
        if arg is None:
            return "null"

        if isinstance(arg, bool):
            return str(arg).lower()

        if isinstance(arg, decimal.Decimal):
            return f"decimal:{arg}"

        if isinstance(arg, float):
            # repr(float) returns the shortest decimal representation
            # for the same binary float
            return repr(arg)

        if isinstance(arg, uuid.UUID):
            return f"uuid:{arg.hex}"

        if isinstance(arg, epoch_datetime):
            return f"epoch:{arg.timestamp()}"

        if isinstance(arg, datetime.datetime):
            return f"datetime:{arg.isoformat()}"

        if isinstance(arg, datetime.date):
            return f"date:{arg.isoformat()}"

        return str(arg)
