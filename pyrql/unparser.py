# -*- coding: utf-8 -*-


class Unparser:

    def unparse(self, expr):
        name = expr.get('name')

        args = []

        for a in expr.get('args', []):
            if isinstance(a, dict):
                arg = self.unparse(a)

            elif isinstance(a, tuple):
                arg = self.unparse_tuple(a)

            else:
                arg = a

            args.append(arg)

        return '{}({})'.format(name, ','.join(map(str, args)))

    def unparse_tuple(self, arg):
        prefix = ''
        tokens = []

        if arg[0] in {'+', '-'}:
            prefix = arg[0]
            arg = arg[1:]

        for a in arg:
            if isinstance(a, tuple):
                tokens.append(self.unparse_tuple(a))
            else:
                tokens.append(a)

        if len(tokens) == 1:
            return prefix + tokens[0]

        else:
            return prefix + '(' + ','.join(tokens) + ')'
