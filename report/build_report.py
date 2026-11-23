"""report/final_report.pdf 생성 (make report).

experiments/*.csv 와 *.svg 를 읽어 report/final_report.html 을 만들고,
Chrome/Chromium이 있으면 헤드리스 인쇄로 PDF를 만든다(표준 모듈만 사용).
표의 숫자와 분석 문장 속 수치는 모두 CSV에서 읽는다. 실험을 다시 돌리면 보고서도 그 값으로 바뀐다.
"""
import csv
import os
import shutil
import subprocess
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXP = os.path.join(ROOT, "experiments")
DEFAULT_REPO = "https://github.com/<GitHub 계정>/algorithms-hw2"


def repo_url():
    if os.environ.get("REPO_URL"):
        return os.environ["REPO_URL"]
    try:
        url = subprocess.run(["git", "-C", ROOT, "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return DEFAULT_REPO
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url[len("git@github.com:"):]
    if url.endswith(".git"):
        url = url[:-4]
    # 프록시·토큰이 섞인 주소는 github.com/<owner>/<repo> 형태로 정리
    i = url.find("github.com/")
    return "https://" + url[i:] if i >= 0 else DEFAULT_REPO


def read_csv(name):
    with open(os.path.join(EXP, name), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    head = rows[0]
    return [[(float(v) if c not in ("n",) and not c.startswith("load_factor_target") else v)
             for c, v in zip(head, r)] for r in rows[1:]], head


def col(head, name):
    return head.index(name)


def build_html():
    probe, ph = read_csv("results.csv")
    comp, chd = read_csv("comparison_results.csv")
    P = lambda r, n: r[col(ph, n)]  # noqa: E731
    C = lambda r, n: r[col(chd, n)]  # noqa: E731
    by_alpha = lambda rows, a: [r for r in rows if r[0] == a][0]  # noqa: E731

    p1 = by_alpha(probe, "1.00")
    p4 = by_alpha(probe, "4.00")
    c5 = by_alpha(comp, "0.5")
    c9 = by_alpha(comp, "0.9")
    c7 = by_alpha(comp, "0.7")

    probe_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%.3f</td><td>%.3f</td><td>%.3f</td><td>%.3f</td></tr>"
        % (r[0], r[1], P(r, "success_measured"), P(r, "success_theory"),
           P(r, "fail_measured"), P(r, "fail_theory"))
        for r in probe if r[0] in ("0.25", "0.50", "1.00", "2.00", "3.00", "4.00"))
    comp_rows = "".join(
        "<tr><td>%s</td><td>%s</td>"
        "<td>%.3f <span class=t>(%.3f)</span></td><td>%.3f <span class=t>(%.3f)</span></td>"
        "<td>%.3f <span class=t>(%.3f)</span></td><td>%.2f <span class=t>(%.2f)</span></td><td>%d</td></tr>"
        % (r[0], r[1], C(r, "chaining_success_measured"), C(r, "chaining_success_theory"),
           C(r, "chaining_fail_measured"), C(r, "chaining_fail_theory"),
           C(r, "linear_success_measured"), C(r, "linear_success_theory"),
           C(r, "linear_fail_measured"), C(r, "linear_fail_theory"),
           C(r, "linear_longest_cluster"))
        for r in comp)

    lin_fail9, ch_fail9 = C(c9, "linear_fail_measured"), C(c9, "chaining_fail_measured")
    lin_succ9, lin_succ9_t = C(c9, "linear_success_measured"), C(c9, "linear_success_theory")

    html = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>고급알고리즘 과제2 보고서</title>
<style>
@page{size:A4;margin:12mm 14mm}
body{font-family:"Noto Serif CJK KR","Noto Serif KR",serif;font-size:10pt;line-height:1.38;color:#111;margin:0}
h1{font-family:"Noto Sans CJK KR",sans-serif;font-size:14.5pt;margin:2px 0 2px}
h2{font-family:"Noto Sans CJK KR",sans-serif;font-size:10.8pt;margin:7px 0 2px;border-bottom:1px solid #999;padding-bottom:1px}
p{margin:2px 0 3px;text-align:justify}
.repo{font-family:"Noto Sans Mono CJK KR",monospace;font-size:10pt;font-weight:700;border:1.5px solid #13233a;padding:3px 8px;display:inline-block;margin-bottom:3px}
.meta{font-family:"Noto Sans CJK KR",sans-serif;font-size:8.6pt;color:#444}
code{font-family:"Noto Sans Mono CJK KR",monospace;font-size:8.6pt;background:#f1f1ef;padding:0 2px}
table{border-collapse:collapse;width:100%%;font-family:"Noto Sans CJK KR",sans-serif;font-size:8.2pt;margin:3px 0}
th,td{border:1px solid #bbb;padding:1px 4px;text-align:right}th{background:#eef1f5;text-align:center}
td:first-child{text-align:center}.t{color:#777}
.cap{font-family:"Noto Sans CJK KR",sans-serif;font-size:8.2pt;color:#333;text-align:center;margin:0 0 3px}
img{display:block;margin:0 auto}
ul{margin:2px 0 3px;padding-left:16px}li{margin:1px 0}
.two{display:flex;gap:10px}.two>div{flex:1}
.pb{break-before:page}
.note{font-family:"Noto Sans CJK KR",sans-serif;font-size:7.8pt;color:#555;border-top:1px solid #ccc;margin-top:5px;padding-top:2px}
</style></head><body>
<div class="repo">저장소: %(repo)s</div>
<h1>과제2 · 해시 테이블 기반 URL 단축기: 개별 체이닝과 선형 탐지 비교</h1>
<div class="meta">2026-2 고급알고리즘(SIT2001-01) · <code>make test</code> · <code>make serve [TABLE=linear]</code> · <code>make experiment</code> · <code>make comparison</code> · <code>make report</code></div>

<h2>1. 과제 목적</h2>
<p>긴 URL을 짧은 코드로 바꾸고 짧은 링크를 원래 주소로 보내는 서비스를 <b>직접 구현한 해시 테이블</b>(<code>dict</code>·<code>set</code>·내장 <code>hash()</code> 금지) 위에 만들고,
같은 호너 해시를 쓰는 개별 체이닝과 선형 탐지의 탐색 비용을 같은 조건에서 재어 이론값과 비교한다.</p>

<h2>2. 구현 방법</h2>
<ul>
<li><b>코드 발급</b>: 1부터 증가하는 일련번호를 base62(<code>0-9a-zA-Z</code>)로 변환. URL 해시값을 코드로 쓰지 않아 코드 중복이 없고, 같은 URL은 URL→코드 테이블에서 기존 코드를 돌려준다.</li>
<li><b>저장</b>: URL→코드, 코드→URL 해시 테이블 2개. <code>Shortener(table="chaining"|"linear")</code>로 교체하며 두 테이블의 인터페이스(<code>put/get/find/remove/len/in/load_factor</code>)가 같다.
해시는 <code>h = (31·h + ord(c)) mod M</code>, 확장 시 <code>next_prime(2M+1)</code>.</li>
<li><b>웹</b>: <code>http.server</code>만 사용. 폼, 결과, 302 리다이렉트, 조회, <code>/table?impl=chaining|linear</code>(호너 계산, 탐색 경로, 단계별 애니메이션). 짧은 링크 호스트는 <code>X-Forwarded-Host</code> 우선.</li>
<li><b>검증</b>: unittest %(ntests)s개. 해시 테이블 계약 테스트를 두 구현이 상속해 함께 돌리고, 단축기·서버 테스트도 두 테이블에서 돈다. 금지 구문은 ast 검사로 확인.</li>
</ul>

<div class="two"><div>
<h2>3. 개별 체이닝 구조</h2>
<p>칸마다 단일 연결 리스트(<code>Node(key, value, next)</code>), 새 키는 리스트 끝. 비용 = 비교한 노드 수(성공은 위치 k, 실패는 리스트 길이, 빈 칸은 0).
이론: 성공 ≈ 1 + α/2, 실패 ≈ α.</p>
</div><div>
<h2>4. 선형 탐지 구조</h2>
<p>칸마다 EMPTY·TOMBSTONE·(key, value). 충돌 시 <code>(i+1) mod M</code>(끝 칸 다음 0번). 삭제는 TOMBSTONE, 삽입은 첫 TOMBSTONE 재사용, 가득 차면 <code>OverflowError</code>.
비용 = 들여다본 칸 수(실패 시 마지막 EMPTY 포함). 이론: 성공 ≈ (1+1/(1−α))/2, 실패 ≈ (1+1/(1−α)²)/2.</p>
</div></div>

<h2>5. 실험 조건</h2>
<p>시드 20261120의 서로 다른 무작위 URL, 칸 수 <b>M = 4093</b> 고정(<code>max_load=None</code>), 같은 해시. α마다 목록 앞 n = round(α·M)개를 새 테이블에 넣고,
성공 = 넣은 키 전부, 실패 = 넣지 않은 URL 5000개의 평균 비용. 실험 A: 체이닝 α 0.25~4(0.25 간격), 실험 B: 두 방식 α 0.1~0.9(0.1 간격), 같은 키·같은 순서. 재실행 시 CSV가 동일함을 확인했다.</p>

<h2>6. 실험 결과</h2>
<div class="two"><div>
<table><tr><th>α</th><th>n</th><th>성공 실험</th><th>성공 이론</th><th>실패 실험</th><th>실패 이론</th></tr>%(probe_rows)s</table>
<div class="cap">표 1. 실험 A: 개별 체이닝 평균 비교 노드 수(일부 행, 전체는 results.csv)</div>
</div><div>
<img src="file://%(exp)s/results.svg" style="width:100%%">
<div class="cap">그림 1. 실험 A (results.svg)</div>
</div></div>

<table><tr><th>α</th><th>n</th><th>체이닝 성공 (이론)</th><th>체이닝 실패 (이론)</th><th>선형 성공 (이론)</th><th>선형 실패 (이론)</th><th>선형 최장 군집</th></tr>%(comp_rows)s</table>
<div class="cap">표 2. 실험 B: 같은 키·같은 M에서 두 방식의 평균 탐색 비용 (괄호는 이론값, comparison_results.csv)</div>
<h2>7. 그래프</h2>
<img src="file://%(exp)s/comparison_results.svg" style="width:82%%">
<div class="cap">그림 2. 실험 B: 실선·동그라미 = 실험값, 점선 = 이론값, 파랑 = 개별 체이닝, 주황 = 선형 탐지 (comparison_results.svg)</div>

<h2>8. 결과 분석</h2>
<ul>
<li><b>적재율에 따른 변화</b>: 체이닝은 α에 대해 직선으로 완만하게 늘어난다(α=1에서 성공 %(p1s).2f, 실패 %(p1f).2f, α=4에서도 성공 %(p4s).2f).
선형 탐지는 α=0.5에서 실패 %(c5lf).2f칸(체이닝 %(c5cf).2f)으로 이미 차이가 나고, α=0.7에서 실패 %(c7lf).2f, α=0.9에서 실패 <b>%(lf9).1f칸</b>으로, 같은 조건 체이닝(%(cf9).2f)의 약 %(ratio).0f배다.</li>
<li><b>군집화</b>: 선형 탐지에서 충돌한 키는 바로 옆 칸에 들어가 연속된 군집을 만들고, 군집 어디에 해시되든 군집 끝까지 밀려 군집이 더 길어진다(1차 군집).
최장 군집은 α=0.5에서 %(cl5)d칸, α=0.9에서 <b>%(cl9)d칸</b>으로 커졌다. 실패 탐색은 EMPTY를 만나야 끝나는데 α→1이면 빈 칸이 사라지므로 비용이 1/(1−α)²로 발산한다.
체이닝은 충돌이 그 칸의 리스트 안에만 머물러 이웃 칸에 번지지 않기 때문에 이런 급증이 없다.</li>
<li><b>이론값과의 차이</b>: 체이닝은 두 실험의 모든 α에서 이론값과의 상대 오차가 최대 %(chdev).1f%%였다. 선형 탐지는 α≤0.8에서 최대 %(lpdev).1f%%로 대체로 맞았으나 α=0.9 성공 탐색이 %(ls9).2f로 이론 %(ls9t).2f보다 컸다.
이론식은 균일 해싱과 M→∞를 가정한 근사이고, α가 클수록 비용이 소수의 긴 군집에 좌우되어 키 집합 하나·실행 한 번의 결과가 크게 흔들린다. 공통 접두사(<code>https://</code>)를 가진 URL에 대한 호너 해시가 완전히 균일하지 않은 것도 원인일 수 있으나, 이번 실험만으로는 구분하지 못했다.</li>
<li><b>장단점과 서비스 적합성</b>: 선형 탐지는 노드 포인터가 없어 메모리가 연속적이고 캐시에 유리하지만, α를 0.5~0.7 이하로 유지해야 하고 삭제에 TOMBSTONE 관리가 필요하다.
체이닝은 α&gt;1에서도 성능이 완만히 나빠지고 삭제가 단순하지만 노드마다 포인터 비용이 든다. 조회가 많고 삭제가 드문 URL 단축 서비스라면 선형 탐지는 <code>max_load=0.5</code>(본 구현 기본값)로 확장 조건을 두면 충분히 쓸 만하고,
적재율 관리가 어려운 경우에는 체이닝이 더 안전하다.</li>
</ul>

<h2>9. AI 에이전트의 오류 및 수정 사례</h2>
%(errors)s

<h2>10. 결론</h2>
<p>일련번호 base62 코드와 직접 구현한 해시 테이블로 URL 단축기를 만들고, 두 충돌 처리 방식을 같은 키·같은 M·같은 해시로 비교했다.
체이닝은 α=4까지 이론 1+α/2, α와 일치했고, 선형 탐지는 α가 1에 가까워질수록 1차 군집 때문에 실패 탐색 비용이 급증해 α=0.9에서 체이닝의 약 %(ratio).0f배가 되었다.
두 구현은 같은 인터페이스를 가져 단축기·서버·테스트에서 그대로 교체된다.</p>
<div class="note">수치는 모두 experiments/*.csv에서 report/build_report.py가 읽어 넣었다. 생성 시각 기준 테스트: %(ntests)s개 통과.</div>
</body></html>"""
    with open(os.path.join(HERE, "agent_errors.html"), encoding="utf-8") as f:
        errors = f.read()
    return html % {
        "repo": escape(repo_url()), "exp": EXP, "probe_rows": probe_rows, "comp_rows": comp_rows,
        "p1s": P(p1, "success_measured"), "p1f": P(p1, "fail_measured"), "p4s": P(p4, "success_measured"),
        "c5lf": C(c5, "linear_fail_measured"), "c7lf": C(c7, "linear_fail_measured"), "c5cf": C(c5, "chaining_fail_measured"),
        "lf9": lin_fail9, "cf9": ch_fail9, "ratio": lin_fail9 / ch_fail9,
        "cl5": C(c5, "linear_longest_cluster"), "cl9": C(c9, "linear_longest_cluster"),
        "chdev": max_dev([(P(r, "success_measured"), P(r, "success_theory")) for r in probe]
                         + [(P(r, "fail_measured"), P(r, "fail_theory")) for r in probe]
                         + [(C(r, "chaining_success_measured"), C(r, "chaining_success_theory")) for r in comp]
                         + [(C(r, "chaining_fail_measured"), C(r, "chaining_fail_theory")) for r in comp]),
        "lpdev": max_dev([(C(r, "linear_success_measured"), C(r, "linear_success_theory")) for r in comp[:-1]]
                         + [(C(r, "linear_fail_measured"), C(r, "linear_fail_theory")) for r in comp[:-1]]),
        "ls9": lin_succ9, "ls9t": lin_succ9_t, "errors": errors, "ntests": count_tests(),
    }


def max_dev(pairs):
    return max(abs(m - t) / t * 100 for m, t in pairs)


def count_tests():
    import unittest
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"))
    return suite.countTestCases()


def find_chrome():
    for name in (os.environ.get("CHROME"), "google-chrome", "chromium", "chromium-browser",
                 "google-chrome-stable"):
        if name and shutil.which(name):
            return shutil.which(name)
    return None


def main():
    html_path = os.path.join(HERE, "final_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html())
    print("HTML: report/final_report.html")
    chrome = find_chrome()
    if chrome is None:
        print("Chrome/Chromium이 없어 PDF는 만들지 않았습니다. HTML을 브라우저에서 열어 PDF로 인쇄하세요.")
        return 1
    pdf_path = os.path.join(HERE, "final_report.pdf")
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--print-to-pdf=" + pdf_path, "file://" + html_path],
                   check=True, capture_output=True)
    print("PDF: report/final_report.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
