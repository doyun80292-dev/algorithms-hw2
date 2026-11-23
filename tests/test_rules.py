"""저장소 규칙 검사 (이슈 #5): src/ 에 dict·set·내장 hash()가 없는지 ast로 확인."""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from check_rules import check_dir, check_source  # noqa: E402


class TestCheckerItself(unittest.TestCase):
    """검사기가 진짜 위반은 잡고, 주석·문자열·비슷한 이름은 통과시키는지."""

    def test_catches_real_usage(self):
        bad = [
            "x = dict()", "x = {}", "x = {'a': 1}", "x = {1, 2}", "x = set()",
            "y = hash('a')", "z = {k: 1 for k in 'ab'}", "w = {k for k in 'ab'}",
            "def f(**kw): pass", "from collections import defaultdict",
            "import collections\nc = collections.Counter()",
        ]
        for src in bad:
            self.assertTrue(check_source(src), src)

    def test_ignores_comments_strings_and_similar_names(self):
        ok = [
            "# dict, set, hash() 금지", "s = 'dict set( hash('",
            "def horner_hash(k, m): return 0", "x = horner_hash('a', 3)",
            "class T:\n    def reset(self): pass", "t.set_value(1)",
            "f(a=1)",
        ]
        for src in ok:
            self.assertEqual(check_source(src), [], src)


class TestSrcFollowsRules(unittest.TestCase):
    def test_src_has_no_forbidden_constructs(self):
        problems = check_dir(os.path.join(ROOT, "src"))
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
