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
@page{size:A4;margin:14mm 16mm 13mm}
body{font-family:"Noto Serif CJK KR","Noto Serif KR",serif;font-size:9.6pt;line-height:1.46;color:#222;margin:0;word-break:keep-all}
.repo{font-family:"Noto Sans CJK KR",sans-serif;font-size:8.8pt;color:#2c3e57;margin-bottom:8px}
.repo span{color:#555}
h1{font-family:"Noto Sans CJK KR",sans-serif;font-weight:500;font-size:14pt;color:#1f2d40;margin:0 0 2px;letter-spacing:-0.2px}
.sub{font-family:"Noto Sans CJK KR",sans-serif;font-size:8.6pt;color:#666;padding-bottom:6px;border-bottom:0.8px solid #2c3e57;margin-bottom:4px}
h2{font-family:"Noto Sans CJK KR",sans-serif;font-weight:500;font-size:10.2pt;color:#1f2d40;margin:9px 0 2px}
p{margin:0 0 4px;text-align:justify}
code{font-family:"Noto Sans Mono CJK KR",monospace;font-size:8.4pt;color:#333}
table{border-collapse:collapse;width:100%%;font-family:"Noto Sans CJK KR",sans-serif;font-size:8pt;margin:4px 0 2px;border-top:0.9px solid #333;border-bottom:0.9px solid #333}
th{font-weight:500;border-bottom:0.6px solid #888;padding:2px 5px;text-align:center;color:#333}
td{padding:1.2px 5px;text-align:right}td:first-child{text-align:center}
.t{color:#8a8a8a}
.cap{font-family:"Noto Sans CJK KR",sans-serif;font-size:7.8pt;color:#555;text-align:center;margin:1px 0 4px}
img{display:block;margin:2px auto 0}
.two{display:flex;gap:14px}.two>div{flex:1}
.eq{text-align:center;margin:2px 0 4px;font-size:9.2pt}
</style></head><body>
<div class="repo"><span>저장소</span>&nbsp; %(repo)s</div>
<h1>해시 테이블 기반 URL 단축기: 개별 체이닝과 선형 탐지의 탐색 비용 비교</h1>
<div class="sub">2026-2 고급알고리즘(SIT2001-01) 과제 2</div>

<h2>1. 개요</h2>
<p>긴 URL을 짧은 코드로 바꾸고, 짧은 링크로 접속하면 원래 주소로 보내 주는 서비스를 만들었다. 저장에는 Python의 <code>dict</code>, <code>set</code>, 내장 <code>hash()</code>를 쓰지 않고 직접 구현한 해시 테이블을 사용했으며,
같은 해시 함수를 쓰는 개별 체이닝과 선형 탐지 두 방식을 구현해 적재율에 따른 탐색 비용을 이론값과 비교하였다.</p>

<h2>2. 구현 방법</h2>
<p>짧은 코드는 1부터 증가하는 일련번호를 base62(<code>0-9a-zA-Z</code>)로 변환해 만든다. URL의 해시값을 코드로 쓰지 않으므로 서로 다른 URL이 같은 코드를 받는 일이 없고,
이미 등록된 URL은 기존 코드를 그대로 돌려준다. 단축기는 URL→코드, 코드→URL 두 개의 해시 테이블을 가지며, 생성 시 <code>table="chaining"</code> 또는 <code>"linear"</code>로 자료구조를 고를 수 있다.
두 테이블의 인터페이스가 같아 단축기와 서버 코드는 그대로 쓸 수 있다. 해시 함수는 두 방식 모두 호너 방법을 쓴다.</p>
<div class="eq">h ← (31·h + ord(c)) mod M &nbsp;(문자열의 각 문자 c에 대해, 초기값 h = 0)</div>
<p>웹 서버는 표준 라이브러리 <code>http.server</code>만으로 작성했다. 메인 페이지에서 URL을 줄이고, 짧은 링크는 302 응답으로 원래 주소에 연결하며, 없는 코드에는 404를 돌려준다.
<code>/table</code> 페이지에서는 두 테이블의 내부 상태와 호너 해시 계산 과정, 탐색 경로를 볼 수 있다. 프록시 환경(Codespaces)에서는 <code>X-Forwarded-Host</code> 헤더로 짧은 링크 주소를 만든다.
테스트는 unittest %(ntests)s개이며, 해시 테이블 공통 테스트를 두 구현이 함께 통과하도록 구성했다.</p>

<div class="two"><div>
<h2>3. 개별 체이닝</h2>
<p>각 칸은 단일 연결 리스트의 머리를 가리키고, 충돌한 키는 해당 리스트 끝에 붙는다. 탐색 비용은 비교한 노드 수로 정의했다. 성공 탐색은 키의 리스트 내 위치, 실패 탐색은 리스트 길이가 비용이며 빈 칸이면 0이다.
이론적으로 성공 탐색은 <span style="white-space:nowrap">1 + α/2,</span> 실패 탐색은 α에 가깝다.</p>
</div><div>
<h2>4. 선형 탐지</h2>
<p>각 칸은 빈 칸, 삭제 표시(tombstone), (키, 값) 중 하나이다. 충돌이 나면 <span style="white-space:nowrap">(i + 1) mod M</span>으로 다음 칸을 보며, 마지막 칸 다음은 0번 칸이다. 삭제는 탐색 경로가 끊기지 않도록 삭제 표시로 처리하고, 테이블이 가득 차면 예외를 낸다.
비용은 들여다본 칸 수(실패 시 마지막 빈 칸 포함)이고, 이론값은 성공 <span style="white-space:nowrap">(1 + 1/(1−α))/2</span>, 실패 <span style="white-space:nowrap">(1 + 1/(1−α)²)/2</span>이다.</p>
</div></div>

<h2>5. 실험 조건</h2>
<p>고정된 시드(20261120)로 서로 다른 무작위 URL을 만들고, 칸 수를 M = 4093으로 고정해 테이블 확장을 끈 상태에서 측정했다. 각 적재율 α마다 목록 앞의 <span style="white-space:nowrap">n = round(α·M)</span>개를 새 테이블에 넣은 뒤,
넣은 키 전부에 대한 평균을 성공 탐색 비용으로, 넣지 않은 URL 5000개에 대한 평균을 실패 탐색 비용으로 삼았다. 실험 A는 개별 체이닝만으로 α = 0.25~4를 0.25 간격으로,
실험 B는 두 방식에 같은 키를 같은 순서로 넣어 α = 0.1~0.9를 0.1 간격으로 측정했다. 다시 실행해도 같은 결과가 나온다.</p>

<h2>6. 실험 결과</h2>
<div class="two"><div>
<table><tr><th>α</th><th>n</th><th>성공(실험)</th><th>성공(이론)</th><th>실패(실험)</th><th>실패(이론)</th></tr>%(probe_rows)s</table>
<div class="cap">표 1. 실험 A — 개별 체이닝의 평균 비교 노드 수 (일부)</div>
</div><div>
<img src="file://%(exp)s/results.svg" style="width:96%%">
<div class="cap">그림 1. 실험 A의 실험값과 이론값</div>
</div></div>
<table><tr><th>α</th><th>n</th><th>체이닝 성공</th><th>체이닝 실패</th><th>선형 탐지 성공</th><th>선형 탐지 실패</th><th>최장 군집</th></tr>%(comp_rows)s</table>
<div class="cap">표 2. 실험 B — 같은 키, 같은 M에서 두 방식의 평균 탐색 비용 (괄호 안은 이론값)</div>
<img src="file://%(exp)s/comparison_results.svg" style="width:74%%">
<div class="cap">그림 2. 실험 B — 실선은 실험값, 점선은 이론값 (왼쪽: 성공 탐색, 오른쪽: 실패 탐색)</div>

<h2>7. 결과 분석</h2>
<p><b>적재율에 따른 변화.</b> 개별 체이닝의 비용은 α에 비례해 완만하게 늘었다. α = 1에서 성공 %(p1s).2f, 실패 %(p1f).2f였고, α = 4에서도 성공 탐색은 %(p4s).2f에 그쳤다.
반면 선형 탐지는 α = 0.5에서 실패 탐색이 %(c5lf).2f칸으로 체이닝(%(c5cf).2f)과 이미 차이가 났고, α = 0.7에서 %(c7lf).2f칸, α = 0.9에서는 %(lf9).1f칸까지 늘어 같은 조건의 체이닝(%(cf9).2f)보다 약 %(ratio).0f배 컸다.</p>
<p><b>α가 1에 가까울 때 선형 탐지가 급격히 나빠지는 이유.</b> 선형 탐지에서는 충돌한 키가 바로 옆 칸을 차지하므로 채워진 칸이 연속된 덩어리(군집)를 이룬다. 군집 안 어느 칸에 해시되든 키는 군집 끝까지 밀려 들어가 군집을 더 키우고,
군집이 길수록 새 키가 그 군집에 걸릴 확률도 커진다(1차 군집). 실제로 최장 군집은 α = 0.5에서 %(cl5)d칸이었으나 α = 0.9에서 %(cl9)d칸이 되었다.
실패 탐색은 빈 칸을 만나야 끝나는데, α가 1에 가까워지면 빈 칸이 드물어져 비용이 1/(1−α)²의 속도로 커진다. 개별 체이닝은 충돌이 그 칸의 리스트 안에서만 쌓이고 이웃 칸으로 번지지 않으므로 이런 급증이 나타나지 않는다.</p>
<p><b>이론값과의 차이.</b> 개별 체이닝은 두 실험 전체에서 이론값과의 상대 오차가 %(chdev).1f%% 이내였다. 선형 탐지도 α ≤ 0.8에서는 최대 %(lpdev).1f%% 차이로 잘 맞았지만, α = 0.9의 성공 탐색은 %(ls9).2f로 이론값 %(ls9t).2f보다 컸다.
이론식은 해시값이 균일하고 M이 충분히 크다는 가정 아래의 근사식인데, α가 클수록 평균이 소수의 긴 군집에 크게 좌우되어 한 번의 키 집합으로 얻은 값의 변동이 커진다.
모든 URL이 <code>https://</code>로 시작해 호너 해시의 분포가 완전히 균일하지 않을 가능성도 있으나, 이번 실험만으로 두 원인을 구분하지는 못했다.</p>
<p><b>서비스 관점의 비교.</b> 선형 탐지는 포인터 없이 배열 하나만 쓰므로 메모리가 연속적이고 캐시에 유리하지만, 적재율을 0.5~0.7 이하로 유지해야 하고 삭제 표시를 관리해야 한다.
개별 체이닝은 α가 1을 넘어도 성능이 완만하게 떨어지고 삭제가 단순한 대신 노드마다 포인터 공간이 든다. 조회가 많고 삭제가 드문 URL 단축기라면 선형 탐지도 최대 적재율 0.5에서 확장하도록 두면 충분히 쓸 수 있고,
적재율을 관리하기 어려운 상황이라면 개별 체이닝이 더 안정적이다.</p>

<h2>8. 에이전트가 틀린 부분과 수정 과정</h2>
%(errors)s

<h2>9. 결론</h2>
<p>개별 체이닝은 α = 4까지 이론값 1 + α/2와 α를 잘 따랐고, 선형 탐지는 α가 1에 가까워질수록 1차 군집 때문에 실패 탐색 비용이 급격히 커져 α = 0.9에서 체이닝의 약 %(ratio).0f배가 되었다.</p>
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
