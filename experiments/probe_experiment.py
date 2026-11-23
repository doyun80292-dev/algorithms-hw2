"""6단계 실험: 개별 체이닝의 적재율에 따른 평균 비교 노드 수 (이슈 #6).

조건 (SPEC.md 7절)
  - HashTable(capacity=4093, max_load=None)  : 크기 고정
  - 적재율 α = 0.25, 0.50, ..., 4.00
  - 무작위 URL(시드 고정)을 n = round(α·M)개 넣는다
  - 성공 탐색: 넣은 키 전부를 find()해 비교 노드 수 평균
  - 실패 탐색: 넣지 않은 URL 5000개를 find()해 비교 노드 수 평균 (빈 칸은 0)
  - 이론값: 성공 ≈ 1 + α/2, 실패 ≈ α
출력: experiments/results.csv, experiments/results.svg
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import svgplot  # noqa: E402
from hash_table import HashTable  # noqa: E402
from urlgen import unique_urls  # noqa: E402

M = 4093
ALPHAS = [i * 0.25 for i in range(1, 17)]
MISS_QUERIES = 5000


def measure(alpha, inserted_pool, miss_pool):
    n = round(alpha * M)
    t = HashTable(capacity=M, max_load=None)
    keys = inserted_pool[:n]
    for i, k in enumerate(keys):
        t.put(k, i)
    assert t.capacity == M and len(t) == n
    hit = 0
    for k in keys:
        value, cmp = t.find(k)
        assert value is not None
        hit += cmp
    miss = 0
    for k in miss_pool:
        value, cmp = t.find(k)
        assert value is None
        miss += cmp
    return n, t.load_factor(), hit / n, miss / len(miss_pool), t.stats().longest_chain


def run():
    n_max = round(ALPHAS[-1] * M)
    pool = unique_urls(n_max + MISS_QUERIES)
    inserted_pool, miss_pool = pool[:n_max], pool[n_max:]
    rows = []
    print("M=%d, 실패 탐색 질의 %d개" % (M, MISS_QUERIES))
    print("%6s %6s | %9s %9s | %9s %9s | %s" % ("α", "n", "성공(실험)", "성공(이론)",
                                              "실패(실험)", "실패(이론)", "최장 체인"))
    for alpha in ALPHAS:
        n, lf, hit, miss, longest = measure(alpha, inserted_pool, miss_pool)
        row = (alpha, n, lf, hit, 1 + lf / 2, miss, lf, longest)
        rows.append(row)
        print("%6.2f %6d | %9.4f %9.4f | %9.4f %9.4f | %d" % (alpha, n, hit, 1 + lf / 2, miss, lf, longest))

    with open(os.path.join(HERE, "results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["load_factor_target", "n", "load_factor", "success_measured", "success_theory",
                    "fail_measured", "fail_theory", "longest_chain"])
        for r in rows:
            w.writerow([("%.2f" % r[0]), r[1], "%.6f" % r[2], "%.6f" % r[3], "%.6f" % r[4],
                        "%.6f" % r[5], "%.6f" % r[6], r[7]])

    xs = [r[2] for r in rows]
    series = [
        ("성공 탐색 실험값", svgplot.SERIES[0], xs, [r[3] for r in rows], "measured"),
        ("성공 탐색 이론 1+α/2", svgplot.SERIES[0], xs, [r[4] for r in rows], "theory"),
        ("실패 탐색 실험값", svgplot.SERIES[1], xs, [r[5] for r in rows], "measured"),
        ("실패 탐색 이론 α", svgplot.SERIES[1], xs, [r[6] for r in rows], "theory"),
    ]
    W, H = 720, 440
    leg, _ = svgplot.legend(66, 400, [(s[0], s[1], s[4]) for s in series], W - 80)
    body = svgplot.panel(0, 0, W, 390,
                         "개별 체이닝: 적재율에 따른 평균 비교 노드 수 (M = %d)" % M,
                         "적재율 α = n / M", "평균 비교 노드 수", series,
                         xs_ticks=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]) + "\n" + leg
    with open(os.path.join(HERE, "results.svg"), "w", encoding="utf-8") as f:
        f.write(svgplot.document(W, H, "개별 체이닝 적재율 실험", body))
    print("저장: experiments/results.csv, experiments/results.svg")


if __name__ == "__main__":
    run()
