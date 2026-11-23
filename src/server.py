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
    """서버가 들고 있는 상태.

    두 단축기(체이닝, 선형 탐지)에 같은 URL을 같은 순서로 넣는다. 일련번호가 같으므로 코드도 같다.
    리다이렉트·조회는 --table로 고른 primary가 맡고, /table은 두 쪽을 모두 보여 줄 수 있다.
    """

    def __init__(self, table="chaining"):
        if table not in ("chaining", "linear"):
            raise ValueError("table은 chaining 또는 linear")
        self.table = table
        self.chaining = Shortener(table="chaining")
        self.linear = Shortener(table="linear")
        self.primary = self.chaining if table == "chaining" else self.linear

    def shortener(self, impl):
        return self.linear if impl == "linear" else self.chaining

    def shorten(self, url):
        code = self.primary.shorten(url)        # 잘못된 URL이면 여기서 예외 → 둘 다 바뀌지 않음
        other = self.linear if self.primary is self.chaining else self.chaining
        other_code = other.shorten(url)
        if other_code != code:                  # 같은 입력·같은 순서이면 일어나지 않아야 한다
            raise RuntimeError("두 단축기의 코드가 어긋났습니다: %s != %s" % (code, other_code))
        return code

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
details.node .c{font-size:13px;display:block}
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
        out.append("<div class=\"bucket%s\" id=\"b%d\"><div class=\"idx\">[%d]</div><div class=\"chain\">%s</div></div>"
                   % ("" if chain else " empty", i, i, "".join(parts)))
    out.append("</div></div>")
    return "".join(out)


def render_table_linear(base, table, which, title):
    from linear_probing import TOMBSTONE
    st = table.stats()
    m = table.capacity
    out = ["<div class=\"card\"><h2>%s</h2>" % escape(title),
           "<div class=\"stats\"><span>칸 수 M = %d</span><span>키 n = %d</span>"
           "<span>적재율 α = %.3f</span><span>가장 긴 군집 %d칸</span><span>max_load = %s</span></div>"
           % (m, st.size, st.load_factor, st.longest_cluster, table.max_load),
           "<p class=\"muted\">칸마다 키 하나만 들어갑니다. 처음 계산한 칸 h가 차 있으면 "
           "<code>index = (index + 1) mod M</code>으로 다음 칸을 봅니다(끝 칸 다음은 0번). "
           "<b>탐색 n칸</b>은 이 키를 찾을 때 들여다본 칸 수이고, 경로는 그 칸 번호들입니다. "
           "지운 칸은 TOMBSTONE으로 남겨 탐색 경로가 끊기지 않게 합니다. 칸을 누르면 호너 계산이 펼쳐집니다.</p>",
           "<div class=\"toolbar\"><label><input type=\"checkbox\" "
           "onchange=\"document.getElementById('buckets').classList.toggle('hide-empty',this.checked)\"> "
           "빈 칸 숨기기</label></div><div id=\"buckets\">"]
    for i, slot in enumerate(table.snapshot()):
        if slot is None:
            out.append("<div class=\"bucket empty\" id=\"b%d\"><div class=\"idx\">[%d]</div>"
                       "<span class=\"null\">EMPTY</span></div>" % (i, i))
            continue
        if slot is TOMBSTONE:
            out.append("<div class=\"bucket\" id=\"b%d\"><div class=\"idx\">[%d]</div>"
                       "<span class=\"null\">TOMBSTONE (지운 자리)</span></div>" % (i, i))
            continue
        key, value = slot
        url, code = (key, value) if which == "url" else (value, key)
        link = "%s/%s" % (base, code)
        home = table.index_of(key)
        path = table.probe_path(key)
        moved = len(path) - 1
        badge = ("<span class=\"badge home\">처음 칸 그대로</span>" if moved == 0 else
                 "<span class=\"badge moved\">충돌 → %d칸 밀림</span>" % moved)
        out.append(
            "<div class=\"bucket\" id=\"b%d\"><div class=\"idx\">[%d]</div>"
            "<details class=\"node lp\"><summary><span class=\"k\">%s</span>"
            "<span class=\"c\">코드 <b>%s</b> · <a href=\"%s\">%s</a></span>"
            "<span class=\"c\">처음 칸 h = <b>%d</b> → 저장 칸 %d · 탐색 %d칸 %s</span>"
            "<span class=\"c mono\">경로: %s</span></summary>%s</details></div>"
            % (i, i, escape(key), escape(code), escape(link, quote=True), escape(link),
               home, i, len(path), badge, " → ".join("[%d]" % p for p in path),
               horner_html(table, key)))
    out.append("</div></div>")
    return "".join(out)


