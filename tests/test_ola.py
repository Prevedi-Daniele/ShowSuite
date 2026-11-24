import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from showsuite.light import project as pj
from showsuite.light.dmx.drivers.ola import OlaDriver, build_set_dmx


def test_build_body():
    assert build_set_dmx(3, bytes([1, 2, 255])) == "u=3&d=1%2C2%2C255"


def test_driver_posts_to_ola_like_server():
    got = []

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            got.append((self.path, parse_qs(body.decode()))); self.send_response(200)
            self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self, *a): pass

    srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        d = pj.OutputConfig("ola", 2, {"host": "127.0.0.1", "port": srv.server_port}).build()
        d.open(); d.send(2, bytes([9, 8, 7])); d.send(2, bytes([1])); d.close()
        assert got[0] == ("/set_dmx", {"u": ["2"], "d": ["9,8,7"]}) and len(got) == 2
    finally:
        srv.shutdown()
