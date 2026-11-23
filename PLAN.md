# 구현 계획 (PLAN.md)

`SPEC.md`를 기준으로 한 단계별 구현 계획이다. 명세와 다르면 **명세가 우선**한다.
모든 단계는 **테스트 작성 → 실패 확인 → 구현 → `make test` 통과 → 커밋** 순서로 진행한다.

## 1. 아키텍처

```
브라우저 ──HTTP──▶ src/server.py (http.server)
                     │  두 Shortener에 같은 URL을 같은 순서로 넣음
                     ├─▶ Shortener(table="chaining") ─▶ HashTable ×2 (URL→코드, 코드→URL)
                     └─▶ Shortener(table="linear")   ─▶ LinearProbingTable ×2
                                  │
                                  └─ 코드 = base62.encode(일련번호)
experiments/*.py ─▶ HashTable / LinearProbingTable 직접 사용 ─▶ CSV + SVG
report/build_report.py ─▶ CSV + SVG ─▶ report/final_report.html ─▶ (Chrome) final_report.pdf
```

## 2. 디렉터리 구조

```
src/
  base62.py            encode, decode
  hashing.py           horner_hash, horner_steps, next_prime (두 테이블이 공유)
  hash_table.py        Node, HashTable (개별 체이닝)
  linear_probing.py    LinearProbingTable (선형 탐지, TOMBSTONE)
  shortener.py         Shortener, validate_url
  server.py            http.server 기반 웹 서버, HTML 렌더링
tests/
  test_base62.py
  test_hash_table.py       공통 테스트 믹스인 + 체이닝 전용 테스트
  test_linear_probing.py   공통 테스트 믹스인 재사용 + 선형 탐지 전용 테스트
  test_shortener.py        두 테이블 모두에 대해 같은 테스트
  test_server.py           실제 서버를 스레드로 띄워 HTTP 요청으로 확인
experiments/
  urlgen.py                시드 고정 무작위 URL 생성기 (중복 확인도 HashTable로)
  svgplot.py               표준 모듈만 쓰는 SVG 꺾은선 그래프
  probe_experiment.py      → results.csv, results.svg
  comparison_experiment.py → comparison_results.csv, comparison_results.svg
report/
  build_report.py, final_report.pdf
.github/copilot-instructions.md   에이전트 규칙
```

## 3. 클래스·함수 설계

### hashing.py
- `horner_hash(key, m) -> int` : `h = (31*h + ord(c)) % m`
- `horner_steps(key, m) -> list[(c, ord(c), h)]` : 화면용 중간값
- `next_prime(n) -> int` : n 이상의 가장 작은 소수 (크기 확장용)

### hash_table.py
- `Node(key, value, next)`
- `HashTable(capacity=11, max_load=1.0)`
  - 필드: `_buckets`(list, 칸마다 Node 또는 None), `_size`, `capacity`, `max_load`
  - `put/get/find/remove/__len__/__contains__/load_factor/keys/items/index_of/horner_steps/snapshot/stats`
  - `_resize()` : `next_prime(2*M+1)`로 늘리고 모든 노드를 다시 넣음
  - `find(key)` 는 `(value|None, comparisons)` — 비교한 노드 수

### linear_probing.py
- `EMPTY`, `TOMBSTONE` 표식 객체(고유 객체, `is`로 비교)
- `LinearProbingTable(capacity=11, max_load=0.5)` — 위와 같은 메서드
  - `_probe(key)` : `(찾은 칸 또는 -1, 넣을 칸 또는 -1, 들여다본 칸 수, 경로)`
  - 가득 찬 테이블에 새 키 → `OverflowError`

### shortener.py
- `validate_url(url) -> str` (앞뒤 공백 제거한 URL, 어기면 ValueError/TypeError)
- `Shortener(table="chaining")` : `shorten`, `expand`, `__len__`, `url_table`, `code_table`, `table_name`
  - 일련번호 `_next_id`는 1부터, `base62.encode(_next_id)`로 코드 생성

### server.py
- `make_handler(app)` 로 요청 처리 클래스를 만든다(테스트에서 포트 0으로 띄우기 위해)
- `App` : 두 Shortener 보관, `primary`(리다이렉트에 쓸 쪽) 선택
- 렌더 함수: `render_index`, `render_result`, `render_table_chaining`, `render_table_linear`
- `base_url(headers)` : `X-Forwarded-Proto`/`X-Forwarded-Host` 우선, 없으면 `Host`

