"""Versioned frame endpoint and browser preview."""

import hashlib
import hmac
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from frame import CONTENT_TYPE, FRAME_SIZE, HEIGHT, WIDTH, validate_frame
from providers import SampleProvider
from renderer import DEFAULT_LAYOUT_PATH, Renderer

FRAME_PATH = "/api/frame/v1"
PREVIEW_PATH = "/preview"
DEFAULT_REFRESH_SECONDS = 60
FRAME_HISTORY_LIMIT = 8


def crop_frame_delta(previous, current):
    """Return byte-aligned bounds and packed pixels for the changed area."""
    first_byte = WIDTH // 8
    last_byte = -1
    first_row = HEIGHT
    last_row = -1
    bytes_per_row = WIDTH // 8
    for y in range(HEIGHT):
        row_start = y * bytes_per_row
        changed = [x for x in range(bytes_per_row)
                   if previous[row_start + x] != current[row_start + x]]
        if changed:
            first_byte = min(first_byte, changed[0])
            last_byte = max(last_byte, changed[-1])
            first_row = min(first_row, y)
            last_row = y
    if last_row < 0:
        return None
    width_bytes = last_byte - first_byte + 1
    payload = b"".join(
        current[y * bytes_per_row + first_byte:
                y * bytes_per_row + first_byte + width_bytes]
        for y in range(first_row, last_row + 1)
    )
    return (first_byte * 8, first_row, width_bytes * 8,
            last_row - first_row + 1, payload)

