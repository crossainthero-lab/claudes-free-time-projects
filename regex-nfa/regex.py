"""A regex engine that never backtracks.

Patterns are parsed to an AST, compiled to a Thompson NFA, and run by tracking the
*set* of live states per input character, so matching is O(len(pattern) * len(text))
no matter how nasty the pattern.

Syntax: literals  .  [abc] [a-z] [^x]  * + ?  {m} {m,} {m,n}  |  ( )  ^ $  \\d \\w \\s \\D \\W \\S  and \\ escapes.
Semantics are leftmost-longest (POSIX style), so `a|ab` on "ab" matches "ab".
There are no backreferences or capture groups; those need backtracking.
"""


class RegexError(ValueError):
    pass


# ---- parsing: pattern -> AST --------------------------------------------------
# AST nodes: ("char", pred) ("cat", [nodes]) ("alt", [nodes]) ("rep", node, lo, hi|None)
#            ("bol",) ("eol",) ("empty",)

def _word(c): return c.isalnum() and c.isascii() or c == "_"
def _digit(c): return c in "0123456789"
def _space(c): return c in " \t\n\r\f\v"

_CLASSES = {"d": _digit, "w": _word, "s": _space,
            "D": lambda c: not _digit(c), "W": lambda c: not _word(c), "S": lambda c: not _space(c)}
_ESC = {"n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v"}


