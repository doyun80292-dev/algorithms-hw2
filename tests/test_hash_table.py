"""개별 체이닝 해시 테이블 테스트 (이슈 #4). SPEC.md 3.3, 6절."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from table_contract import HashTableContract, colliding_keys  # noqa: E402
from hash_table import HashTable  # noqa: E402
from hashing import horner_hash, next_prime  # noqa: E402


class TestChainingContract(HashTableContract, unittest.TestCase):
    TABLE_CLASS = HashTable


class TestHashing(unittest.TestCase):
    def test_horner_formula(self):
        # 손 계산: "hi", M=13 → h=(104)%13=0 → (0*31+105)%13=105%13=1
        self.assertEqual(horner_hash("hi", 13), 1)
        self.assertEqual(horner_hash("", 13), 0)

    def test_horner_deterministic_across_calls(self):
        self.assertEqual(horner_hash("https://a.com", 4093),
                         horner_hash("https://a.com", 4093))

    def test_next_prime(self):
        self.assertEqual(next_prime(1), 2)
        self.assertEqual(next_prime(2), 2)
        self.assertEqual(next_prime(11), 11)
        self.assertEqual(next_prime(23), 23)
        self.assertEqual(next_prime(24), 29)
        self.assertEqual(next_prime(4093), 4093)


class TestChainingSpecific(unittest.TestCase):
    def test_defaults(self):
        t = HashTable()
        self.assertEqual(t.capacity, 11)
        self.assertEqual(t.max_load, 1.0)

    def test_unsuccessful_search_empty_bucket_counts_zero(self):
        t = HashTable(capacity=11, max_load=None)
        _, cmp = t.find("abc")
        self.assertEqual(cmp, 0)

    def test_comparison_counts_position_in_chain(self):
        t = HashTable(capacity=11, max_load=None)
        keys = colliding_keys(11, 4)
        for k in keys:
            t.put(k, k)
        for pos, k in enumerate(keys, start=1):
            self.assertEqual(t.find(k), (k, pos))
        # 같은 칸으로 가는 없는 키: 체인 길이만큼 비교
        extra = colliding_keys(11, 6)[5]
        self.assertEqual(t.find(extra), (None, 4))

    def test_new_key_appended_at_tail(self):
        t = HashTable(capacity=11, max_load=None)
        keys = colliding_keys(11, 3)
        for k in keys:
            t.put(k, 0)
        idx = t.index_of(keys[0])
        chain = t.snapshot()[idx]
        self.assertEqual([node[0] for node in chain], keys)

    def test_snapshot_shape(self):
        t = HashTable(capacity=5, max_load=None)
        t.put("a", 1)
        snap = t.snapshot()
        self.assertEqual(len(snap), 5)
        self.assertEqual(snap[t.index_of("a")], [("a", 1)])
        self.assertEqual(sum(len(c) for c in snap), 1)

    def test_resize_grows_to_prime(self):
        t = HashTable(capacity=11, max_load=1.0)
        for i in range(12):
            t.put("k%d" % i, i)
        # 12/11 > 1.0 이므로 next_prime(23) = 23 으로 늘어난다
        self.assertEqual(t.capacity, 23)

    def test_load_factor_above_one_allowed(self):
        t = HashTable(capacity=10, max_load=None)
        for i in range(40):
            t.put("k%d" % i, i)
        self.assertAlmostEqual(t.load_factor(), 4.0)
        self.assertEqual(t.stats().longest_chain >= 4, True)


if __name__ == "__main__":
    unittest.main()