PREVIEW_HTML = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Slate frame preview</title>
<style>body{font:16px system-ui;margin:2rem;background:#eee;color:#222}canvas{display:block;width:min(100%,1000px);height:auto;border:1px solid #777;background:white;image-rendering:pixelated}</style>
<h1>Slate frame preview</h1><p>Version 1 · 800 × 480 · top-left origin</p>
<label>Device token <input id="token" type="password" autocomplete="off"></label>
<canvas id="frame" width="800" height="480" aria-label="Current Slate monochrome frame"></canvas>
<script>
let etag;
async function updateFrame(){
 try{
  const headers=etag?{'If-None-Match':etag}:{};
  const token=document.querySelector('#token').value;
  if(!token)return;
  headers.Authorization='Bearer '+token;
  const response=await fetch('/api/frame/v1',{headers,cache:'no-store'});
  if(response.status===304)return;
  if(!response.ok)throw Error('Frame request failed: '+response.status);
  const bytes=new Uint8Array(await response.arrayBuffer());
  if(bytes.length!==48000)throw Error('Invalid frame size');
  const canvas=document.querySelector('#frame'),ctx=canvas.getContext('2d'),image=ctx.createImageData(800,480);
  for(let y=0;y<480;y++)for(let x=0;x<800;x++){
   const black=(bytes[y*100+(x>>3)]&(128>>(x&7)))===0,offset=(y*800+x)*4,value=black?0:255;
   image.data[offset]=image.data[offset+1]=image.data[offset+2]=value;image.data[offset+3]=255;
  }
  ctx.putImageData(image,0,0);
  etag=response.headers.get('ETag');
 }catch(error){
  let message=document.querySelector('#error');
  if(!message){message=document.createElement('p');message.id='error';message.setAttribute('role','alert');document.body.append(message);}
  message.textContent=error.message;
 }
}
updateFrame();
setInterval(updateFrame,5000);
</script></html>"""


class CachedFrame:
    """Render at most once per refresh interval and retain a stable frame ETag."""

    def __init__(self, frame_provider, refresh_seconds=DEFAULT_REFRESH_SECONDS, cache_key_provider=None):
        if refresh_seconds < 1:
            raise ValueError("refresh_seconds must be at least 1")
        self.frame_provider = frame_provider
        self.refresh_seconds = refresh_seconds
        self.cache_key_provider = cache_key_provider or (lambda: None)
        self.lock = threading.Lock()
        self.frame = None
        self.etag = None
        self.frames_by_etag = {}
        self.frame_etags = []
        self.rendered_at = 0

    def get(self):
        with self.lock:
            cache_key = self.cache_key_provider()
            if (self.frame is None or cache_key != self.cache_key
                    or time.monotonic() - self.rendered_at >= self.refresh_seconds):
                frame = validate_frame(self.frame_provider())
                self.frame = frame
                self.etag = '"' + hashlib.sha256(frame).hexdigest() + '"'
                if self.etag not in self.frames_by_etag:
                    self.frames_by_etag[self.etag] = frame
                    self.frame_etags.append(self.etag)
                    while len(self.frame_etags) > FRAME_HISTORY_LIMIT:
                        expired = self.frame_etags.pop(0)
                        self.frames_by_etag.pop(expired, None)
                self.rendered_at = time.monotonic()
                self.cache_key = self.cache_key_provider()
            return self.frame, self.etag

    def get_by_etag(self, etag):
        with self.lock:
            return self.frames_by_etag.get(etag)


def create_handler(frame_provider=None, refresh_seconds=DEFAULT_REFRESH_SECONDS,
                   device_token=None, require_https=False):
    cache_key_provider = None
    if frame_provider is None:
        layout_path = os.environ.get("SLATE_LAYOUT_PATH", str(DEFAULT_LAYOUT_PATH))
        layout_file = os.path.abspath(layout_path)

        def layout_file_signature():
            stat = os.stat(layout_file)
            return stat.st_mtime_ns, stat.st_size

        provider = SampleProvider()
        frame_provider = lambda: Renderer.from_file(layout_file).render(provider.get_data())
        cache_key_provider = layout_file_signature
    cached_frame = CachedFrame(frame_provider, refresh_seconds, cache_key_provider)
    if not device_token:
        raise ValueError("a device token is required")

    class SlateHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == PREVIEW_PATH:
                body = PREVIEW_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == FRAME_PATH:
                if require_https and self.headers.get("X-Forwarded-Proto", "").lower() != "https":
                    self.send_error(400, "HTTPS is required")
                    return
                authorization = self.headers.get("Authorization", "")
                scheme, separator, supplied_token = authorization.partition(" ")
                if (not separator or scheme.lower() != "bearer"
                        or not hmac.compare_digest(supplied_token, device_token)):
                    self.send_error(401, "Unauthorized")
                    return
                try:
                    frame, etag = cached_frame.get()
                except (OSError, TypeError, ValueError):
                    self.send_error(500, "Frame could not be rendered")
                    return
                if self.headers.get("If-None-Match"):
                    tags = {tag.strip().removeprefix("W/") for tag in self.headers["If-None-Match"].split(",")}
                    if "*" in tags or etag in tags:
                        self.send_response(304)
                        self.send_header("ETag", etag)
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("X-Slate-Format-Version", "1")
                        self.send_header("X-Slate-Width", "800")
                        self.send_header("X-Slate-Height", "480")
                        self.end_headers()
                        return
                refresh_mode = self.headers.get("X-Slate-Refresh-Mode", "full").lower()
                displayed_etag = self.headers.get("X-Slate-Displayed-ETag", "")
                region = None
                fallback_reason = ""
                if refresh_mode == "partial" and displayed_etag:
                    previous = cached_frame.get_by_etag(displayed_etag)
                    if previous is not None:
                        region = crop_frame_delta(previous, frame)
                        if region is None:
                            fallback_reason = "no-byte-differences"
                    else:
                        fallback_reason = "displayed-frame-not-in-history"
                elif refresh_mode == "partial":
                    fallback_reason = "displayed-etag-missing"
                if region is None:
                    x, y, width, height, body = 0, 0, WIDTH, HEIGHT, frame
                    payload_type = "full"
                else:
                    x, y, width, height, body = region
                    payload_type = "delta"
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("ETag", etag)
                self.send_header("X-Slate-Format-Version", "1")
                self.send_header("X-Slate-Width", "800")
                self.send_header("X-Slate-Height", "480")
                self.send_header("X-Slate-Region-X", str(x))
                self.send_header("X-Slate-Region-Y", str(y))
                self.send_header("X-Slate-Region-Width", str(width))
                self.send_header("X-Slate-Region-Height", str(height))
                self.send_header("X-Slate-Payload-Type", payload_type)
                if fallback_reason:
                    self.send_header("X-Slate-Fallback", fallback_reason)
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def log_message(self, _format, *_args):
            pass

    return SlateHandler


def create_server(frame_provider=None, host="127.0.0.1", port=8000,
                  refresh_seconds=DEFAULT_REFRESH_SECONDS, device_token=None,
                  require_https=False):
    return ThreadingHTTPServer((host, port), create_handler(
        frame_provider, refresh_seconds, device_token, require_https))


if __name__ == "__main__":
    refresh_seconds = int(os.environ.get("SLATE_REFRESH_SECONDS", DEFAULT_REFRESH_SECONDS))
    token = os.environ.get("SLATE_DEVICE_TOKEN")
    if not token:
        raise SystemExit("SLATE_DEVICE_TOKEN must be set")
    require_https_value = os.environ.get("SLATE_REQUIRE_HTTPS", "true").lower()
    if require_https_value not in ("true", "false", "1", "0"):
        raise SystemExit("SLATE_REQUIRE_HTTPS must be true or false")
    require_https = require_https_value in ("true", "1")
    server = create_server(host=os.environ.get("SLATE_HOST", "0.0.0.0"),
                           refresh_seconds=refresh_seconds, device_token=token,
                           require_https=require_https)
    address = server.server_address
    print(f"Slate preview: http://{address[0]}:{address[1]}{PREVIEW_PATH}")
    server.serve_forever()
