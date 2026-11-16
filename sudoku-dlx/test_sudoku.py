import unittest

from sudoku import count, pretty, solve, solutions

EASY = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
EASY_SOLVED = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
# Arto Inkala's "world's hardest sudoku" (2012)
HARD = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
HARD_SOLVED = "812753649943682175675491283154237896369845721287169534521974368438526917796318452"


def valid(g):
    units = [g[i * 9:(i + 1) * 9] for i in range(9)] + [g[i::9] for i in range(9)]
    units += [g[r * 9 + c:r * 9 + c + 3] + g[r * 9 + c + 9:r * 9 + c + 12] + g[r * 9 + c + 18:r * 9 + c + 21]
              for r in (0, 3, 6) for c in (0, 3, 6)]
    return all(sorted(u) == list("123456789") for u in units)


class T(unittest.TestCase):
    def test_easy(self):
        self.assertEqual(solve(EASY), EASY_SOLVED)

    def test_hard(self):
        self.assertEqual(solve(HARD), HARD_SOLVED)

    def test_uniqueness(self):
        self.assertEqual(count(EASY), 1)
        self.assertEqual(count(HARD), 1)

    def test_blank_grid_gives_valid_distinct_solutions(self):
        sols = []
        for s in solutions("." * 81):
            sols.append(s)
            if len(sols) == 3:
                break
        self.assertEqual(len(set(sols)), 3)
        self.assertTrue(all(valid(s) for s in sols))

    def test_multiple_solutions_detected(self):
        self.assertEqual(count("." * 81, limit=2), 2)

    def test_contradictory_givens(self):
        self.assertIsNone(solve("55" + "." * 79))               # same row, same digit
        self.assertIsNone(solve("1.......1" + "." * 72))        # same row
        self.assertIsNone(solve("1........" + "1" + "." * 71))  # same column

    def test_unsolvable_but_consistent(self):
        # Row 0 forces r1c9 = 9, but column 9 already holds a 9.
        self.assertIsNone(solve("12345678." + "........9" + "." * 63))

    def test_bad_input(self):
        for bad in ("123", "x" * 81):
            with self.assertRaises(ValueError):
                solve(bad)

    def test_pretty(self):
        self.assertEqual(len(pretty(EASY_SOLVED).splitlines()), 11)


if __name__ == "__main__":
    unittest.main()
