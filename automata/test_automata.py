import os
import tempfile
import unittest

from automata import Ant, rule_rows, to_blocks, write_image, write_pgm


class T(unittest.TestCase):
    def test_rule30_first_rows(self):
        rows = list(rule_rows(30, 9, 4))
        s = ["".join(map(str, r)) for r in rows]
        self.assertEqual(s[0], "000010000")
        self.assertEqual(s[1], "000111000")
        self.assertEqual(s[2], "001100100")
        self.assertEqual(s[3], "011011110")

    def test_rule90_is_sierpinski(self):
        # Row n of rule 90 has 2^popcount(n) live cells (Pascal's triangle mod 2).
        rows = list(rule_rows(90, 129, 32))
        for n, r in enumerate(rows):
            self.assertEqual(sum(r), 2 ** bin(n).count("1"), n)

    def test_rule_bounds(self):
        with self.assertRaises(ValueError):
            list(rule_rows(256, 5, 1))

    def test_ant_first_steps(self):
        a = Ant().run(1)
        self.assertEqual((a.x, a.y, a.black), (1, 0, {(0, 0)}))

    def test_ant_highway(self):
        # After ~10,000 chaotic steps the ant builds a diagonal "highway":
        # a 104-step cycle that shifts it 2 cells diagonally each time.
        a = Ant().run(11000)
        p1 = (a.x, a.y)
        a.run(104)
        p2 = (a.x, a.y)
        self.assertEqual((abs(p2[0] - p1[0]), abs(p2[1] - p1[1])), (2, 2))
        a.run(104)
        self.assertEqual((a.x - p2[0], a.y - p2[1]), (p2[0] - p1[0], p2[1] - p1[1]))

    def test_blocks(self):
        self.assertEqual(to_blocks([[1, 0], [1, 1]]), "█▄")
        self.assertEqual(to_blocks([[1, 0]]), "▀ ")

    def test_pgm(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.pgm")
            write_pgm([[1, 0], [0, 1]], path, scale=2)
            with open(path, "rb") as f:
                data = f.read()
            self.assertTrue(data.startswith(b"P5\n4 4\n255\n"))
            self.assertEqual(len(data), len(b"P5\n4 4\n255\n") + 16)

    def test_png(self):
        import struct, zlib
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.png")
            write_image([[1, 0], [0, 1]], path, scale=3)
            with open(path, "rb") as f:
                data = f.read()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            w, h = struct.unpack(">II", data[16:24])
            self.assertEqual((w, h), (6, 6))
            idat = data.index(b"IDAT")
            n = struct.unpack(">I", data[idat - 4:idat])[0]
            raw = zlib.decompress(data[idat + 4:idat + 4 + n])
            self.assertEqual(len(raw), 6 * (1 + 6))
            self.assertEqual(raw[1:7], bytes([0, 0, 0, 255, 255, 255]))


if __name__ == "__main__":
    unittest.main()
