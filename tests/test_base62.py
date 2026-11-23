"""base62 인코딩/디코딩 테스트 (이슈 #1)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode  # noqa: E402


class TestBase62Encode(unittest.TestCase):
    def test_alphabet_order(self):
        self.assertEqual(
            ALPHABET,
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )
        self.assertEqual(len(ALPHABET), 62)

    def test_zero_is_0(self):
        self.assertEqual(encode(0), "0")

    def test_single_digits(self):
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_multi_digit(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(63), "11")
        self.assertEqual(encode(62 * 62 - 1), "ZZ")
        self.assertEqual(encode(62 * 62), "100")
        # 125 = 2*62 + 1
        self.assertEqual(encode(125), "21")

    def test_large_number(self):
        n = 62 ** 10 + 12345
        self.assertEqual(decode(encode(n)), n)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_non_int_raises(self):
        for bad in (1.5, "10", None, True):
            with self.assertRaises(TypeError):
                encode(bad)


class TestBase62Decode(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("ZZ"), 62 * 62 - 1)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_invalid_char_raises(self):
        for bad in ("-1", "ab_c", "한글", " 1", "a b", "+"):
            with self.assertRaises(ValueError):
                decode(bad)

    def test_non_str_raises(self):
        with self.assertRaises(TypeError):
            decode(10)

    def test_case_sensitive(self):
        self.assertNotEqual(decode("a"), decode("A"))

    def test_round_trip(self):
        for n in list(range(0, 5000)) + [62 ** k for k in range(1, 12)]:
            self.assertEqual(decode(encode(n)), n)


if __name__ == "__main__":
    unittest.main()
