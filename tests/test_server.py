"""웹 서버 테스트 (이슈 #7, #8). SPEC.md 5절.

실제 http.server를 빈 포트(0)로 스레드에서 띄우고 http.client로 요청한다.
리다이렉트를 따라가지 않으므로 302와 Location을 그대로 확인할 수 있다.
"""
import http.client
import os
import sys
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import App, make_server  # noqa: E402


class ServerTestBase:
    TABLE = "chaining"

    def setUp(self):
        self.app = App(table=self.TABLE)
        self.httpd = make_server(self.app, "127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": "127.0.0.1:%d" % self.port}
        if body is not None:
            body = urlencode(body)
            h["Content-Type"] = "application/x-www-form-urlencoded"
        if headers:
            h.update(headers)
        conn.request(method, path, body=body, headers=h)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        return resp, data

    def shorten(self, url, headers=None):
        return self.request("POST", "/shorten", {"url": url}, headers)

    # ---- 테스트 ----
    def test_index_has_form(self):
        resp, html = self.request("GET", "/")
        self.assertEqual(resp.status, 200)
        self.assertIn("text/html", resp.getheader("Content-Type"))
        self.assertIn("<form", html)
        self.assertIn('name="url"', html)
        self.assertIn('action="/shorten"', html)

    def test_shorten_shows_short_link(self):
        resp, html = self.shorten("https://www.yonsei.ac.kr/sc/")
        self.assertEqual(resp.status, 200)
        self.assertIn("http://127.0.0.1:%d/1" % self.port, html)
        self.assertIn("https://www.yonsei.ac.kr/sc/", html)

    def test_duplicate_url_same_code(self):
        self.shorten("https://a.example/x")
        resp, html = self.shorten("https://a.example/x")
        self.assertIn("/1<", html)
        self.assertEqual(len(self.app.primary), 1)

    def test_redirect(self):
        self.shorten("https://example.com/long/path?q=1")
        resp, _ = self.request("GET", "/1")
        self.assertEqual(resp.status, 302)
        self.assertEqual(resp.getheader("Location"), "https://example.com/long/path?q=1")

    def test_unknown_code_404(self):
        for path in ("/1", "/zz", "/bad_code", "/%ED%95%9C"):
            resp, html = self.request("GET", path)
            self.assertEqual(resp.status, 404, path)

    def test_invalid_url_400(self):
        for bad in ("ftp://example.com", "example.com", "https://a b.com", "", "https://"):
            resp, html = self.shorten(bad)
            self.assertEqual(resp.status, 400, bad)
            self.assertIn("<form", html)
            self.assertIn('class="error"', html)
        self.assertEqual(len(self.app.primary), 0)

    def test_missing_field_400(self):
        resp, _ = self.request("POST", "/shorten", {"other": "x"})
        self.assertEqual(resp.status, 400)

    def test_expand_page(self):
        self.shorten("https://example.com/e")
        resp, html = self.request("GET", "/expand?code=1")
        self.assertEqual(resp.status, 200)
        self.assertIn("https://example.com/e", html)
        resp, _ = self.request("GET", "/expand?code=9")
        self.assertEqual(resp.status, 404)
        resp, _ = self.request("GET", "/expand")
        self.assertEqual(resp.status, 404)

    def test_forwarded_host_used_for_short_link(self):
        resp, html = self.shorten(
            "https://example.com/fw",
            {"X-Forwarded-Host": "abc-8000.app.github.dev", "X-Forwarded-Proto": "https"})
        self.assertIn("https://abc-8000.app.github.dev/1", html)
        self.assertNotIn("127.0.0.1", html.split("짧은 링크")[1][:300])

    def test_html_is_escaped(self):
        resp, html = self.shorten('https://evil.example/"><script>alert(1)</script>')
        self.assertEqual(resp.status, 200)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        resp, html = self.request("GET", "/table")
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_table_page_chaining(self):
        self.shorten("https://example.com/a")
        self.shorten("https://example.com/b")
        resp, html = self.request("GET", "/table?impl=chaining")
        self.assertEqual(resp.status, 200)
        self.assertIn("NULL", html)
        self.assertIn("https://example.com/a", html)
        self.assertIn("31", html)           # 호너 계산 과정
        self.assertIn("<details", html)     # 노드를 펼치면 계산 과정
        self.assertIn("/1", html)           # 짧은 링크

    def test_table_default_page(self):
        resp, html = self.request("GET", "/table")
        self.assertEqual(resp.status, 200)
        self.assertIn("NULL", html)

    def test_unknown_path_and_method(self):
        resp, _ = self.request("GET", "/no/such/path")
        self.assertEqual(resp.status, 404)
        resp, _ = self.request("POST", "/")
        self.assertEqual(resp.status, 405)
        resp, _ = self.request("PUT", "/shorten", {"url": "https://a.com"})
        self.assertEqual(resp.status, 405)


class TestServerChaining(ServerTestBase, unittest.TestCase):
    TABLE = "chaining"


class TestServerLinear(ServerTestBase, unittest.TestCase):
    TABLE = "linear"

    def test_primary_uses_linear_table(self):
        self.assertEqual(self.app.primary.table_name, "linear")


class TestTableSwitch(ServerTestBase, unittest.TestCase):
    """/table 에서 두 알고리즘을 고를 수 있다 (과제 #8)."""

    def test_both_tables_receive_same_urls(self):
        self.shorten("https://example.com/a")
        self.shorten("https://example.com/b")
        self.assertEqual(len(self.app.chaining), 2)
        self.assertEqual(len(self.app.linear), 2)
        self.assertEqual(self.app.linear.expand("2"), "https://example.com/b")

    def test_table_page_linear(self):
        self.shorten("https://example.com/a")
        self.shorten("https://example.com/b")
        resp, html = self.request("GET", "/table?impl=linear")
        self.assertEqual(resp.status, 200)
        self.assertIn("선형 탐지", html)
        self.assertIn("https://example.com/a", html)
        self.assertIn("탐색", html)          # 처음 칸에서 몇 칸 탐색했는지
        self.assertIn("EMPTY", html)
        self.assertIn("31", html)

    def test_table_page_has_both_switch_links(self):
        resp, html = self.request("GET", "/table")
        self.assertIn("impl=chaining", html)
        self.assertIn("impl=linear", html)

    def test_table_page_has_step_animation(self):
        resp, html = self.request("GET", "/table?impl=linear")
        self.assertIn('id="sim"', html)
        resp, html = self.request("GET", "/table?impl=chaining")
        self.assertIn('id="sim"', html)


if __name__ == "__main__":
    unittest.main()
