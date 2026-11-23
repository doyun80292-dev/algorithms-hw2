"""base62 인코딩/디코딩.

글자 순서는 0-9, a-z, A-Z (SPEC.md 2절).
dict를 쓰지 않으므로 디코딩은 ALPHABET.find()로 글자 위치를 찾는다.
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def encode(n):
    """0 이상의 정수 n을 base62 문자열로 바꾼다. encode(0) == "0"."""
    # bool은 int의 하위 클래스이므로 따로 막는다.
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("encode()는 정수만 받습니다: %r" % (n,))
    if n < 0:
        raise ValueError("encode()는 0 이상의 정수만 받습니다: %d" % n)
    if n == 0:
        return ALPHABET[0]
    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    digits.reverse()
    return "".join(digits)


def decode(s):
    """base62 문자열 s를 정수로 바꾼다. 빈 문자열·허용되지 않은 글자는 ValueError."""
    if not isinstance(s, str):
        raise TypeError("decode()는 문자열만 받습니다: %r" % (s,))
    if s == "":
        raise ValueError("빈 문자열은 디코딩할 수 없습니다")
    n = 0
    for ch in s:
        d = ALPHABET.find(ch) if len(ch) == 1 else -1
        if d < 0:
            raise ValueError("base62에 없는 글자입니다: %r" % ch)
        n = n * BASE + d
    return n
