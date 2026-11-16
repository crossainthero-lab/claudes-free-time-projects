# regex-nfa

A regex engine that never backtracks. Patterns compile to a Thompson NFA, and matching tracks the *set* of live states one character at a time, so the cost is O(pattern × text) for any pattern.

```sh
python3 regex.py '\d+' 'ab123cd'     # 2:5  '123'
python3 -m unittest -q
```

```python
from regex import Regex, fullmatch, search
fullmatch(r"\w+@\w+\.com", "me@example.com")   # True
search("a|ab", "xab")                           # (1, 3): leftmost-longest
Regex(r"\d+").findall("a1b22c333")              # ['1', '22', '333']
```

**Syntax:** literals, `.`, `[abc]` `[a-z]` `[^x]`, `* + ?`, `{m}` `{m,}` `{m,n}`, `|`, `( )`, `^` `$`, `\d \w \s` and their negations, `\` escapes. `{,n}` is not a bound; it's literal text.
**Left out on purpose:** capture groups and backreferences. Both need backtracking (or much heavier machinery), which is the thing this avoids.
**Semantics:** leftmost-longest like POSIX, not leftmost-first like Perl and Python, so `a|ab` on `"ab"` matches `"ab"`.

## Why bother

`(a?){n}a{n}` against `a`×n is the classic backtracking killer. Same machine, same inputs:

| n | this engine | Python `re` |
|---|---|---|
| 20 | 0.2 ms | 19 ms |
| 24 | 0.2 ms | 328 ms |
| 26 | 0.2 ms | 1390 ms |

Python's time roughly quadruples every two characters. Mine doesn't move.

## How it's tested

Besides unit tests, a fuzz test generates ~1500 random patterns and checks them against Python's `re` on thousands of inputs. `fullmatch` results must agree exactly. `search` must agree on whether there is a match and where it starts, and its end must be at least as far as Python's (since longest ≥ first-found).

The fuzzer found something funny: on one generated pattern, with a 5-character input, *Python's `re`* stalled for over 3 seconds. The test bounds the oracle with a timer and skips those cases.