SIM_JS = r"""
(function(){
var D = JSON.parse(document.getElementById('simdata').textContent);
var M = D.m, form = document.getElementById('sim'), logEl = document.getElementById('simlog');
var timer = null;
function cps(s){ var a=[]; for (var ch of s) a.push(ch); return a; }  // 파이썬 ord()와 같게 코드 포인트 단위
function clear(){ document.querySelectorAll('.bucket.hl,.bucket.hl2,.bucket.hl3').forEach(function(e){e.classList.remove('hl','hl2','hl3');}); }
function mark(i, cls){ var e=document.getElementById('b'+i); if(e){ e.classList.add(cls); return e; } }
function run(mode){
  if (timer) clearInterval(timer);
  clear(); logEl.innerHTML='';
  var key = document.getElementById('simkey').value;
  var steps = [], h = 0, chars = cps(key);
  steps.push(['h = 0 에서 시작, M = '+M, null]);
  chars.forEach(function(c, i){
    var o = c.codePointAt(0), nh = (31*h + o) % M;
    steps.push(['['+i+'] \''+c+'\' ord='+o+' : (31×'+h+' + '+o+') mod '+M+' = '+nh, null]);
    h = nh;
  });
  steps.push(['처음 칸 = '+h, function(){ mark(h,'hl'); }]);
  if (D.kind === 'chaining') {
    var chain = D.slots[h], found = false;
    if (chain.length === 0) steps.push(['['+h+'] 는 NULL → 비교 0번', null]);
    for (var k=0;k<chain.length;k++){
      (function(k){
        var eq = chain[k] === key;
        steps.push(['노드 '+(k+1)+' 비교: '+chain[k]+(eq?'  ✔ 같음':'  ✘ 다름'), null]);
      })(k);
      if (chain[k] === key){ found = true; break; }
    }
    var n = found ? chain.indexOf(key)+1 : chain.length;
    if (mode === 'search') steps.push([found ? '성공 탐색: 노드 '+n+'개 비교' : '실패 탐색: 노드 '+n+'개 비교 후 NULL', function(){ mark(h, found?'hl3':'hl2'); }]);
    else steps.push([found ? '이미 있는 키 → 값만 덮어씀 (비교 '+n+'번)' : '리스트 끝(NULL 자리)에 새 노드를 붙임 (비교 '+n+'번)', function(){ mark(h,'hl3'); }]);
  } else {
    var i = h, firstFree = -1, done = false, count = 0, found = false;
    for (var t=0;t<M && !done;t++){
      var s = D.slots[i]; count++;
      (function(i, s){
        var msg, cls='hl';
        if (s === null){ msg='['+i+'] EMPTY → 탐색 끝'; done = true; if(firstFree<0) firstFree=i; }
        else if (s === '\u0000TOMB'){ msg='['+i+'] TOMBSTONE → 건너뛰고 다음 칸'; if(firstFree<0) firstFree=i; }
        else if (s === key){ msg='['+i+'] '+s+'  ✔ 같은 키'; done = true; cls='hl3'; }
        else { msg='['+i+'] '+s+'  ✘ 다른 키 → (index+1) mod '+M; }
        steps.push([msg, function(){ mark(i, cls).scrollIntoView({block:'nearest'}); }]);
      })(i, s);
      if (s === key){ found = true; break; }
      if (s === null) break;
      i = (i + 1) % M;
    }
    if (mode === 'search') steps.push([found ? '성공 탐색: '+count+'칸 탐색' : '실패 탐색: '+count+'칸 탐색', null]);
    else if (found) steps.push(['이미 있는 키 → 값만 덮어씀', null]);
    else if (firstFree >= 0) steps.push(['['+firstFree+'] 에 저장 ('+count+'칸 탐색, 처음 칸에서 '+((firstFree-h+M)%M)+'칸 밀림)', function(){ mark(firstFree,'hl3'); }]);
    else steps.push(['빈 칸이 없음 → 테이블을 늘려야 함', null]);
  }
  var j = 0;
  timer = setInterval(function(){
    if (j >= steps.length){ clearInterval(timer); timer=null; return; }
    var li = document.createElement('li'); li.textContent = steps[j][0]; logEl.appendChild(li);
    if (steps[j][1]) steps[j][1]();
    logEl.scrollTop = logEl.scrollHeight; j++;
  }, Number(document.getElementById('simspeed').value));
}
form.addEventListener('submit', function(e){ e.preventDefault(); run(e.submitter && e.submitter.value === 'insert' ? 'insert' : 'search'); });
})();
"""

