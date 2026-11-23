"""URL 단축 웹 서버 (SPEC.md 5절). 표준 모듈 http.server만 쓴다.

    python3 src/server.py --port 8000          (make serve)

경로
  GET  /                  URL 입력 폼
  POST /shorten           짧은 링크 결과 화면 (잘못된 URL이면 400)
  GET  /<code>            원본 URL로 302 (없으면 404)
  GET  /expand?code=...   원본 URL 조회 화면
  GET  /table             해시 테이블 시각화
"""
import argparse
import os
import sys
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base62  # noqa: E402
from shortener import MAX_URL_LENGTH, Shortener  # noqa: E402

MAX_BODY = 16 * 1024


def query_value(pairs, name):
    """parse_qsl 결과(list of tuple)에서 name의 첫 값을 찾는다. dict를 쓰지 않는다."""
    for k, v in pairs:
        if k == name:
            return v
    return None


class App:
    """서버가 들고 있는 상태. 단축기 하나(primary)."""

    def __init__(self, table="chaining"):
        self.table = table
        self.primary = Shortener(table=table)

    def shorten(self, url):
        return self.primary.shorten(url)

    def expand(self, code):
        return self.primary.expand(code)


# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#fcfcfb;--fg:#0b0b0b;--fg2:#52514e;--line:#d9d8d3;--card:#fff;
--accent:#2a78d6;--accent2:#eb6834;--ok:#1baf7a;--err:#c62828;--null:#8a8984}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:"Noto Sans KR","Noto Sans CJK KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
line-height:1.5;font-size:16px}
header{background:#13233a;color:#fff;padding:12px 16px;display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center}
header b{font-size:18px}
header a{color:#cfe1fa;text-decoration:none}
header a.on{color:#fff;font-weight:700;border-bottom:2px solid #fff}
main{max-width:1100px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}
input[type=text],input[type=url]{width:100%;font-size:16px;padding:12px;border:1px solid var(--line);border-radius:8px}
button{font-size:16px;padding:10px 18px;border:0;border-radius:8px;background:var(--accent);color:#fff;cursor:pointer}
button.secondary{background:#e9eef6;color:#13233a}
.row-form{display:flex;gap:8px;flex-wrap:wrap}.row-form input{flex:1 1 260px}
.error{color:var(--err);font-weight:700}
.short{font-size:22px;font-weight:700;word-break:break-all}
.url{word-break:break-all;font-family:ui-monospace,Consolas,monospace;font-size:14px}
code,.mono{font-family:ui-monospace,Consolas,"D2Coding",monospace}
.muted{color:var(--fg2);font-size:14px}
table.kv td{padding:2px 10px 2px 0;vertical-align:top}table.kv td:first-child{white-space:nowrap}
.stats{display:flex;flex-wrap:wrap;gap:8px}.stats span{background:#eef3fa;border-radius:6px;padding:4px 10px;font-size:14px}
.bucket{display:flex;align-items:flex-start;gap:6px;padding:6px 0;border-bottom:1px dashed var(--line);overflow-x:auto}
.idx{flex:0 0 54px;text-align:right;font-family:ui-monospace,monospace;font-weight:700;color:#13233a;
background:#eef3fa;border-radius:6px;padding:6px 8px}
.chain{display:flex;flex-wrap:wrap;align-items:flex-start;gap:4px}
.arrow{color:var(--fg2);padding:6px 2px;font-weight:700}
.null{color:var(--null);font-family:ui-monospace,monospace;padding:6px 4px;font-size:13px}
details.node{border:2px solid var(--accent);border-radius:8px;background:#f4f8fe;max-width:340px;min-width:150px}
details.node>summary{cursor:pointer;padding:4px 8px;list-style:none}
details.node>summary::-webkit-details-marker{display:none}
details.node .k{font-size:12px;word-break:break-all;font-family:ui-monospace,monospace;display:block}
details.node .c{font-size:13px}
details.node .c b{color:var(--accent2)}
.horner{padding:6px 8px;border-top:1px solid var(--line);font-size:12px;max-height:280px;overflow:auto;background:#fff}
.horner table{border-collapse:collapse;width:100%}
.horner td,.horner th{border-bottom:1px solid #eee;padding:1px 4px;text-align:right;font-family:ui-monospace,monospace}
.horner th{color:var(--fg2);font-weight:400}
.hide-empty .bucket.empty{display:none}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
@media (max-width:600px){main{padding:10px}.idx{flex-basis:44px;padding:6px 4px}details.node{max-width:260px}}
"""


def page(title, body, active=""):
    def nav(href, label, key):
        cls = ' class="on"' if key == active else ""
        return '<a href="%s"%s>%s</a>' % (href, cls, label)
    return ("<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body>"
            "<header><b>URL 단축기</b>%s%s</header><main>%s</main></body></html>"
            % (escape(title), CSS, nav("/", "줄이기", "home"),
               nav("/table", "해시 테이블 보기", "table"), body))


def form_html(value="", error=None):
    err = '<p class="error">%s</p>' % escape(error) if error else ""
    return ("<div class=\"card\"><h2>긴 URL 줄이기</h2>%s"
            "<form method=\"post\" action=\"/shorten\" class=\"row-form\">"
            "<input type=\"text\" name=\"url\" inputmode=\"url\" autocomplete=\"off\" "
            "placeholder=\"https://example.com/아주/긴/주소\" value=\"%s\" maxlength=\"%d\" required>"
            "<button type=\"submit\">줄이기</button></form>"
            "<p class=\"muted\">http:// 또는 https:// 로 시작하는 %d자 이하 주소. 같은 주소를 다시 넣으면 같은 코드를 돌려줍니다.</p>"
            "</div>"
            "<div class=\"card\"><h3>원본 URL 조회</h3>"
            "<form method=\"get\" action=\"/expand\" class=\"row-form\">"
            "<input type=\"text\" name=\"code\" placeholder=\"짧은 코드 (예: 1, a, Z, 10)\" autocomplete=\"off\">"
            "<button type=\"submit\" class=\"secondary\">조회</button></form></div>"
            % (err, escape(value), MAX_URL_LENGTH + 100, MAX_URL_LENGTH))


def render_index(value="", error=None):
    return page("URL 단축기", form_html(value, error), "home")


def render_result(base, url, code):
    link = "%s/%s" % (base, code)
    body = ("<div class=\"card\"><h2>짧은 링크</h2>"
            "<p class=\"short\"><a href=\"%s\">%s</a></p>"
            "<table class=\"kv\"><tr><td>원본 URL</td><td class=\"url\">%s</td></tr>"
            "<tr><td>코드</td><td><code>%s</code> (일련번호 %d의 base62)</td></tr></table>"
            "<p><a href=\"/table\">해시 테이블에서 이 노드 보기 →</a></p></div>"
            % (escape(link, quote=True), escape(link), escape(url), escape(code), base62.decode(code)))
    return page("짧은 링크", body + form_html(), "home")


def render_expand(base, code, url):
    link = "%s/%s" % (base, code)
    body = ("<div class=\"card\"><h2>원본 URL 조회</h2><table class=\"kv\">"
            "<tr><td>코드</td><td><code>%s</code></td></tr>"
            "<tr><td>짧은 링크</td><td class=\"url\">%s</td></tr>"
            "<tr><td>원본 URL</td><td class=\"url\"><a href=\"%s\">%s</a></td></tr></table></div>"
            % (escape(code), escape(link), escape(url, quote=True), escape(url)))
    return page("원본 URL 조회", body, "home")


def render_not_found(what):
    body = ("<div class=\"card\"><h2>찾을 수 없습니다</h2><p class=\"error\">%s</p>"
            "<p><a href=\"/\">처음으로</a></p></div>" % escape(what))
    return page("404", body, "")


def horner_html(table, key):
    rows = []
    prev = 0
    m = table.capacity
    for i, (c, o, h) in enumerate(table.horner_steps(key)):
        rows.append("<tr><td>%d</td><td>%s</td><td>%d</td><td>(31×%d + %d) mod %d</td><td><b>%d</b></td></tr>"
                    % (i, escape(repr(c)[1:-1]), o, prev, o, m, h))
        prev = h
    return ("<div class=\"horner\"><div>h = (31·h + ord(c)) mod M, M = %d, 처음 h = 0</div>"
            "<table><tr><th>i</th><th>c</th><th>ord</th><th>계산</th><th>h</th></tr>%s</table>"
            "<div>최종 칸 번호 = <b>%d</b></div></div>" % (m, "".join(rows), prev))


def render_table_chaining(base, table, which, title):
    st = table.stats()
    out = ["<div class=\"card\"><h2>%s</h2>" % escape(title),
           "<div class=\"stats\"><span>칸 수 M = %d</span><span>키 n = %d</span>"
           "<span>적재율 α = %.3f</span><span>사용 중인 칸 %d</span><span>최장 체인 %d</span>"
           "<span>max_load = %s</span></div>"
           % (st.capacity, st.size, st.load_factor, st.used_slots, st.longest_chain,
              table.max_load),
           "<p class=\"muted\">칸마다 연결 리스트를 화살표로 잇습니다. 노드를 누르면 호너 해시 계산 과정이 펼쳐집니다. "
           "새 키는 리스트 끝에 붙고, 적재율이 max_load를 넘으면 칸 수를 2M+1 이상의 소수로 늘려 다시 넣습니다.</p>",
           "<div class=\"toolbar\"><label><input type=\"checkbox\" "
           "onchange=\"document.getElementById('buckets').classList.toggle('hide-empty',this.checked)\"> "
           "빈 칸 숨기기</label></div><div id=\"buckets\">"]
    for i, chain in enumerate(table.snapshot()):
        parts = []
        for key, value in chain:
            if which == "url":
                url, code = key, value
            else:
                code, url = key, value
            link = "%s/%s" % (base, code)
            parts.append(
                "<details class=\"node\"><summary><span class=\"k\">%s</span>"
                "<span class=\"c\">코드 <b>%s</b> · <a href=\"%s\">%s</a></span></summary>%s</details>"
                % (escape(key), escape(code), escape(link, quote=True), escape(link),
                   horner_html(table, key)))
            parts.append("<span class=\"arrow\">→</span>")
        parts.append("<span class=\"null\">NULL</span>")
        out.append("<div class=\"bucket%s\"><div class=\"idx\">[%d]</div><div class=\"chain\">%s</div></div>"
                   % ("" if chain else " empty", i, "".join(parts)))
    out.append("</div></div>")
    return "".join(out)


def render_table(app, base, which):
    s = app.primary
    table = s.url_table if which == "url" else s.code_table
    name = "URL → 코드" if which == "url" else "코드 → URL"
    tabs = ("<div class=\"toolbar\"><span>테이블:</span>"
            "<a href=\"/table?which=url\">URL → 코드</a> · <a href=\"/table?which=code\">코드 → URL</a></div>")
    body = tabs + render_table_chaining(base, table, which, "개별 체이닝 · %s 테이블" % name)
    return page("해시 테이블", body, "table")


# ---------------------------------------------------------------- HTTP

def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "URLShortener/1.0"

        def log_message(self, fmt, *args):
            if not getattr(self.server, "quiet", False):
                super().log_message(fmt, *args)

        # 짧은 링크 주소: X-Forwarded-* 가 있으면 그것을 먼저 쓴다 (Codespaces 공개 포트)
        def base_url(self):
            host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "localhost:8000"
            proto = self.headers.get("X-Forwarded-Proto") or "http"
            host = host.split(",")[0].strip()
            proto = proto.split(",")[0].strip()
            return "%s://%s" % (proto, host)

        def send_html(self, status, html):
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parts = urlsplit(self.path)
            path = parts.path
            query = parse_qsl(parts.query)
            if path == "/":
                return self.send_html(200, render_index())
            if path == "/table":
                which = query_value(query, "which") or "url"
                if which not in ("url", "code"):
                    which = "url"
                return self.send_html(200, render_table(app, self.base_url(), which))
            if path == "/expand":
                code = (query_value(query, "code") or "").strip()
                url = app.expand(code)
                if url is None:
                    return self.send_html(404, render_not_found("없는 코드입니다: %s" % code))
                return self.send_html(200, render_expand(self.base_url(), code, url))
            code = unquote(path[1:])
            if "/" not in code:
                url = app.expand(code)
                if url is not None:
                    self.send_response(302)
                    self.send_header("Location", url)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            return self.send_html(404, render_not_found("없는 짧은 링크입니다: %s" % path))

        def do_POST(self):
            path = urlsplit(self.path).path
            if path != "/shorten":
                return self.method_not_allowed()
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self.send_html(413, render_index(error="요청이 너무 큽니다"))
            raw = self.rfile.read(length).decode("utf-8", "replace")
            url = query_value(parse_qsl(raw, keep_blank_values=True), "url")
            if url is None:
                return self.send_html(400, render_index(error="url 값이 없습니다"))
            try:
                code = app.shorten(url)
            except (ValueError, TypeError) as e:
                return self.send_html(400, render_index(url, str(e)))
            return self.send_html(200, render_result(self.base_url(), url.strip(), code))

        def method_not_allowed(self):
            self.send_response(405)
            self.send_header("Allow", "GET, POST")
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_PUT = do_DELETE = do_PATCH = method_not_allowed

    return Handler


def make_server(app, host="0.0.0.0", port=8000, quiet=True):
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    httpd.quiet = quiet
    return httpd


def main(argv=None):
    p = argparse.ArgumentParser(description="URL 단축 웹 서버")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--table", choices=("chaining", "linear"), default="chaining")
    args = p.parse_args(argv)
    app = App(table=args.table)
    httpd = make_server(app, args.host, args.port, quiet=False)
    print("URL 단축기 (%s): http://localhost:%d  (끝내려면 Ctrl+C)" % (args.table, args.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 끕니다.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
