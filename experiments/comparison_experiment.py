"""과제 실험: 개별 체이닝 vs 선형 탐지 (이슈 #8).

같은 조건 (SPEC.md 7절)
  - 칸 수 M = 4093 고정 (두 테이블 모두 max_load=None)
  - 같은 URL 목록(시드 고정), 같은 호너 해시
  - 적재율 α = 0.1, 0.2, ..., 0.9 : 목록 앞에서 n = round(α·M)개를 넣는다
  - 성공 탐색: 넣은 키 전부 find() 평균 / 실패 탐색: 넣지 않은 URL 5000개 find() 평균
  - 체이닝은 비교한 노드 수, 선형 탐지는 들여다본 칸 수로 센다
이론값
  체이닝  성공 1 + α/2,            실패 α
  선형    성공 (1 + 1/(1-α))/2,    실패 (1 + 1/(1-α)^2)/2
출력: experiments/comparison_results.csv, experiments/comparison_results.svg
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import svgplot  # noqa: E402
from hash_table import HashTable  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402
from urlgen import unique_urls  # noqa: E402

M = 4093
ALPHAS = [i / 10 for i in range(1, 10)]
MISS_QUERIES = 5000


def theory(alpha):
    return (1 + alpha / 2, alpha,
            (1 + 1 / (1 - alpha)) / 2, (1 + 1 / (1 - alpha) ** 2) / 2)


def measure(cls, keys, misses):
    t = cls(capacity=M, max_load=None)
    for i, k in enumerate(keys):
        t.put(k, i)
    assert t.capacity == M and len(t) == len(keys)
    hit = 0
    for k in keys:
        v, c = t.find(k)
        assert v is not None
        hit += c
    miss = 0
    for k in misses:
        v, c = t.find(k)
        assert v is None
        miss += c
    return hit / len(keys), miss / len(misses), t.stats().longest_run


def run():
    n_max = round(ALPHAS[-1] * M)
    pool = unique_urls(n_max + MISS_QUERIES)
    inserted, misses = pool[:n_max], pool[n_max:]
    rows = []
    print("M=%d, 실패 탐색 질의 %d개" % (M, MISS_QUERIES))
    print("%4s %5s | %-23s | %-23s | %-23s | %-23s" % (
        "α", "n", "체이닝 성공 실험/이론", "체이닝 실패 실험/이론", "선형 성공 실험/이론", "선형 실패 실험/이론"))
    for alpha in ALPHAS:
        n = round(alpha * M)
        keys = inserted[:n]
        lf = n / M
        ch_s, ch_f, ch_long = measure(HashTable, keys, misses)
        lp_s, lp_f, lp_long = measure(LinearProbingTable, keys, misses)
        th = theory(lf)
        rows.append((alpha, n, lf, ch_s, th[0], ch_f, th[1], lp_s, th[2], lp_f, th[3], ch_long, lp_long))
        print("%4.1f %5d | %9.4f / %9.4f | %9.4f / %9.4f | %9.4f / %9.4f | %9.4f / %9.4f"
              % (alpha, n, ch_s, th[0], ch_f, th[1], lp_s, th[2], lp_f, th[3]))

    with open(os.path.join(HERE, "comparison_results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["load_factor_target", "n", "load_factor",
                    "chaining_success_measured", "chaining_success_theory",
                    "chaining_fail_measured", "chaining_fail_theory",
                    "linear_success_measured", "linear_success_theory",
                    "linear_fail_measured", "linear_fail_theory",
                    "chaining_longest_chain", "linear_longest_cluster"])
        for r in rows:
            w.writerow(["%.1f" % r[0], r[1]] + ["%.6f" % v for v in r[2:11]] + [r[11], r[12]])

    xs = [r[2] for r in rows]
    C, L = svgplot.SERIES[0], svgplot.SERIES[1]

    def series(i_ch, i_lp):
        return [
            ("체이닝 실험값", C, xs, [r[i_ch] for r in rows], "measured"),
            ("체이닝 이론값", C, xs, [r[i_ch + 1] for r in rows], "theory"),
            ("선형 탐지 실험값", L, xs, [r[i_lp] for r in rows], "measured"),
            ("선형 탐지 이론값", L, xs, [r[i_lp + 1] for r in rows], "theory"),
        ]

    W, H, PH = 960, 450, 400
    ticks = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    s_succ = series(3, 7)
    s_fail = series(5, 9)
    body = svgplot.panel(0, 0, W / 2, PH, "성공 탐색: 체이닝 vs 선형 탐지 (M = %d)" % M, "적재율 α", "평균 탐색 비용 (노드 / 칸)",
                         s_succ, xs_ticks=ticks)
    body += "\n" + svgplot.panel(W / 2, 0, W / 2, PH, "실패 탐색: 체이닝 vs 선형 탐지 (M = %d)" % M, "적재율 α", "평균 탐색 비용 (노드 / 칸)",
                                 s_fail, xs_ticks=ticks)
    leg, _ = svgplot.legend(66, PH + 26, [(s[0], s[1], s[4]) for s in s_succ], W - 80)
    body += "\n" + leg
    with open(os.path.join(HERE, "comparison_results.svg"), "w", encoding="utf-8") as f:
        f.write(svgplot.document(W, H, "개별 체이닝 vs 선형 탐지 (M = %d)" % M, body))
    print("저장: experiments/comparison_results.csv, experiments/comparison_results.svg")


if __name__ == "__main__":
    run()
