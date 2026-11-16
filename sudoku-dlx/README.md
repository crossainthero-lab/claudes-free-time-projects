# sudoku-dlx

Sudoku as an exact-cover problem, solved with Knuth's Algorithm X. A 9x9 grid becomes 324 constraints (every cell filled; every digit once per row, column and box) and 729 candidate placements. Always branching on the constraint with the fewest options keeps the search tiny.

```sh
python3 sudoku.py "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
python3 sudoku.py puzzles.txt      # one 81-char puzzle per line
python3 -m unittest -q
```

```
8 1 2 | 7 5 3 | 6 4 9
9 4 3 | 6 8 2 | 1 7 5
6 7 5 | 4 9 1 | 2 8 3
------+-------+------
...
```

As a library, `solutions(puzzle)` is a lazy generator of every solution and `count(puzzle, limit=2)` answers "is this puzzle unique?" without enumerating them all. Contradictory givens and unsolvable-but-consistent grids both return `None`.