class _Parser:
    def __init__(self, src):
        self.s, self.i = src, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def take(self):
        c = self.peek()
        if c is None:
            raise RegexError("unexpected end of pattern")
        self.i += 1
        return c

    def parse(self):
        node = self.alt()
        if self.peek() is not None:
            raise RegexError(f"unmatched ) at {self.i}")
        return node

    def alt(self):
        branches = [self.cat()]
        while self.peek() == "|":
            self.i += 1
            branches.append(self.cat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def cat(self):
        items = []
        while self.peek() not in (None, "|", ")"):
            items.append(self.repeat())
        return ("cat", items) if items else ("empty",)

    def repeat(self):
        node = self.atom()
        while True:
            c = self.peek()
            if c == "*": self.i += 1; node = ("rep", node, 0, None)
            elif c == "+": self.i += 1; node = ("rep", node, 1, None)
            elif c == "?": self.i += 1; node = ("rep", node, 0, 1)
            elif c == "{" and self._is_bound():
                node = ("rep", node, *self.bound())
            else:
                return node

    def _is_bound(self):
        j = self.s.find("}", self.i)
        body = self.s[self.i + 1:j] if j != -1 else ""
        lo, _, hi = body.partition(",")
        return lo.isdigit() and (hi == "" or hi.isdigit()) and ("," in body or hi == "")

    def bound(self):
        j = self.s.index("}", self.i)
        body = self.s[self.i + 1:j]
        self.i = j + 1
        lo, comma, hi = body.partition(",")
        lo = int(lo)
        hi = (int(hi) if hi else None) if comma else lo
        if hi is not None and hi < lo:
            raise RegexError("bad repetition bounds")
        if lo > 1000 or (hi or 0) > 1000:
            raise RegexError("repetition bound too large")
        return lo, hi

    def atom(self):
        c = self.take()
        if c == "(":
            node = self.alt()
            if self.peek() != ")":
                raise RegexError("missing )")
            self.i += 1
            return node
        if c in "*+?":
            raise RegexError(f"nothing to repeat at {self.i - 1}")
        if c == ".": return ("char", lambda ch: ch != "\n")
        if c == "^": return ("bol",)
        if c == "$": return ("eol",)
        if c == "[": return self.charset()
        if c == "\\":
            e = self.take()
            if e in _CLASSES: return ("char", _CLASSES[e])
            lit = _ESC.get(e, e)
            return ("char", lambda ch, lit=lit: ch == lit)
        return ("char", lambda ch, c=c: ch == c)

    def charset(self):
        negate = self.peek() == "^"
        if negate:
            self.i += 1
        preds, first = [], True
        while True:
            c = self.take()
            if c == "]" and not first:
                break
            first = False
            if c == "\\":
                e = self.take()
                if e in _CLASSES:
                    preds.append(_CLASSES[e]); continue
                c = _ESC.get(e, e)
            if self.peek() == "-" and self.s[self.i + 1:self.i + 2] not in ("]", ""):
                self.i += 1
                hi = self.take()
                if hi == "\\":
                    hi = self.take(); hi = _ESC.get(hi, hi)
                if hi < c:
                    raise RegexError(f"bad range {c}-{hi}")
                preds.append(lambda ch, lo=c, hi=hi: lo <= ch <= hi)
            else:
                preds.append(lambda ch, c=c: ch == c)
        test = lambda ch: any(p(ch) for p in preds)
        return ("char", (lambda ch: not test(ch)) if negate else test)


# ---- compiling: AST -> NFA ----------------------------------------------------
# Instruction forms: ("char", pred) ("split", a, b) ("jmp", a) ("bol",) ("eol",) ("match",)

def _emit(node, prog):
    kind = node[0]
    if kind == "char":
        prog.append(("char", node[1]))
    elif kind in ("bol", "eol"):
        prog.append((kind,))
    elif kind == "empty":
        pass
    elif kind == "cat":
        for n in node[1]:
            _emit(n, prog)
    elif kind == "alt":
        jumps = []
        for n in node[1][:-1]:
            split = len(prog); prog.append(None)
            _emit(n, prog)
            jumps.append(len(prog)); prog.append(None)
            prog[split] = ("split", split + 1, len(prog))
        _emit(node[1][-1], prog)
        for j in jumps:
            prog[j] = ("jmp", len(prog))
    elif kind == "rep":
        _, sub, lo, hi = node
        for _ in range(lo):
            _emit(sub, prog)
        if hi is None:                       # sub* : L: split(body, out); body; jmp L
            split = len(prog); prog.append(None)
            _emit(sub, prog)
            prog.append(("jmp", split))
            prog[split] = ("split", split + 1, len(prog))
        else:                                # (sub (sub (sub)?)?)? up to hi-lo extra copies
            splits = []
            for _ in range(hi - lo):
                splits.append(len(prog)); prog.append(None)
                _emit(sub, prog)
            for s in splits:
                prog[s] = ("split", s + 1, len(prog))


class Regex:
    def __init__(self, pattern):
        self.pattern = pattern
        self.prog = []
        _emit(_Parser(pattern).parse(), self.prog)
        self.prog.append(("match",))
        if len(self.prog) > 200_000:
            raise RegexError("pattern too large")

    def _closure(self, pcs, text, pos):
        """Follow split/jmp/assertions from each pc; return the pcs that consume or match.

        `seen` covers every visited pc, not just the returned ones: empty-bodied loops
        like (a*)* form cycles that consume nothing and would otherwise never terminate.
        """
        out, seen, stack = set(), set(), list(pcs)
        while stack:
            pc = stack.pop()
            if pc in seen:
                continue
            seen.add(pc)
            op = self.prog[pc]
            k = op[0]
            if k == "jmp": stack.append(op[1])
            elif k == "split": stack.extend((op[1], op[2]))
            elif k == "bol":
                if pos == 0: stack.append(pc + 1)
            elif k == "eol":
                if pos == len(text): stack.append(pc + 1)
            else:
                out.add(pc)
        return out

    def _longest_from(self, text, start):
        """End of the longest match beginning exactly at `start`, or -1."""
        states = self._closure([0], text, start)
        best = -1
        pos = start
        while states:
            if any(self.prog[pc][0] == "match" for pc in states):
                best = pos
            if pos == len(text):
                break
            ch = text[pos]
            nxt = [pc + 1 for pc in states if self.prog[pc][0] == "char" and self.prog[pc][1](ch)]
            pos += 1
            states = self._closure(nxt, text, pos)
        return best

    def fullmatch(self, text):
        return self._longest_from(text, 0) == len(text)  # longest end == len(text) iff some path ends there

    def search(self, text, pos=0):
        """Leftmost-longest match at or after `pos` as (start, end), or None."""
        for start in range(pos, len(text) + 1):
            end = self._longest_from(text, start)
            if end >= 0:
                return start, end
        return None

    def findall(self, text):
        out, pos = [], 0
        while pos <= len(text):
            m = self.search(text, pos)
            if m is None:
                break
            s, e = m
            out.append(text[s:e])
            pos = e + 1 if e == s else e
        return out


def compile(pattern):
    return Regex(pattern)


def fullmatch(pattern, text):
    return Regex(pattern).fullmatch(text)


def search(pattern, text):
    return Regex(pattern).search(text)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        sys.exit("usage: python regex.py PATTERN TEXT")
    m = search(sys.argv[1], sys.argv[2])
    print("no match" if m is None else f"{m[0]}:{m[1]}  {sys.argv[2][m[0]:m[1]]!r}")