## 4. 구현 순서 (이슈 = 단계)

| 이슈 | 브랜치 | 할 일 | 완료 조건 |
| --- | --- | --- | --- |
| #1 | feature/1-base62 | 테스트 → base62 | `make test` 통과 |
| #2 | feature/2-spec | SPEC.md | TEMPLATE 줄 삭제, 경계 사례 목록 |
| #3 | feature/3-plan | PLAN.md | 명세와 모순 없음 |
| #4 | feature/4-hash-table | **테스트 먼저** (`test_hash_table.py`, `test_shortener.py`) → 실패 확인 커밋 → `hashing.py`, `hash_table.py`, `shortener.py` 구현 | 테스트 수정 없이 통과 |
| #5 | feature/5-rules | `.github/copilot-instructions.md`, `src/` 규칙 위반 검사(grep + 코드 문맥) | 위반 0 |
| #6 | feature/6-experiment | `probe_experiment.py`, CSV, SVG | 적재율 1에서 이론값과 근접 |
| #7 | feature/7-server | `test_server.py` 먼저 → `server.py`, `/table` | 브라우저로 확인 |
| #8 | feature/8-linear-probing | 선형 탐지 테스트 → 구현 → 단축기 교체 → 비교 실험 → `/table` 확장 → 보고서 | 두 테이블에서 모든 테스트 통과 |

## 5. 테스트 전략

- `unittest`만 쓴다. `make test` = `python3 -m unittest discover -s tests -v`.
- 해시 테이블 테스트는 **믹스인 클래스**(`HashTableContract`)로 작성하고, 체이닝/선형 탐지 테스트 클래스가
  `TABLE_CLASS`만 바꿔 같은 테스트를 상속한다.
- 단축기 테스트도 같은 방식으로 `"chaining"`, `"linear"` 두 번 돈다.
- 충돌 키는 손으로 찾지 않고 테스트 안에서 `horner_hash`가 같은 칸을 주는 키를 찾아 쓴다.
- 실패하면 테스트가 아니라 코드를 고친다.

## 6. 실험 계획

- 시드 고정(`random.Random(20261120)`), 무작위 URL은 `https://<도메인>/<경로>` 꼴, 중복은 `HashTable`로 거른다.
- 6단계: M=4093, α = 0.25 … 4.00. 각 α에서 n = round(α·M)개를 새 테이블에 넣고
  성공 탐색 = 넣은 키 전부의 평균 비교 수, 실패 탐색 = 넣지 않은 URL 5000개의 평균.
- 과제: M=4093, α = 0.1 … 0.9, 같은 URL 목록 앞부분 n개를 두 테이블에 넣어 같은 방식으로 측정.
- CSV 열: `load_factor, n, success_measured, success_theory, fail_measured, fail_theory` (비교 실험은 두 방식 열).

## 7. 웹 서비스 계획

- 7단계에서 체이닝 버전, #8에서 선형 탐지 버전과 `/table?impl=` 전환, 단계별 애니메이션(JS) 추가.
- 확인: `make serve` → `/` → URL 입력 → 결과 → 짧은 링크 → 302 → `/table`. 자동 테스트 + 실제 브라우저로 확인.

## 8. 보고서 계획

- `make report` → `report/build_report.py`가 CSV·SVG를 읽어 HTML을 만들고, Chrome이 있으면 PDF로 인쇄.
- 2쪽 이내, 첫 줄에 저장소 URL, 한글 글꼴(Noto Sans/Serif CJK KR).
- "에이전트가 틀린 곳"은 커밋 이력과 테스트 결과로 확인된 실제 사례만 쓴다.

## 9. 명세 대조 체크리스트

- [x] URL→코드 저장에 `dict`를 쓰지 않는다 → 두 방향 모두 직접 만든 해시 테이블.
- [x] 코드는 URL 해시값이 아니라 일련번호의 base62.
- [x] 테스트를 마지막이 아니라 각 구현 **전에** 쓴다(#4, #7, #8).
- [x] 체이닝 실패 탐색에서 빈 칸은 0으로 센다(SPEC 3.3).
- [x] 없는 코드 조회는 예외가 아니라 `None`(SPEC 4).
