"""선형 탐지 해시 테이블 테스트 (이슈 #8). SPEC.md 3.4, 6절.

해시 테이블 공통 계약(table_contract.HashTableContract)을 그대로 상속하고,
끝 칸 → 0번 칸 넘어가기, 가득 찬 테이블, TOMBSTONE 같은 선형 탐지 전용 사례를 더한다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from table_contract import HashTableContract, colliding_keys  # noqa: E402
from hashing import horner_hash  # noqa: E402
from linear_probing import TOMBSTONE, LinearProbingTable  # noqa: E402


def keys_at(m, index, count, prefix="w"):
    """capacity m에서 처음 칸이 index인 서로 다른 키 count개."""
    out = []
    i = 0
    while len(out) < count:
        k = "%s%d" % (prefix, i)
        if horner_hash(k, m) == index:
            out.append(k)
        i += 1
    return out


class TestLinearContract(HashTableContract, unittest.TestCase):
    TABLE_CLASS = LinearProbingTable


class TestLinearSpecific(unittest.TestCase):
    def test_defaults(self):
        t = LinearProbingTable()
        self.assertEqual(t.capacity, 11)
        self.assertEqual(t.max_load, 0.5)

    def test_collision_goes_to_next_slot(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        a, b, c = colliding_keys(11, 3)
        home = t.index_of(a)
        for k in (a, b, c):
            t.put(k, k)
        snap = t.snapshot()
        self.assertEqual(snap[home][0], a)
        self.assertEqual(snap[(home + 1) % 11][0], b)
        self.assertEqual(snap[(home + 2) % 11][0], c)
        self.assertEqual(t.find(a), (a, 1))
        self.assertEqual(t.find(b), (b, 2))
        self.assertEqual(t.find(c), (c, 3))

    def test_wraps_from_last_slot_to_zero(self):
        m = 11
        t = LinearProbingTable(capacity=m, max_load=None)
        k1, k2, k3 = keys_at(m, m - 1, 3)
        for k in (k1, k2, k3):
            t.put(k, k)
        snap = t.snapshot()
        self.assertEqual(snap[m - 1][0], k1)
        self.assertEqual(snap[0][0], k2)
        self.assertEqual(snap[1][0], k3)
        self.assertEqual(t.find(k3), (k3, 3))
        self.assertEqual(t.probe_path(k3), [m - 1, 0, 1])

    def test_unsuccessful_search_counts_empty_slot(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        self.assertEqual(t.find("abc"), (None, 1))     # 빈 칸 하나를 들여다봄
        a, b, c = colliding_keys(11, 3)
        t.put(a, 1)
        t.put(b, 2)
        self.assertEqual(t.find(c), (None, 3))         # a, b, 빈 칸

    def test_full_table(self):
        m = 5
        t = LinearProbingTable(capacity=m, max_load=None)
        keys = ["f%d" % i for i in range(m)]
        for i, k in enumerate(keys):
            t.put(k, i)
        self.assertEqual(len(t), m)
        self.assertAlmostEqual(t.load_factor(), 1.0)
        with self.assertRaises(OverflowError):
            t.put("new-key", 99)
        self.assertEqual(len(t), m)
        t.put(keys[2], "overwritten")                   # 있는 키 덮어쓰기는 된다
        self.assertEqual(t.get(keys[2]), "overwritten")
        self.assertEqual(t.find("new-key"), (None, m))  # M칸을 다 보고 실패
        for i, k in enumerate(keys):
            if i != 2:
                self.assertEqual(t.get(k), i)

    def test_full_table_after_remove_accepts_new_key(self):
        m = 5
        t = LinearProbingTable(capacity=m, max_load=None)
        for i in range(m):
            t.put("f%d" % i, i)
        t.remove("f3")
        t.put("new-key", 99)                            # TOMBSTONE 자리에 들어간다
        self.assertEqual(t.get("new-key"), 99)
        self.assertEqual(len(t), m)

    def test_remove_leaves_tombstone_and_keeps_path(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        a, b, c = colliding_keys(11, 3)
        home = t.index_of(a)
        for k in (a, b, c):
            t.put(k, k)
        t.remove(b)
        self.assertIs(t.snapshot()[(home + 1) % 11], TOMBSTONE)
        self.assertEqual(t.find(c), (c, 3))             # TOMBSTONE을 건너 계속 탐색
        self.assertIsNone(t.get(b))

    def test_insert_reuses_first_tombstone(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        a, b, c, d = colliding_keys(11, 4)
        home = t.index_of(a)
        for k in (a, b, c):
            t.put(k, k)
        t.remove(b)
        t.put(d, d)
        self.assertEqual(t.snapshot()[(home + 1) % 11][0], d)
        self.assertEqual(len(t), 3)

    def test_put_existing_key_after_tombstone_does_not_duplicate(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        a, b, c = colliding_keys(11, 3)
        for k in (a, b, c):
            t.put(k, k)
        t.remove(a)
        t.put(c, "new")         # c는 TOMBSTONE 뒤에 이미 있다 → 덮어써야 함
        self.assertEqual(len(t), 2)
        self.assertEqual(t.get(c), "new")
        self.assertEqual(sum(1 for s in t.snapshot() if isinstance(s, tuple) and s[0] == c), 1)

    def test_resize_drops_tombstones(self):
        t = LinearProbingTable(capacity=11, max_load=0.5)
        for i in range(5):
            t.put("k%d" % i, i)
        t.remove("k0")
        for i in range(5, 12):
            t.put("k%d" % i, i)
        self.assertGreater(t.capacity, 11)
        self.assertFalse(any(s is TOMBSTONE for s in t.snapshot()))
        for i in range(1, 12):
            self.assertEqual(t.get("k%d" % i), i)

    def test_probe_path_for_missing_key_ends_at_empty(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        a, b, c = colliding_keys(11, 3)
        home = t.index_of(a)
        t.put(a, 1)
        self.assertEqual(t.probe_path(c), [home, (home + 1) % 11])

    def test_stats_longest_cluster(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        for k in colliding_keys(11, 4):
            t.put(k, 0)
        self.assertEqual(t.stats().longest_cluster, 4)


if __name__ == "__main__":
    unittest.main()
