"""Sudoku via Knuth's Algorithm X on an exact-cover matrix (dictionary-of-sets form).

    python sudoku.py "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    python sudoku.py puzzles.txt          # one 81-char puzzle per line; '.' or '0' = blank
"""
import sys
from itertools import product


def build(n=3):
    """Exact-cover problem for an n^2 x n^2 Sudoku: 4 constraint families per (r, c, v)."""
    N = n * n
    X = ({("rc", rc) for rc in product(range(N), range(N))}
         | {("rn", rn) for rn in product(range(N), range(1, N + 1))}
         | {("cn", cn) for cn in product(range(N), range(1, N + 1))}
         | {("bn", bn) for bn in product(range(N), range(1, N + 1))})
    Y = {}
    for r, c, v in product(range(N), range(N), range(1, N + 1)):
        b = (r // n) * n + (c // n)
        Y[(r, c, v)] = [("rc", (r, c)), ("rn", (r, v)), ("cn", (c, v)), ("bn", (b, v))]
    X = {j: set() for j in X}
    for y, cols in Y.items():
        for j in cols:
            X[j].add(y)
    return X, Y


def solve_exact_cover(X, Y, solution=None):
    """Yield every exact cover. Picks the column with fewest candidates each step."""
    if solution is None:
        solution = []
    if not X:
        yield list(solution)
        return
    c = min(X, key=lambda c: len(X[c]))
    for r in list(X[c]):
        solution.append(r)
        removed = select(X, Y, r)
        yield from solve_exact_cover(X, Y, solution)
        deselect(X, Y, r, removed)
        solution.pop()


def select(X, Y, r):
    removed = []
    for j in Y[r]:
        for i in X[j]:
            for k in Y[i]:
                if k != j:
                    X[k].remove(i)
        removed.append(X.pop(j))
    return removed


def deselect(X, Y, r, removed):
    for j in reversed(Y[r]):
        X[j] = removed.pop()
        for i in X[j]:
            for k in Y[i]:
                if k != j:
                    X[k].add(i)


def solutions(puzzle):
    """Yield solved grids (as 81-char strings) for a puzzle string. Lazy: take as many as you need."""
    cells = puzzle.strip().replace("0", ".")
    if len(cells) != 81 or any(ch not in ".123456789" for ch in cells):
        raise ValueError("puzzle must be 81 characters of 1-9 and '.' / '0'")
    X, Y = build(3)
    for i, ch in enumerate(cells):
        if ch != ".":
            r, c = divmod(i, 9)
            try:
                select(X, Y, (r, c, int(ch)))
            except KeyError:  # clashing givens: a column was already consumed
                return
    for sol in solve_exact_cover(X, Y):
        grid = list(cells)
        for r, c, v in sol:
            grid[r * 9 + c] = str(v)
        yield "".join(grid)


def solve(puzzle):
    return next(solutions(puzzle), None)


def count(puzzle, limit=2):
    """Number of solutions, capped at `limit` (2 is enough to test uniqueness)."""
    n = 0
    for _ in solutions(puzzle):
        n += 1
        if n >= limit:
            break
    return n


def pretty(grid):
    lines = []
    for r in range(9):
        if r and r % 3 == 0:
            lines.append("------+-------+------")
        row = grid[r * 9:(r + 1) * 9]
        lines.append(" | ".join(" ".join(row[i:i + 3]) for i in (0, 3, 6)).replace(" | ", " | "))
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    arg = argv[1]
    try:
        with open(arg) as f:
            puzzles = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except OSError:
        puzzles = [arg]
    status = 0
    for p in puzzles:
        s = solve(p)
        if s is None:
            print("no solution:", p)
            status = 1
        elif len(puzzles) == 1:
            print(pretty(s))
        else:
            print(s)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
