"""A small Lisp: lexical closures, tail-call optimisation, a REPL.

    python tinylisp.py              # REPL
    python tinylisp.py file.lisp    # run a file
"""
import math
import operator
import sys
from functools import reduce


class LispError(Exception):
    pass


class Symbol(str):
    pass


class Env(dict):
    def __init__(self, params=(), args=(), outer=None):
        super().__init__(zip(params, args))
        self.outer = outer

    def find(self, name):
        env = self
        while env is not None:
            if name in env:
                return env
            env = env.outer
        raise LispError(f"unbound symbol: {name}")


class Lambda:
    def __init__(self, params, body, env):
        self.params, self.body, self.env = params, body, env

    def __repr__(self):
        return "#<lambda>"


def tokenize(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
        elif c == ";":
            while i < n and src[i] != "\n":
                i += 1
        elif c in "()'":
            out.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            if j >= n:
                raise LispError("unterminated string")
            out.append(src[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and not src[j].isspace() and src[j] not in "()';":
                j += 1
            out.append(src[i:j])
            i = j
    return out


def atom(tok):
    if tok[0] == '"':
        return bytes(tok[1:-1], "utf-8").decode("unicode_escape")
    for conv in (int, float):
        try:
            return conv(tok)
        except ValueError:
            pass
    if tok == "#t":
        return True
    if tok == "#f":
        return False
    return Symbol(tok)


def read_from(tokens):
    if not tokens:
        raise LispError("unexpected EOF")
    tok = tokens.pop(0)
    if tok == "(":
        lst = []
        while tokens and tokens[0] != ")":
            lst.append(read_from(tokens))
        if not tokens:
            raise LispError("missing )")
        tokens.pop(0)
        return lst
    if tok == ")":
        raise LispError("unexpected )")
    if tok == "'":
        return [Symbol("quote"), read_from(tokens)]
    return atom(tok)


def parse_all(src):
    tokens = tokenize(src)
    forms = []
    while tokens:
        forms.append(read_from(tokens))
    return forms


def _div(a, b):
    if b == 0:
        raise LispError("division by zero")
    q = a / b
    return int(q) if isinstance(a, int) and isinstance(b, int) and a % b == 0 else q


def _chain(cmp):
    return lambda *xs: all(cmp(a, b) for a, b in zip(xs, xs[1:]))


def standard_env():
    env = Env()
    env.update({
        "+": lambda *a: sum(a),
        "*": lambda *a: reduce(operator.mul, a, 1),
        "-": lambda a, *r: -a if not r else reduce(operator.sub, r, a),
        "/": lambda a, *r: reduce(_div, r, a),
        "mod": operator.mod, "abs": abs, "sqrt": math.sqrt,
        "min": min, "max": max,
        "=": _chain(operator.eq), "<": _chain(operator.lt), ">": _chain(operator.gt),
        "<=": _chain(operator.le), ">=": _chain(operator.ge),
        "not": operator.not_,
        "cons": lambda a, b: [a] + list(b),
        "car": lambda x: x[0], "cdr": lambda x: x[1:],
        "list": lambda *a: list(a),
        "length": len, "append": lambda *ls: [x for l in ls for x in l],
        "null?": lambda x: x == [],
        "list?": lambda x: isinstance(x, list),
        "number?": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "symbol?": lambda x: isinstance(x, Symbol),
        "string-append": lambda *s: "".join(s),
        "display": lambda x: print(to_string(x, False), end="") or None,
        "newline": lambda: print() or None,
    })
    return env


def evaluate(x, env):
    while True:  # loop instead of recursion in tail position
        if isinstance(x, Symbol):
            return env.find(x)[x]
        if not isinstance(x, list):
            return x
        if not x:
            raise LispError("cannot evaluate ()")
        head = x[0]
        if head == "quote":
            return x[1]
        if head == "if":
            if len(x) not in (3, 4):
                raise LispError("if takes 2 or 3 arguments")
            test = evaluate(x[1], env)
            if test is not False:
                x = x[2]
            elif len(x) == 4:
                x = x[3]
            else:
                return None
        elif head == "cond":
            for clause in x[1:]:
                if clause[0] == "else" or evaluate(clause[0], env) is not False:
                    for form in clause[1:-1]:
                        evaluate(form, env)
                    x = clause[-1]
                    break
            else:
                return None
        elif head == "define":
            target = x[1]
            if isinstance(target, list):  # (define (f a b) body...)
                name, params = target[0], target[1:]
                env[name] = Lambda(params, [Symbol("begin")] + x[2:], env)
            else:
                env[target] = evaluate(x[2], env)
            return None
        elif head == "set!":
            env.find(x[1])[x[1]] = evaluate(x[2], env)
            return None
        elif head == "lambda":
            return Lambda(x[1], [Symbol("begin")] + x[2:], env)
        elif head == "let":
            names = [b[0] for b in x[1]]
            vals = [evaluate(b[1], env) for b in x[1]]
            env = Env(names, vals, env)
            x = [Symbol("begin")] + x[2:]
        elif head == "begin":
            if len(x) == 1:
                return None
            for form in x[1:-1]:
                evaluate(form, env)
            x = x[-1]
        elif head == "and":
            for form in x[1:-1]:
                if evaluate(form, env) is False:
                    return False
            x = x[-1] if len(x) > 1 else True
            if x is True:
                return True
        elif head == "or":
            for form in x[1:-1]:
                v = evaluate(form, env)
                if v is not False:
                    return v
            x = x[-1] if len(x) > 1 else False
            if x is False:
                return False
        else:
            fn = evaluate(head, env)
            args = [evaluate(a, env) for a in x[1:]]
            if isinstance(fn, Lambda):
                if len(args) != len(fn.params):
                    raise LispError(f"expected {len(fn.params)} args, got {len(args)}")
                env = Env(fn.params, args, fn.env)
                x = fn.body
            elif callable(fn):
                try:
                    return fn(*args)
                except LispError:
                    raise
                except (TypeError, IndexError, ValueError) as e:
                    raise LispError(f"{head}: {e}")
            else:
                raise LispError(f"not a function: {to_string(fn)}")


def to_string(x, readable=True):
    if x is True:
        return "#t"
    if x is False:
        return "#f"
    if isinstance(x, list):
        return "(" + " ".join(to_string(i, readable) for i in x) + ")"
    if isinstance(x, str) and not isinstance(x, Symbol):
        return '"' + x + '"' if readable else x
    return str(x)


def run(src, env=None):
    env = env if env is not None else standard_env()
    result = None
    for form in parse_all(src):
        result = evaluate(form, env)
    return result


def repl():
    env = standard_env()
    buf = ""
    while True:
        try:
            line = input("... " if buf else "lisp> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        buf += line + "\n"
        if buf.count("(") > buf.count(")"):
            continue
        try:
            result = run(buf, env)
            if result is not None:
                print(to_string(result))
        except LispError as e:
            print("error:", e)
        except RecursionError:
            print("error: recursion too deep")
        buf = ""


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            run(f.read())
    else:
        repl()
