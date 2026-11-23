"""시드를 고정한 무작위 URL 생성기 (두 실험이 함께 쓴다).

중복 확인도 set 대신 직접 만든 HashTable로 한다.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable  # noqa: E402

SEED = 20261120
LETTERS = "abcdefghijklmnopqrstuvwxyz"
PATH_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-_"
TLDS = ("com", "net", "org", "kr", "io", "co.kr", "ac.kr", "dev")


def random_url(rng):
    domain = "".join(rng.choice(LETTERS) for _ in range(rng.randint(4, 12)))
    parts = []
    for _ in range(rng.randint(1, 4)):
        parts.append("".join(rng.choice(PATH_CHARS) for _ in range(rng.randint(3, 10))))
    url = "https://%s.%s/%s" % (domain, rng.choice(TLDS), "/".join(parts))
    if rng.random() < 0.3:
        url += "?id=%d" % rng.randint(0, 10 ** 6)
    return url


def unique_urls(count, seed=SEED):
    """서로 다른 무작위 URL count개 (같은 seed면 항상 같은 목록)."""
    rng = random.Random(seed)
    seen = HashTable(capacity=10007)
    out = []
    while len(out) < count:
        u = random_url(rng)
        if u not in seen:
            seen.put(u, True)
            out.append(u)
    return out