SIM_CSS = """
.sim ol{max-height:260px;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:8px;
padding:8px 8px 8px 32px;font-family:ui-monospace,monospace;font-size:13px;word-break:break-all}
.bucket.hl{background:#fff6d6}.bucket.hl2{background:#fde3e3}.bucket.hl3{background:#dff5ea}
.badge{display:inline-block;border-radius:10px;padding:0 8px;font-size:12px;margin-left:4px}
.badge.home{background:#dff5ea;color:#0d6b47}.badge.moved{background:#fde9de;color:#9a3a12}
details.node.lp{max-width:none;flex:1 1 auto}
"""


def sim_html(table, which):
    """현재 테이블을 그대로 복사해 브라우저에서 삽입·검색 과정을 한 단계씩 보여 준다(테이블은 바꾸지 않음)."""
    import json
    from linear_probing import TOMBSTONE
    if table.kind == "chaining":
        slots = [[k for k, _ in chain] for chain in table.snapshot()]
    else:
        slots = [None if s is None else ("\u0000TOMB" if s is TOMBSTONE else s[0]) for s in table.snapshot()]
    data = ('{"kind": %s, "m": %d, "slots": %s}'
            % (json.dumps(table.kind), table.capacity, json.dumps(slots, ensure_ascii=False)))
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    example = "https://example.com/new" if which == "url" else "1"
    return ("<div class=\"card sim\"><h3>삽입·검색 과정 단계별 보기</h3>"
            "<p class=\"muted\">아래 테이블의 현재 상태로 호너 해시 계산 → 칸 찾기 → %s 과정을 한 줄씩 보여 줍니다. "
            "실제 테이블은 바뀌지 않습니다.</p>"
            "<form id=\"sim\" class=\"row-form\"><input type=\"text\" id=\"simkey\" value=\"%s\" autocomplete=\"off\">"
            "<button type=\"submit\" value=\"search\">검색 과정</button>"
            "<button type=\"submit\" value=\"insert\" class=\"secondary\">삽입 과정</button>"
            "<select id=\"simspeed\" aria-label=\"속도\"><option value=\"700\">보통</option>"
            "<option value=\"1400\">느리게</option><option value=\"150\">빠르게</option></select></form>"
            "<ol id=\"simlog\"></ol></div>"
            "<script type=\"application/json\" id=\"simdata\">%s</script><script>%s</script>"
            % ("연결 리스트 비교" if table.kind == "chaining" else "다음 칸 탐색",
               escape(example, quote=True), data, SIM_JS))


def render_table(app, base, impl, which):
    s = app.shortener(impl)
    table = s.url_table if which == "url" else s.code_table
    name = "URL → 코드" if which == "url" else "코드 → URL"

    def link(i, w, label):
        on = " style=\"font-weight:700\"" if (i, w) == (impl, which) or (w is None and i == impl) else ""
        return "<a href=\"/table?impl=%s&amp;which=%s\"%s>%s</a>" % (i, w or which, on, label)

    tabs = ("<div class=\"toolbar\"><span>알고리즘:</span>%s · %s"
            "<span style=\"margin-left:12px\">테이블:</span>%s · %s"
            "<span class=\"muted\">(리다이렉트에 쓰는 쪽: %s)</span></div>"
            % (link("chaining", None, "개별 체이닝"), link("linear", None, "선형 탐지"),
               link(impl, "url", "URL → 코드"), link(impl, "code", "코드 → URL"),
               "개별 체이닝" if app.table == "chaining" else "선형 탐지"))
    if impl == "linear":
        view = render_table_linear(base, table, which, "선형 탐지 · %s 테이블" % name)
    else:
        view = render_table_chaining(base, table, which, "개별 체이닝 · %s 테이블" % name)
    body = "<style>%s</style>%s%s%s" % (SIM_CSS, tabs, sim_html(table, which), view)
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
                impl = query_value(query, "impl") or app.table
                if impl not in ("chaining", "linear"):
                    impl = app.table
                return self.send_html(200, render_table(app, self.base_url(), impl, which))
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
