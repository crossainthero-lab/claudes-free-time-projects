"""Cellular automata in the terminal and as images.

    python automata.py rule 110 --width 79 --steps 40
    python automata.py ant --steps 11000 --out ant.png
"""
import argparse
import struct
import sys
import zlib


def rule_rows(rule, width, steps, wrap=True):
    """Yield `steps` generations of an elementary CA, starting from one live cell."""
    if not 0 <= rule <= 255:
        raise ValueError("rule must be 0-255")
    row = [0] * width
    row[width // 2] = 1
    for _ in range(steps):
        yield row
        nxt = []
        for i in range(width):
            l = row[i - 1] if wrap or i > 0 else 0
            r = row[(i + 1) % width] if wrap or i < width - 1 else 0
            nxt.append((rule >> (l << 2 | row[i] << 1 | r)) & 1)
        row = nxt


class Ant:
    """Langton's ant on an unbounded grid (sparse set of black cells)."""

    DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))  # up, right, down, left

    def __init__(self):
        self.black, self.x, self.y, self.d, self.steps = set(), 0, 0, 0, 0

    def step(self):
        pos = (self.x, self.y)
        if pos in self.black:       # black: turn left, flip to white
            self.d = (self.d - 1) % 4
            self.black.remove(pos)
        else:                       # white: turn right, flip to black
            self.d = (self.d + 1) % 4
            self.black.add(pos)
        dx, dy = self.DIRS[self.d]
        self.x, self.y = self.x + dx, self.y + dy
        self.steps += 1

    def run(self, n):
        for _ in range(n):
            self.step()
        return self

    def bounds(self):
        xs = [p[0] for p in self.black] + [self.x]
        ys = [p[1] for p in self.black] + [self.y]
        return min(xs), min(ys), max(xs), max(ys)

    def grid(self, pad=1):
        x0, y0, x1, y1 = self.bounds()
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
        return [[1 if (x, y) in self.black else 0 for x in range(x0, x1 + 1)]
                for y in range(y0, y1 + 1)]


def to_blocks(rows):
    """Pack pairs of rows into half-block characters (2x vertical resolution)."""
    rows = [list(r) for r in rows]
    if len(rows) % 2:
        rows.append([0] * len(rows[0]))
    glyph = {(0, 0): " ", (1, 0): "▀", (0, 1): "▄", (1, 1): "█"}
    return "\n".join(
        "".join(glyph[(a, b)] for a, b in zip(rows[i], rows[i + 1]))
        for i in range(0, len(rows), 2))


def write_pgm(rows, path, scale=1):
    """Write a binary PGM (opens in any image viewer; `convert x.pgm x.png` for PNG)."""
    h, w = len(rows), len(rows[0])
    with open(path, "wb") as f:
        f.write(f"P5\n{w * scale} {h * scale}\n255\n".encode())
        for r in rows:
            line = bytes(0 if c else 255 for c in r for _ in range(scale))
            f.write(line * scale)


def write_png(rows, path, scale=1):
    """Write a greyscale PNG using only the standard library."""
    h, w = len(rows), len(rows[0])

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(
        b"\x00" + bytes(0 if c else 255 for c in r for _ in range(scale))
        for r in rows for _ in range(scale))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 0, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def write_image(rows, path, scale=1):
    (write_png if path.lower().endswith(".png") else write_pgm)(rows, path, scale)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rule", help="elementary cellular automaton")
    r.add_argument("number", type=int)
    r.add_argument("--width", type=int, default=79)
    r.add_argument("--steps", type=int, default=40)
    r.add_argument("--out", help="write a .png or .pgm image instead of printing")
    r.add_argument("--scale", type=int, default=4)
    a = sub.add_parser("ant", help="Langton's ant")
    a.add_argument("--steps", type=int, default=11000)
    a.add_argument("--out", help="write a .png or .pgm image instead of printing")
    a.add_argument("--scale", type=int, default=2)
    args = p.parse_args(argv)

    if args.cmd == "rule":
        rows = list(rule_rows(args.number, args.width, args.steps))
    else:
        ant = Ant().run(args.steps)
        rows = ant.grid()
        print(f"{ant.steps} steps, {len(ant.black)} black cells, ant at ({ant.x}, {ant.y})", file=sys.stderr)
    if args.out:
        write_image(rows, args.out, args.scale)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(to_blocks(rows))


if __name__ == "__main__":
    main()
