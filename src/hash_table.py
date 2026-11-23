"""개별 체이닝 해시 테이블 (SPEC.md 3.3).

각 칸은 단일 연결 리스트의 머리 노드 또는 None.
dict, set, 내장 hash()를 쓰지 않는다.
"""
from hashing import TableStats, horner_hash, horner_steps, next_prime


class Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next=None):
        self.key = key
        self.value = value
        self.next = next


class HashTable:
    kind = "chaining"

    def __init__(self, capacity=11, max_load=1.0):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity는 1 이상의 정수여야 합니다")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load는 양수 또는 None이어야 합니다")
        self.capacity = capacity
        self.max_load = max_load
        self._buckets = [None] * capacity
        self._size = 0

    # ---- 해시 ----
    def index_of(self, key):
        return horner_hash(key, self.capacity)

    def horner_steps(self, key):
        return horner_steps(key, self.capacity)

    # ---- 기본 연산 ----
    def find(self, key):
        """(값 또는 None, 비교한 노드 수). 빈 칸에서 실패하면 0."""
        node = self._buckets[self.index_of(key)]
        comparisons = 0
        while node is not None:
            comparisons += 1
            if node.key == key:
                return node.value, comparisons
            node = node.next
        return None, comparisons

    def _find_node(self, key):
        node = self._buckets[self.index_of(key)]
        while node is not None:
            if node.key == key:
                return node
            node = node.next
        return None

    def get(self, key, default=None):
        node = self._find_node(key)
        return default if node is None else node.value

    def __contains__(self, key):
        return self._find_node(key) is not None

    def put(self, key, value):
        i = self.index_of(key)
        node = self._buckets[i]
        if node is None:
            self._buckets[i] = Node(key, value)
        else:
            while True:
                if node.key == key:
                    node.value = value      # 덮어쓰기
                    return
                if node.next is None:
                    break
                node = node.next
            node.next = Node(key, value)    # 리스트 끝에 붙인다
        self._size += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._resize()

    def remove(self, key):
        i = self.index_of(key)
        prev = None
        node = self._buckets[i]
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._buckets[i] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                return node.value
            prev, node = node, node.next
        raise KeyError(key)

    def __len__(self):
        return self._size

    def load_factor(self):
        return self._size / self.capacity

    # ---- 크기 확장 ----
    def _resize(self):
        old = self._buckets
        self.capacity = next_prime(2 * self.capacity + 1)
        self._buckets = [None] * self.capacity
        self._size = 0
        max_load, self.max_load = self.max_load, None   # 다시 넣는 동안 확장 금지
        for head in old:
            node = head
            while node is not None:
                self.put(node.key, node.value)
                node = node.next
        self.max_load = max_load

    # ---- 조회·화면용 ----
    def items(self):
        out = []
        for head in self._buckets:
            node = head
            while node is not None:
                out.append((node.key, node.value))
                node = node.next
        return out

    def keys(self):
        return [k for k, _ in self.items()]

    def snapshot(self):
        """칸마다 [(key, value), ...] (리스트 순서 그대로)."""
        snap = []
        for head in self._buckets:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            snap.append(chain)
        return snap

    def stats(self):
        used = 0
        longest = 0
        for head in self._buckets:
            length = 0
            node = head
            while node is not None:
                length += 1
                node = node.next
            if length:
                used += 1
            if length > longest:
                longest = length
        return TableStats(self.capacity, self._size, used, longest, self.kind)

    def __repr__(self):
        return "HashTable(capacity=%d, size=%d)" % (self.capacity, self._size)
