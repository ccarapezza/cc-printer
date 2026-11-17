#!/usr/bin/env python3
"""CC-Printer A1 webcam: Picamera2 (IMX219 NoIR) -> MJPEG on 127.0.0.1:8080.
nginx publishes it as /webcam/stream.mjpg and /webcam/snapshot.jpg (used by Fluidd)."""
import io, logging, socketserver
from http import server
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

SIZE, FPS, PORT = (1280, 960), 15, 8080
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

class Out(io.BufferedIOBase):
    def __init__(self):
        self.frame, self.cond = None, Condition()
    def write(self, buf):
        with self.cond:
            self.frame = buf; self.cond.notify_all()

class Handler(server.BaseHTTPRequestHandler):
    def _jpeg_headers(self, n):
        self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", n)
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/snapshot.jpg", "/snapshot"):
            with out.cond:
                out.cond.wait_for(lambda: out.frame is not None, timeout=5); f = out.frame
            if f is None:
                return self.send_error(503)
            self.send_response(200); self.send_header("Cache-Control", "no-cache, private")
            self._jpeg_headers(len(f)); self.end_headers(); self.wfile.write(f)
        elif path in ("/stream.mjpg", "/stream", "/"):
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()
            try:
                while True:
                    with out.cond:
                        out.cond.wait(); f = out.frame
                    self.wfile.write(b"--FRAME\r\n"); self._jpeg_headers(len(f)); self.end_headers()
                    self.wfile.write(f); self.wfile.write(b"\r\n")
            except Exception:
                pass
        else:
            self.send_error(404)
    def log_message(self, *a):
        pass

class Srv(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True; daemon_threads = True

tuning = Picamera2.load_tuning_file("imx219_noir.json", dir="/usr/share/libcamera/ipa/rpi/vc4")
cam = Picamera2(tuning=tuning)
cam.configure(cam.create_video_configuration(main={"size": SIZE}, controls={"FrameRate": FPS}))
out = Out()
cam.start_recording(MJPEGEncoder(), FileOutput(out))
logging.info("camara %sx%s @ %s fps en 127.0.0.1:%s", *SIZE, FPS, PORT)
try:
    Srv(("127.0.0.1", PORT), Handler).serve_forever()
finally:
    cam.stop_recording()
