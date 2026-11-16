import random
import re
import signal
import time
import unittest

from regex import Regex, RegexError, fullmatch, search


class _Slow(Exception):
    pass


def _oracle(py, text, seconds=0.5):
    """Python's own re can go exponential on nested stars, so bound it and skip those cases."""
    def alarm(*_):
        raise _Slow()
    old = signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return py.fullmatch(text), py.search(text)
    except _Slow:
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class T(unittest.TestCase):
    def test_basics(self):
        self.assertTrue(fullmatch("abc", "abc"))
        self.assertFalse(fullmatch("abc", "abcd"))
        self.assertTrue(fullmatch("a.c", "axc"))
        self.assertFalse(fullmatch("a.c", "a\nc"))
        self.assertTrue(fullmatch("", ""))
        self.assertTrue(fullmatch("a*", ""))

    def test_classes_and_escapes(self):
        self.assertTrue(fullmatch(r"[a-c]+\d{2,3}", "abca12"))
        self.assertFalse(fullmatch(r"[^a-c]", "b"))
        self.assertTrue(fullmatch(r"[]a]+", "]a]"))
        self.assertTrue(fullmatch(r"[a\-z]+", "a-z"))
        self.assertTrue(fullmatch(r"\w+@\w+\.com", "me@example.com"))
        self.assertTrue(fullmatch(r"a\.b", "a.b") and not fullmatch(r"a\.b", "axb"))

    def test_leftmost_longest(self):
        self.assertEqual(search("a|ab", "xab"), (1, 3))
        self.assertEqual(search("a*", "baaa"), (0, 0))
        self.assertEqual(search(r"\d+", "ab123cd"), (2, 5))

    def test_anchors(self):
        self.assertEqual(search("^ab", "abab"), (0, 2))
        self.assertIsNone(search("^b", "ab"))
        self.assertEqual(search("b$", "abb"), (2, 3))
        self.assertEqual(search("^$", ""), (0, 0))

    def test_bounds(self):
        self.assertTrue(fullmatch("a{3}", "aaa") and not fullmatch("a{3}", "aa"))
        self.assertTrue(fullmatch("a{2,}", "aaaa") and not fullmatch("a{2,}", "a"))
        self.assertTrue(fullmatch("(ab){1,2}", "abab") and not fullmatch("(ab){1,2}", "ababab"))
        self.assertTrue(fullmatch("a{,2}", "a{,2}"))  # not a valid bound, so literal

    def test_findall(self):
        self.assertEqual(Regex(r"\d+").findall("a1b22c333"), ["1", "22", "333"])
        self.assertEqual(Regex("x*").findall("axxb"), ["", "xx", "", ""])

    def test_errors(self):
        for bad in ("(", ")", "*a", "a|*", "[a", "[z-a]", "a{3,1}", "a\\"):
            with self.assertRaises(RegexError, msg=bad):
                Regex(bad)

    def test_pathological_patterns_stay_fast(self):
        n = 28   # (a?){n}a{n} against a^n takes a backtracking engine ~2^n steps
        t = time.time()
        self.assertTrue(fullmatch("a?" * n + "a" * n, "a" * n))
        self.assertTrue(fullmatch("(a*)*b", "a" * 300 + "b"))
        self.assertFalse(fullmatch("(a*)*b", "a" * 300))
        self.assertLess(time.time() - t, 5)

    def test_fuzz_against_python_re(self):
        """fullmatch and 'is there a match / where does it start' are engine-independent."""
        rnd = random.Random(1234)
        atoms = ["a", "b", "c", ".", "[ab]", "[^a]", r"\w", "(a|b)", "(ab|c)", "(a*|b)", ""]
        quants = ["", "", "", "*", "+", "?", "{2}", "{1,2}"]

        def gen(d=0):
            parts = []
            for _ in range(rnd.randint(1, 4)):
                a = rnd.choice(atoms)
                if d < 2 and rnd.random() < 0.2:
                    a = "(" + gen(d + 1) + "|" + gen(d + 1) + ")"
                parts.append(a + (rnd.choice(quants) if a else ""))
            return "".join(parts)

        checked = 0
        for _ in range(1500):
            pat = gen()
            try:
                py = re.compile(pat)
            except re.error:
                continue
            ours = Regex(pat)
            for _ in range(6):
                text = "".join(rnd.choice("abc\n") for _ in range(rnd.randint(0, 8)))
                ref = _oracle(py, text)
                if ref is None:
                    continue
                full, m = ref
                self.assertEqual(ours.fullmatch(text), full is not None, (pat, text))
                s = ours.search(text)
                self.assertEqual(s is not None, m is not None, (pat, text))
                if m:
                    self.assertEqual(s[0], m.start(), (pat, text))
                    self.assertGreaterEqual(s[1], m.end(), (pat, text))  # longest >= first-found
                checked += 1
        self.assertGreater(checked, 5000)


if __name__ == "__main__":
    unittest.main()
