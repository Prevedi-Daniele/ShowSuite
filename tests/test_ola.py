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


def test_enttec_pro_packet_and_driver(monkeypatch):
    import sys, types
    from showsuite.light.dmx.drivers.enttecpro import EnttecProDriver, build_packet
    pk = build_packet(bytes([10, 20, 30]))
    assert pk == bytes([0x7E, 6, 4, 0, 0, 10, 20, 30, 0xE7])
    assert len(build_packet(bytes(600))) == 4 + 513 + 1            # tagliato a 512 + start code
    big = build_packet(bytes(512)); assert big[2:4] == bytes([0x01, 0x02])   # 513 = 0x0201 (LSB, MSB)
    written = []
    class FakeSerial:
        def __init__(self, port, **kw): self.port, self.kw = port, kw
        def write(self, b): written.append(b)
        def close(self): pass
    monkeypatch.setitem(sys.modules, "serial", types.SimpleNamespace(Serial=FakeSerial))
    d = pj.OutputConfig("enttecpro", 1, {"port": "COM3"}).build()
    d.open(); d.send(2, b"\x01"); d.send(1, b"\x05"); d.close()
    assert written == [bytes([0x7E, 6, 2, 0, 0, 5, 0xE7])]         # l'universo 2 è ignorato
