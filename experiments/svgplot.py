"""표준 모듈만으로 꺾은선 그래프 SVG를 쓴다.

실험값 = 실선 + 동그라미 표식, 이론값 = 같은 색 점선. 색은 계열(구현/탐색 종류)을 나타내고,
실험/이론 구분은 선 모양으로 한다. 각 점에는 <title>로 값이 붙어 마우스를 올리면 보인다.
"""
from xml.sax.saxutils import escape

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e4e3df"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#6250d6")
FONT = "Noto Sans CJK KR, Noto Sans KR, Malgun Gothic, Apple SD Gothic Neo, sans-serif"


def _nice_ticks(lo, hi, n=5):
    span = hi - lo
    for step in (0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100):
        if span / step <= n:
            break
    t = (lo // step) * step
    ticks = []
    while t <= hi + 1e-9:
        if t >= lo - 1e-9:
            ticks.append(round(t, 6))
        t += step
    return ticks


def _fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def panel(x0, y0, w, h, title, xlabel, ylabel, series, xs_ticks=None, ymax=None):
    """series: [(이름, 색, xs, ys, 'measured'|'theory')]. SVG 조각 문자열을 돌려준다."""
    ml, mr, mt, mb = 58, 16, 34, 46
    pw, ph = w - ml - mr, h - mt - mb
    allx = [x for s in series for x in s[2]]
    ally = [y for s in series for y in s[3]]
    xmin, xmax = min(allx), max(allx)
    ymin = 0.0
    ymax = ymax if ymax is not None else max(ally) * 1.08
    sx = lambda x: x0 + ml + (x - xmin) / (xmax - xmin) * pw  # noqa: E731
    sy = lambda y: y0 + mt + ph - (min(y, ymax) - ymin) / (ymax - ymin) * ph  # noqa: E731
    out = []
    out.append('<text x="%.1f" y="%.1f" font-size="14" font-weight="700" fill="%s">%s</text>'
               % (x0 + ml, y0 + 20, TEXT, escape(title)))
    for t in _nice_ticks(ymin, ymax):
        y = sy(t)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
                   % (x0 + ml, y, x0 + ml + pw, y, GRID))
        out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="end">%s</text>'
                   % (x0 + ml - 6, y + 4, TEXT2, _fmt(t)))
    for t in (xs_ticks or _nice_ticks(xmin, xmax)):
        if t < xmin - 1e-9 or t > xmax + 1e-9:
            continue  # 그래프 범위 밖 눈금은 그리지 않는다
        x = sx(t)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>'
                   % (x, y0 + mt + ph, x, y0 + mt + ph + 4, TEXT2))
        out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="middle">%s</text>'
                   % (x, y0 + mt + ph + 17, TEXT2, _fmt(t)))
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
               % (x0 + ml, y0 + mt + ph, x0 + ml + pw, y0 + mt + ph, TEXT2))
    out.append('<text x="%.1f" y="%.1f" font-size="12" fill="%s" text-anchor="middle">%s</text>'
               % (x0 + ml + pw / 2, y0 + h - 8, TEXT, escape(xlabel)))
    out.append('<text transform="translate(%.1f %.1f) rotate(-90)" font-size="12" fill="%s" '
               'text-anchor="middle">%s</text>' % (x0 + 15, y0 + mt + ph / 2, TEXT, escape(ylabel)))
    for name, color, xs, ys, kind in series:
        pts = " ".join("%.1f,%.1f" % (sx(x), sy(y)) for x, y in zip(xs, ys) if y <= ymax * 1.0001)
        dash = ' stroke-dasharray="6 4"' if kind == "theory" else ""
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"%s '
                   'stroke-linejoin="round" stroke-linecap="round"/>' % (pts, color, dash))
        if kind == "measured":
            for x, y in zip(xs, ys):
                if y > ymax:
                    continue
                out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="%s" stroke-width="2">'
                           '<title>%s · α=%s · %.3f</title></circle>'
                           % (sx(x), sy(y), color, SURFACE, escape(name), _fmt(x), y))
    return "\n".join(out)


def legend(x, y, entries, width):
    """entries: [(이름, 색, 'measured'|'theory')] 를 가로로 늘어놓는다(넘치면 줄바꿈)."""
    out = []
    cx, cy = x, y
    for name, color, kind in entries:
        wlen = 34 + 7.2 * len(name) + 22
        if cx + wlen > x + width:
            cx, cy = x, cy + 20
        dash = ' stroke-dasharray="6 4"' if kind == "theory" else ""
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"%s/>'
                   % (cx, cy, cx + 26, cy, color, dash))
        if kind == "measured":
            out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="%s" stroke-width="2"/>'
                       % (cx + 13, cy, color, SURFACE))
        out.append('<text x="%.1f" y="%.1f" font-size="12" fill="%s">%s</text>'
                   % (cx + 32, cy + 4, TEXT, escape(name)))
        cx += wlen
    return "\n".join(out), cy


def document(width, height, title, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
            'font-family="%s">\n<title>%s</title>\n'
            '<rect width="100%%" height="100%%" fill="%s"/>\n%s\n</svg>\n'
            % (width, height, width, height, FONT, escape(title), SURFACE, body))
