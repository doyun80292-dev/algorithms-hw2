"""단축기 테스트 (이슈 #4, #8). SPEC.md 4절, 6절 '단축기'.

같은 테스트를 개별 체이닝과 선형 탐지 두 테이블에서 모두 돌린다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shortener import Shortener, validate_url  # noqa: E402


class ShortenerContract:
    TABLE = None

    def setUp(self):
        self.s = Shortener(table=self.TABLE)

    # 1. 일련번호 base62
    def test_codes_are_sequential_base62(self):
        codes = [self.s.shorten("https://example.com/%d" % i) for i in range(62)]
        self.assertEqual(codes[0], "1")
        self.assertEqual(codes[1], "2")
        self.assertEqual(codes[8], "9")
        self.assertEqual(codes[9], "a")
        self.assertEqual(codes[60], "Z")
        self.assertEqual(codes[61], "10")

    # 2. 같은 URL 두 번
    def test_duplicate_url_returns_same_code(self):
        c1 = self.s.shorten("https://example.com/a")
        c2 = self.s.shorten("https://example.com/a")
        self.assertEqual(c1, c2)
        self.assertEqual(len(self.s), 1)
        # 다음 새 URL은 번호를 건너뛰지 않는다
        self.assertEqual(self.s.shorten("https://example.com/b"), "2")

    def test_duplicate_after_strip(self):
        c1 = self.s.shorten("https://example.com/a")
        c2 = self.s.shorten("  https://example.com/a \n")
        self.assertEqual(c1, c2)

    # 3. 다른 URL
    def test_different_urls_different_codes(self):
        a = self.s.shorten("https://example.com/a")
        b = self.s.shorten("https://example.com/A")
        c = self.s.shorten("https://example.com/a/")
        self.assertEqual(len([a, b, c]), 3)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)

    # 4. 왕복
    def test_expand_round_trip(self):
        url = "https://www.yonsei.ac.kr/sc/intro/index.jsp?x=1&y=%EA%B0%80#top"
        self.assertEqual(self.s.expand(self.s.shorten(url)), url)

    # 5. 없는 코드
    def test_expand_unknown_returns_none(self):
        self.assertIsNone(self.s.expand("1"))
        self.s.shorten("https://example.com")
        self.assertIsNone(self.s.expand("2"))
        self.assertIsNone(self.s.expand(""))
        self.assertIsNone(self.s.expand("ab_c"))
        self.assertIsNone(self.s.expand("한글"))
        self.assertIsNone(self.s.expand(None))

    # 6. 잘못된 스킴·호스트
    def test_rejects_bad_scheme(self):
        for bad in ("ftp://example.com/file", "javascript:alert(1)",
                    "example.com", "www.example.com/path", "mailto:a@b.c",
                    "http//example.com", "://example.com"):
            with self.assertRaises(ValueError, msg=bad):
                self.s.shorten(bad)
        self.assertEqual(len(self.s), 0)

    def test_rejects_missing_host(self):
        for bad in ("http://", "https://", "https:///path", "http://?q=1", "http://#x"):
            with self.assertRaises(ValueError, msg=bad):
                self.s.shorten(bad)

    def test_rejects_empty(self):
        for bad in ("", "   ", "\n\t"):
            with self.assertRaises(ValueError):
                self.s.shorten(bad)

    def test_rejects_non_str(self):
        for bad in (None, 123, b"https://a.com"):
            with self.assertRaises(TypeError):
                self.s.shorten(bad)

    # 7. 공백
    def test_rejects_inner_whitespace(self):
        for bad in ("https://exa mple.com", "https://example.com/a b",
                    "https://example.com/\ta", "https://example.com/a\nb"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.s.shorten(bad)

    # 8. 길이
    def test_length_limit(self):
        base = "https://example.com/"
        ok = base + "a" * (2048 - len(base))
        self.assertEqual(len(ok), 2048)
        code = self.s.shorten(ok)
        self.assertEqual(self.s.expand(code), ok)
        with self.assertRaises(ValueError):
            self.s.shorten(ok + "a")

    # 9. 대문자 스킴
    def test_uppercase_scheme_ok(self):
        code = self.s.shorten("HTTPS://Example.com/X")
        self.assertEqual(self.s.expand(code), "HTTPS://Example.com/X")

    # 10. 대량
    def test_bulk(self):
        n = 3000
        codes = [self.s.shorten("https://bulk.example/%d" % i) for i in range(n)]
        self.assertEqual(len(self.s), n)
        for i, c in enumerate(codes):
            self.assertEqual(self.s.expand(c), "https://bulk.example/%d" % i)
        # 모두 다른 코드
        self.assertEqual(codes[-1], self._b62(n))

    @staticmethod
    def _b62(n):
        from base62 import encode
        return encode(n)

    def test_code_is_not_url_hash(self):
        # 같은 칸으로 가는 URL이어도 코드는 다르다 (일련번호이므로)
        a = self.s.shorten("https://a.example/1")
        b = self.s.shorten("https://a.example/2")
        self.assertEqual((a, b), ("1", "2"))

    def test_table_name(self):
        self.assertEqual(self.s.table_name, self.TABLE)


class TestShortenerChaining(ShortenerContract, unittest.TestCase):
    TABLE = "chaining"


class TestValidateUrl(unittest.TestCase):
    def test_returns_stripped(self):
        self.assertEqual(validate_url("  https://a.com  "), "https://a.com")

    def test_ok_examples(self):
        for ok in ("http://a.com", "https://a.com/", "http://localhost:8000/x",
                   "https://127.0.0.1/path?q=%20", "https://한글.kr/경로"):
            self.assertEqual(validate_url(ok), ok)


class TestShortenerOptions(unittest.TestCase):
    def test_default_is_chaining(self):
        self.assertEqual(Shortener().table_name, "chaining")

    def test_unknown_table_raises(self):
        with self.assertRaises(ValueError):
            Shortener(table="cuckoo")


if __name__ == "__main__":
    unittest.main()
