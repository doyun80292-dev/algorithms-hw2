"""URL 단축기 (SPEC.md 4절).

코드 = 1부터 증가하는 일련번호의 base62. URL 해시값으로 코드를 만들지 않는다.
URL→코드, 코드→URL 두 방향 모두 직접 만든 해시 테이블에 저장한다.
"""
import base62
from hash_table import HashTable

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = ("http://", "https://")
WHITESPACE = " \t\r\n\v\f"


def _table_class(table):
    if table == "chaining":
        return HashTable
    if table == "linear":
        from linear_probing import LinearProbingTable
        return LinearProbingTable
    if isinstance(table, type):
        return table
    raise ValueError("table은 'chaining' 또는 'linear'이어야 합니다: %r" % (table,))


def validate_url(url):
    """검사를 통과한 URL(앞뒤 공백 제거)을 돌려준다. SPEC.md 4.1."""
    if not isinstance(url, str):
        raise TypeError("URL은 문자열이어야 합니다")
    url = url.strip(WHITESPACE)
    if url == "":
        raise ValueError("URL이 비어 있습니다")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL이 너무 깁니다 (최대 %d자)" % MAX_URL_LENGTH)
    for ch in url:
        if ch in WHITESPACE:
            raise ValueError("URL 중간에 공백이 있습니다")
    lower = url.lower()
    rest = None
    for scheme in ALLOWED_SCHEMES:
        if lower.startswith(scheme):
            rest = url[len(scheme):]
            break
    if rest is None:
        raise ValueError("http:// 또는 https:// 로 시작하는 URL만 줄일 수 있습니다")
    host = rest
    for sep in "/?#":
        cut = host.find(sep)
        if cut >= 0:
            host = host[:cut]
    if host == "":
        raise ValueError("URL에 호스트가 없습니다")
    return url


class Shortener:
    def __init__(self, table="chaining", capacity=11, max_load="default"):
        cls = _table_class(table)
        self.table_name = table if isinstance(table, str) else getattr(cls, "kind", cls.__name__)
        if max_load == "default":
            self.url_table = cls(capacity=capacity)     # URL → 코드
            self.code_table = cls(capacity=capacity)    # 코드 → URL
        else:
            self.url_table = cls(capacity=capacity, max_load=max_load)
            self.code_table = cls(capacity=capacity, max_load=max_load)
        self._next_id = 1

    def shorten(self, url):
        url = validate_url(url)
        existing = self.url_table.get(url)
        if existing is not None:
            return existing                 # 같은 URL → 기존 코드
        code = base62.encode(self._next_id)
        self._next_id += 1
        self.url_table.put(url, code)
        self.code_table.put(code, url)
        return code

    def expand(self, code):
        """원본 URL, 없으면 None (예외를 던지지 않는다)."""
        if not isinstance(code, str) or code == "":
            return None
        try:
            base62.decode(code)
        except ValueError:
            return None
        return self.code_table.get(code)

    def __len__(self):
        return len(self.code_table)
