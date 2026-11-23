"""두 해시 테이블이 함께 쓰는 해시 함수와 보조 함수 (SPEC.md 3.2).

내장 hash()는 쓰지 않는다. 문자열 hash()는 실행마다 값이 바뀌기 때문이다.
"""

HORNER_BASE = 31


def _check_key(key):
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 합니다: %r" % (key,))


def horner_hash(key, m):
    """호너 방식 해시: h = (31*h + ord(c)) % m."""
    _check_key(key)
    h = 0
    for c in key:
        h = (HORNER_BASE * h + ord(c)) % m
    return h


def horner_steps(key, m):
    """화면용 계산 과정. [(글자, ord(글자), 그 글자까지의 h), ...]"""
    _check_key(key)
    steps = []
    h = 0
    for c in key:
        h = (HORNER_BASE * h + ord(c)) % m
        steps.append((c, ord(c), h))
    return steps


def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def next_prime(n):
    """n 이상의 가장 작은 소수."""
    if n <= 2:
        return 2
    while not is_prime(n):
        n += 1
    return n


class TableStats:
    """stats() 결과. dict 대신 속성으로 담는다."""

    def __init__(self, capacity, size, used_slots, longest_run, kind):
        self.capacity = capacity
        self.size = size
        self.load_factor = size / capacity
        self.used_slots = used_slots        # 비어 있지 않은 칸 수
        self.longest_run = longest_run      # 가장 긴 체인 / 가장 긴 군집
        self.kind = kind

    # 체이닝에서 읽기 좋은 이름
    @property
    def longest_chain(self):
        return self.longest_run

    @property
    def longest_cluster(self):
        return self.longest_run

    def __repr__(self):
        return ("TableStats(kind=%s, capacity=%d, size=%d, load_factor=%.3f, "
                "used_slots=%d, longest_run=%d)" % (
                    self.kind, self.capacity, self.size, self.load_factor,
                    self.used_slots, self.longest_run))
