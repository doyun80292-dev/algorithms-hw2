"""두 해시 테이블(개별 체이닝, 선형 탐지)이 함께 지켜야 할 계약 테스트.

SPEC.md 6절 '해시 테이블(두 구현 공통)'을 옮긴 것이다.
이 파일은 test_*.py가 아니므로 혼자서는 돌지 않는다.
test_hash_table.py / test_linear_probing.py가 TABLE_CLASS만 바꿔 상속한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hashing import horner_hash  # noqa: E402


def colliding_keys(m, count, prefix="k"):
    """capacity m 에서 같은 칸으로 가는 서로 다른 키 count개를 찾는다."""
    target = horner_hash(prefix + "0", m)
    found = [prefix + "0"]
    i = 1
    while len(found) < count:
        k = prefix + str(i)
        if horner_hash(k, m) == target:
            found.append(k)
        i += 1
    return found


class HashTableContract:
    TABLE_CLASS = None  # 하위 클래스가 정한다

    def make(self, capacity=11, max_load=None):
        return self.TABLE_CLASS(capacity=capacity, max_load=max_load)

    # 1. 빈 테이블
    def test_empty_table(self):
        t = self.make()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t.get("nope"))
        self.assertEqual(t.get("nope", "dflt"), "dflt")
        self.assertFalse("nope" in t)
        self.assertEqual(t.load_factor(), 0)
        self.assertEqual(t.keys(), [])

    # 2. 넣고 찾기, 덮어쓰기
    def test_put_get(self):
        t = self.make()
        t.put("https://a.com", "1")
        self.assertEqual(t.get("https://a.com"), "1")
        self.assertTrue("https://a.com" in t)
        self.assertEqual(len(t), 1)

    def test_put_overwrites(self):
        t = self.make()
        t.put("x", 1)
        t.put("x", 2)
        self.assertEqual(t.get("x"), 2)
        self.assertEqual(len(t), 1)

    # 3. 충돌
    def test_collisions_all_found(self):
        t = self.make(capacity=11)
        keys = colliding_keys(11, 5)
        for i, k in enumerate(keys):
            t.put(k, i)
        self.assertEqual(len(t), 5)
        for i, k in enumerate(keys):
            self.assertEqual(t.get(k), i)
        self.assertEqual(len(set_free_unique(t.index_of(k) for k in keys)), 1)

    # 4. 충돌한 키 중 가운데 삭제
    def test_remove_middle_of_collision(self):
        t = self.make(capacity=11)
        keys = colliding_keys(11, 5)
        for i, k in enumerate(keys):
            t.put(k, i)
        self.assertEqual(t.remove(keys[2]), 2)
        self.assertEqual(len(t), 4)
        self.assertIsNone(t.get(keys[2]))
        self.assertFalse(keys[2] in t)
        for i, k in enumerate(keys):
            if i != 2:
                self.assertEqual(t.get(k), i, "삭제 뒤 %r를 못 찾음" % k)

    # 5. 없는 키 삭제
    def test_remove_missing_raises(self):
        t = self.make()
        with self.assertRaises(KeyError):
            t.remove("missing")
        t.put("a", 1)
        t.remove("a")
        with self.assertRaises(KeyError):
            t.remove("a")
        self.assertEqual(len(t), 0)

    def test_reinsert_after_remove(self):
        t = self.make()
        t.put("a", 1)
        t.remove("a")
        t.put("a", 2)
        self.assertEqual(t.get("a"), 2)
        self.assertEqual(len(t), 1)

    # 6. 빈 문자열 키
    def test_empty_string_key(self):
        t = self.make()
        self.assertEqual(t.index_of(""), 0)
        t.put("", "empty")
        self.assertEqual(t.get(""), "empty")
        self.assertTrue("" in t)

    # 7. 문자열이 아닌 키
    def test_non_str_key_raises(self):
        t = self.make()
        for bad in (1, None, 3.5, ("a",)):
            with self.assertRaises(TypeError):
                t.put(bad, 1)
            with self.assertRaises(TypeError):
                t.get(bad)

    # 8. 호너 해시가 명세 식과 같다 (손 계산)
    def test_horner_matches_spec(self):
        t = self.make(capacity=11)
        # "ab": h=(0*31+97)%11=9, h=(9*31+98)%11=377%11=3
        self.assertEqual(t.index_of("ab"), 3)
        # "abc": h=(3*31+99)%11=192%11=5
        self.assertEqual(t.index_of("abc"), 5)
        steps = t.horner_steps("ab")
        self.assertEqual([s[2] for s in steps], [9, 3])
        self.assertEqual([s[1] for s in steps], [97, 98])

    # 9. 크기 확장
    def test_resize_when_over_max_load(self):
        t = self.TABLE_CLASS(capacity=5, max_load=0.5)
        for i in range(20):
            t.put("key%d" % i, i)
            self.assertLessEqual(t.load_factor(), 0.5)
        self.assertGreater(t.capacity, 5)
        for i in range(20):
            self.assertEqual(t.get("key%d" % i), i)

    def test_no_resize_when_max_load_none(self):
        t = self.make(capacity=7, max_load=None)
        for i in range(7):
            t.put("k%d" % i, i)
        self.assertEqual(t.capacity, 7)
        self.assertAlmostEqual(t.load_factor(), 1.0)

    # 10. find 비교 횟수 (공통으로 성립하는 것)
    def test_find_returns_value_and_count(self):
        t = self.make()
        t.put("a", 1)
        value, cmp = t.find("a")
        self.assertEqual(value, 1)
        self.assertEqual(cmp, 1)
        value, cmp = t.find("zzz-not-here")
        self.assertIsNone(value)
        self.assertGreaterEqual(cmp, 0)

    # 11. 대량 데이터
    def test_bulk(self):
        t = self.TABLE_CLASS()  # 기본 설정(확장 켜짐)
        n = 5000
        for i in range(n):
            t.put("https://example.com/page/%d" % i, i)
        self.assertEqual(len(t), n)
        for i in range(n):
            self.assertEqual(t.get("https://example.com/page/%d" % i), i)
        self.assertIsNone(t.get("https://example.com/page/%d" % n))
        self.assertEqual(len(t.keys()), n)

    # 12. 아주 작은 테이블
    def test_capacity_one(self):
        t = self.TABLE_CLASS(capacity=1, max_load=1.0)
        t.put("a", 1)
        t.put("b", 2)
        t.put("c", 3)
        self.assertEqual([t.get(k) for k in "abc"], [1, 2, 3])

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            self.TABLE_CLASS(capacity=0)

    def test_items_and_stats(self):
        t = self.make()
        t.put("a", 1)
        t.put("b", 2)
        items = t.items()
        self.assertEqual(len(items), 2)
        self.assertIn(("a", 1), items)
        st = t.stats()
        self.assertEqual(st.size, 2)
        self.assertEqual(st.capacity, 11)
        self.assertAlmostEqual(st.load_factor, 2 / 11)


def set_free_unique(values):
    """set 없이 중복을 제거한 리스트 (테스트 보조)."""
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out
