"""선형 탐지 해시 테이블 (SPEC.md 3.4). HashTable(개별 체이닝)과 인터페이스가 같다.

각 칸: EMPTY(None) / TOMBSTONE / (key, value)
충돌하면 index = (index + 1) % M. 삭제는 TOMBSTONE으로 표시해 탐색 경로를 잇는다.
dict, set, 내장 hash()를 쓰지 않는다.
"""
from hashing import TableStats, horner_hash, horner_steps, next_prime

EMPTY = None


class _Tombstone:
    __slots__ = ()

    def __repr__(self):
        return "TOMBSTONE"


TOMBSTONE = _Tombstone()


class LinearProbingTable:
    kind = "linear"

    def __init__(self, capacity=11, max_load=0.5):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity는 1 이상의 정수여야 합니다")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load는 양수 또는 None이어야 합니다")
        self.capacity = capacity
        self.max_load = max_load
        self._slots = [EMPTY] * capacity
        self._size = 0

    # ---- 해시 ----
    def index_of(self, key):
        return horner_hash(key, self.capacity)

    def horner_steps(self, key):
        return horner_steps(key, self.capacity)

    # ---- 탐색의 핵심 ----
    def _probe(self, key):
        """(찾은 칸 또는 -1, 넣을 수 있는 첫 칸 또는 -1, 들여다본 칸 경로)

        키를 찾거나 EMPTY를 만나거나 M칸을 다 보면 멈춘다. TOMBSTONE은 건너뛴다.
        """
        i = self.index_of(key)
        first_free = -1
        path = []
        for _ in range(self.capacity):
            path.append(i)
            slot = self._slots[i]
            if slot is EMPTY:
                if first_free < 0:
                    first_free = i
                return -1, first_free, path
            if slot is TOMBSTONE:
                if first_free < 0:
                    first_free = i
            elif slot[0] == key:
                return i, first_free, path
            i = (i + 1) % self.capacity
        return -1, first_free, path

    def find(self, key):
        """(값 또는 None, 들여다본 칸 수). 실패 탐색은 마지막 EMPTY 칸도 센다."""
        found, _, path = self._probe(key)
        if found >= 0:
            return self._slots[found][1], len(path)
        return None, len(path)

    def probe_path(self, key):
        """탐색하며 들여다본 칸 번호 목록 (화면용)."""
        return self._probe(key)[2]

    def get(self, key, default=None):
        found, _, _ = self._probe(key)
        return self._slots[found][1] if found >= 0 else default

    def __contains__(self, key):
        return self._probe(key)[0] >= 0

    def put(self, key, value):
        found, free, _ = self._probe(key)
        if found >= 0:
            self._slots[found] = (key, value)      # 덮어쓰기
            return
        if free < 0:
            if self.max_load is not None:
                # max_load >= 1 이면 적재율 검사보다 먼저 칸이 바닥날 수 있다 → 늘린 뒤 다시 넣는다
                self._resize()
                return self.put(key, value)
            raise OverflowError("테이블이 가득 찼습니다 (capacity=%d)" % self.capacity)
        self._slots[free] = (key, value)
        self._size += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._resize()

    def remove(self, key):
        found, _, _ = self._probe(key)
        if found < 0:
            raise KeyError(key)
        value = self._slots[found][1]
        self._slots[found] = TOMBSTONE
        self._size -= 1
        return value

    def __len__(self):
        return self._size

    def load_factor(self):
        return self._size / self.capacity

    # ---- 크기 확장 (TOMBSTONE은 버린다) ----
    def _resize(self):
        old = self._slots
        self.capacity = next_prime(2 * self.capacity + 1)
        self._slots = [EMPTY] * self.capacity
        self._size = 0
        max_load, self.max_load = self.max_load, None
        for slot in old:
            if slot is not EMPTY and slot is not TOMBSTONE:
                self.put(slot[0], slot[1])
        self.max_load = max_load

    # ---- 조회·화면용 ----
    def items(self):
        return [s for s in self._slots if s is not EMPTY and s is not TOMBSTONE]

    def keys(self):
        return [k for k, _ in self.items()]

    def snapshot(self):
        """칸마다 None(EMPTY) / TOMBSTONE / (key, value)."""
        return list(self._slots)

    def stats(self):
        used = 0
        longest = 0
        run = 0
        # 원형 배열이므로 두 바퀴 돌며 군집(비어 있지 않은 연속 칸) 길이를 잰다
        for j in range(2 * self.capacity):
            slot = self._slots[j % self.capacity]
            if slot is EMPTY:
                run = 0
            else:
                run += 1
                if run > longest:
                    longest = run
            if j < self.capacity and slot is not EMPTY and slot is not TOMBSTONE:
                used += 1
        return TableStats(self.capacity, self._size, used, min(longest, self.capacity), self.kind)

    def __repr__(self):
        return "LinearProbingTable(capacity=%d, size=%d)" % (self.capacity, self._size)
