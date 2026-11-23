# 명세: URL 단축기

초안은 에이전트가 쓰고, **본인이 읽고 고칩니다.** 무엇을 고쳤는지는 이슈에 댓글로 남깁니다.
에이전트는 이 파일을 읽고 구현합니다. 여기 적지 않은 것은 에이전트가 마음대로 정합니다.

## 1. 무엇을 만드는가

사용자가 브라우저 폼(또는 Python 함수)에 `http://`·`https://`로 시작하는 긴 URL을 넣으면,
서버가 짧은 코드(base62)를 발급해 `http://<호스트>/<코드>` 형태의 짧은 링크를 돌려준다.
짧은 링크로 접속하면 원래 URL로 302 리다이렉트한다.
URL↔코드 저장은 **직접 구현한 해시 테이블**로만 한다. 해시 테이블은 두 가지를 만든다.

- `HashTable` — 개별 체이닝(연결 리스트), 수업 단계(1~7)
- `LinearProbingTable` — 선형 탐지, 과제 단계(#8)

외부 라이브러리는 쓰지 않는다(Python 표준 모듈만).

### 비기능 요구사항

- `src/` 안에서 `dict`, `set`, 내장 `hash()`를 쓰지 않는다. 내장 `hash()`는 문자열에 대해
  실행마다 값이 바뀌어(PYTHONHASHSEED) 실험 재현성을 해친다.
- 실험은 난수 시드를 고정해 같은 명령이 같은 CSV를 만든다.
- 모든 기능은 `make test`(unittest)로 검증한다. 테스트를 먼저 쓴다.

## 2. base62 인코딩

- 모듈 `src/base62.py`, 함수 `encode(n) -> str`, `decode(s) -> int`.
- 글자 순서: `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`
  (0-9 → 0~9, a-z → 10~35, A-Z → 36~61). 대소문자를 구분한다.
- `encode(0) == "0"`. 그 밖의 수는 맨 앞에 `0`이 붙지 않는다.
- 음수는 `ValueError`, 정수가 아닌 값(`float`, `str`, `None`, `bool`)은 `TypeError`.
- `decode("")`는 `ValueError`. 위 62글자 밖의 글자(공백, `-`, `_`, 한글 등)가 하나라도 있으면 `ValueError`.
  문자열이 아니면 `TypeError`.
- 모든 n ≥ 0에 대해 `decode(encode(n)) == n` (왕복 보장).

## 3. 해시 테이블

### 3.1 공통 인터페이스 (두 구현이 같다)

| 메서드 | 동작 |
| --- | --- |
| `HashTable(capacity=11, max_load=…)` | 칸 수 `capacity`(≥1)로 시작. `max_load=None`이면 크기를 바꾸지 않는다 |
| `put(key, value)` | 없으면 넣고, 있으면 값을 덮어쓴다. 키는 `str`만 받는다(아니면 `TypeError`) |
| `get(key, default=None)` | 값을 돌려주고, 없으면 `default` |
| `find(key)` | `(값 또는 None, 비교 횟수)` 를 돌려준다. 실험용 |
| `remove(key)` | 지우고 값을 돌려준다. 없으면 `KeyError` |
| `len(t)` / `key in t` | 저장된 키 개수 / 포함 여부 |
| `load_factor()` | `len(t) / capacity` |
| `capacity` | 현재 칸 수 |
| `keys()` / `items()` | 저장된 키 / (키, 값) 목록(list) |
| `index_of(key)` | 호너 해시로 계산한 처음 칸 번호 |
| `horner_steps(key)` | 호너 해시 계산 과정(글자, ord, 중간값) 목록. `/table` 화면용 |
| `snapshot()` | 내부 배열 상태(칸별 내용). 화면·디버깅용 |
| `stats()` | 칸 수, 키 수, 적재율, 가장 긴 체인(또는 가장 긴 군집) 등 |

### 3.2 해시 함수 (호너 방식, 주제 08)

```
h = 0
for c in key:
    h = (31 * h + ord(c)) % M
index = h
```

`M`은 현재 칸 수다. 크기를 바꾸면 새 `M`으로 모든 키를 다시 계산한다.

### 3.3 개별 체이닝 (`src/hash_table.py`의 `HashTable`)

- 각 칸은 단일 연결 리스트의 머리(`Node(key, value, next)`) 또는 `None`.
- 새 키는 리스트 **끝**에 붙인다(넣은 순서 = 리스트 순서, 화면에서 읽기 쉽게).
- 기본값 `capacity=11`, `max_load=1.0`. 넣은 뒤 적재율이 `max_load`를 넘으면
  칸 수를 `2M+1` 이상의 가장 작은 소수로 늘리고 모두 다시 넣는다.
- **비교 횟수**: 탐색하며 키를 비교한 노드 수.
  - 성공 탐색: 찾은 노드가 리스트의 k번째이면 k.
  - 실패 탐색: 그 칸의 리스트 길이(빈 칸이면 **0**). 빈 칸을 1로 세지 않는다.
  - 이론값: 성공 ≈ 1 + α/2, 실패 ≈ α.

### 3.4 선형 탐지 (`src/linear_probing.py`의 `LinearProbingTable`)

- 각 칸은 `EMPTY`, `TOMBSTONE`(지운 자리), 또는 `(key, value)` 하나.
- 충돌하면 `index = (index + 1) % M` 으로 다음 칸을 본다(끝 칸 다음은 0번 칸).
- 탐색은 키를 찾거나 `EMPTY`를 만나면 멈춘다. `TOMBSTONE`은 건너뛰고 계속 간다.
  M칸을 모두 보고도 못 찾으면 실패.
- 삽입은 키가 이미 있으면 덮어쓰고, 없으면 지나온 첫 `TOMBSTONE` 자리(없으면 처음 만난 `EMPTY`)에 넣는다.
- 삭제는 칸을 `TOMBSTONE`으로 바꾼다(탐색 경로가 끊기지 않게).
- 기본값 `capacity=11`, `max_load=0.5`. 넣은 뒤 적재율이 넘으면 체이닝과 같은 규칙으로 늘린다
  (늘릴 때 TOMBSTONE은 버린다).
- `max_load=None`에서 빈 칸(EMPTY와 TOMBSTONE 모두 없음)이 없는데 새 키를 넣으면 `OverflowError`("테이블이 가득 참").
- **비교 횟수(들여다본 칸 수)**: 탐색하며 본 칸의 수. 실패 탐색은 마지막 `EMPTY` 칸도 1로 센다.
  - 이론값: 성공 ≈ (1 + 1/(1−α))/2, 실패 ≈ (1 + 1/(1−α)²)/2.

## 4. 단축기 (`src/shortener.py`의 `Shortener`)

- `Shortener(table="chaining" | "linear")`: 어떤 해시 테이블을 쓸지 고른다. 기본은 `"chaining"`.
  해시 테이블 클래스를 직접 넘겨도 된다.
- 내부에 테이블 두 개를 둔다: `URL → 코드`(중복 확인용), `코드 → URL`(조회·리다이렉트용).
- `shorten(url) -> code`
  - 코드는 **1부터 증가하는 일련번호**를 base62로 바꾼 것이다(1 → `"1"`, 62 → `"10"`).
    URL의 해시값으로 코드를 만들지 않는다(서로 다른 URL이 같은 코드를 받을 수 있으므로).
  - **같은 URL을 다시 넣으면** 새 번호를 쓰지 않고 기존 코드를 돌려준다.
  - URL 앞뒤 공백은 잘라 낸 뒤 검사한다. 비교는 글자 그대로 한다(대소문자, 끝 `/` 구분).
- `expand(code) -> url 또는 None`: 없는 코드, 빈 문자열, base62가 아닌 글자는 **`None`** (예외 아님).
- `len(shortener)`: 발급한 코드 수.

### 4.1 URL 검증 (어기면 `ValueError`)

- 문자열이 아니면 `TypeError`.
- 앞뒤 공백을 자른 뒤 빈 문자열이면 거부.
- 스킴은 `http://` 또는 `https://` 만 허용(대소문자 무시). `ftp://`, `javascript:`, 스킴 없음은 거부.
- 스킴 뒤 호스트가 비어 있으면 거부(`http://`, `https:///path`).
- 중간에 공백 문자(스페이스, 탭, 줄바꿈)가 있으면 거부.
- 길이는 2048자 이하. 넘으면 거부.

## 5. 웹 서버 (`src/server.py`)

- 표준 모듈 `http.server`만 쓴다. `make serve`로 포트 8000에서 실행한다.
  `make serve TABLE=linear`(또는 `--table linear`)이면 선형 탐지 단축기를 리다이렉트에 쓴다.
- 서버는 두 단축기(체이닝, 선형 탐지)에 같은 URL을 같은 순서로 넣는다. 일련번호가 같으므로 두 쪽이 같은 코드를 낸다.

| 요청 | 응답 |
| --- | --- |
| `GET /` | URL 입력 폼(HTML) |
| `POST /shorten` (폼 필드 `url`) | 결과 화면: 짧은 링크, 원본 URL, 코드. 잘못된 URL이면 400과 오류 메시지가 있는 폼 |
| `GET /<code>` | 있으면 302, `Location: 원본 URL`. 없으면 404 화면 |
| `GET /expand?code=<code>` | 원본 URL 조회 화면(리다이렉트하지 않음). 없으면 404 |
| `GET /table?impl=chaining\|linear` | 현재 해시 테이블 시각화 |
| 그 밖의 경로·메서드 | 404 / 405 |

- 짧은 링크의 호스트는 `X-Forwarded-Host`(있으면) → `Host` 순서로 정하고, 스킴은
  `X-Forwarded-Proto`(있으면) → `http`. Codespaces 공개 포트 주소로 휴대폰에서 열 수 있어야 한다.
- HTML에 넣는 사용자 입력은 모두 이스케이프한다.
- `/table`
  - 체이닝: 칸 번호마다 연결 리스트 노드를 화살표로 잇고 끝은 `NULL`. 노드에 URL 키, 짧은 코드, 짧은 링크.
    노드를 펼치면 호너 해시 계산 과정(글자별 `h = (31·h + ord(c)) mod M`)이 보인다.
  - 선형 탐지: 칸마다 키 하나(또는 빈 칸/TOMBSTONE). 처음 계산한 칸, 실제 저장 칸, 몇 칸을 탐색했는지(탐색 경로), 호너 계산 근거.
  - 화면에서 키를 입력하면 삽입·검색 과정을 단계별로 보여 주는 애니메이션(현재 테이블 기준, 테이블은 바꾸지 않음).
  - 데스크톱과 휴대폰 화면 모두에서 읽을 수 있게 한다.

## 6. 경계 사례 (4단계 테스트로 옮긴다)

해시 테이블(두 구현 공통)
1. 빈 테이블에서 `get`은 `None`(또는 default), `in`은 False, `len`은 0.
2. `put` 후 `get`이 같은 값, 같은 키 `put`은 덮어쓰고 `len`은 그대로.
3. 같은 칸으로 가는 서로 다른 키(충돌) 여러 개를 넣고 모두 찾는다.
4. 충돌한 키 중 가운데 것을 지운 뒤 나머지를 모두 찾는다(선형 탐지는 TOMBSTONE 확인).
5. 없는 키 `remove`는 `KeyError`. 지운 키는 `get`이 `None`, `in`이 False.
6. 빈 문자열 키 `""`도 키로 쓸 수 있다(해시값 0).
7. 문자열이 아닌 키는 `TypeError`.
8. 호너 해시가 명세 식과 같다(손으로 계산한 값과 비교).
9. `max_load`를 넘으면 칸 수가 늘고 모든 키를 여전히 찾는다. `max_load=None`이면 늘지 않는다.
10. `find`의 비교 횟수: 빈 칸 실패 탐색 0(체이닝), 체인 k번째 성공 탐색 k.
11. 대량 데이터(수천 개)를 넣고 모두 찾는다.
12. capacity=1 같은 아주 작은 테이블.
13. (선형 탐지) 끝 칸에서 0번 칸으로 넘어가는 삽입·탐색.
14. (선형 탐지) 가득 찬 테이블에 새 키 → `OverflowError`, 있는 키 덮어쓰기는 허용, 가득 찬 테이블에서 없는 키 탐색은 M칸 후 실패.
15. (선형 탐지) TOMBSTONE 자리에 다시 넣기.

단축기(두 테이블 모두에서)
1. 첫 코드는 `"1"`, 다음은 `"2"` … 62번째는 `"10"` (일련번호 base62).
2. 같은 URL 두 번 → 같은 코드, `len` 그대로.
3. 다른 URL → 다른 코드.
4. `expand(shorten(u)) == u`.
5. 없는 코드, 빈 코드, base62 밖 글자 → `None`.
6. `ftp://`, `javascript:`, 스킴 없음, `http://`(호스트 없음) → `ValueError`.
7. 공백이 들어간 URL → `ValueError`. 앞뒤 공백은 잘라서 받는다.
8. 2048자 URL은 받고, 2049자는 `ValueError`.
9. 대문자 스킴 `HTTPS://`는 받는다.
10. 대량(수천 개) URL을 줄이고 모두 되돌린다.
11. 체이닝 단축기와 선형 탐지 단축기가 같은 입력에 같은 코드를 낸다.

## 7. 실험

- 6단계 `experiments/probe_experiment.py` (`make experiment`): `HashTable(capacity=4093, max_load=None)`,
  적재율 0.25~4.00 (0.25 간격). 무작위 URL(시드 고정)을 넣고 성공·실패 탐색의 평균 비교 노드 수를
  이론값과 함께 `experiments/results.csv`, `experiments/results.svg`로 저장한다.
- 과제 `experiments/comparison_experiment.py` (`make comparison`): 같은 칸 수(4093), 같은 URL, 같은 호너 해시로
  적재율 0.1~0.9 (0.1 간격)에서 두 구현의 성공·실패 탐색 비용을 이론값과 함께
  `experiments/comparison_results.csv`, `experiments/comparison_results.svg`로 저장한다.
- 그래프는 표준 모듈만으로 SVG를 직접 쓴다. 제목, 축 이름, 범례, 실험값과 이론값을 모두 담는다.
