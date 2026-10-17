"""Minimal versioned frame endpoint and browser preview for development."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from frame import CONTENT_TYPE, FRAME_SIZE, sample_frame, validate_frame

FRAME_PATH = "/api/frame/v1"
PREVIEW_PATH = "/preview"

PREVIEW_HTML = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Slate frame preview</title>
<style>body{font:16px system-ui;margin:2rem;background:#eee;color:#222}canvas{display:block;width:min(100%,1000px);height:auto;border:1px solid #777;background:white;image-rendering:pixelated}</style>
<h1>Slate frame preview</h1><p>Version 1 · 800 × 480 · top-left origin</p>
<canvas id="frame" width="800" height="480" aria-label="Current Slate monochrome frame"></canvas>
<script>
fetch('/api/frame/v1').then(r=>{if(!r.ok)throw Error('Frame request failed: '+r.status);return r.arrayBuffer()})
 .then(buffer=>{const bytes=new Uint8Array(buffer);if(bytes.length!==48000)throw Error('Invalid frame size');
 const canvas=document.querySelector('#frame'),ctx=canvas.getContext('2d'),image=ctx.createImageData(800,480);
 for(let y=0;y<480;y++)for(let x=0;x<800;x++){
  const black=(bytes[y*100+(x>>3)]&(128>>(x&7)))===0,offset=(y*800+x)*4,value=black?0:255;
  image.data[offset]=image.data[offset+1]=image.data[offset+2]=value;image.data[offset+3]=255;
 }ctx.putImageData(image,0,0);
 }).catch(error=>{document.body.insertAdjacentHTML('beforeend','<p role="alert">'+error.message+'</p>');});
</script></html>"""


def create_handler(frame_provider=sample_frame):
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
                try:
                    frame = validate_frame(frame_provider())
                except (TypeError, ValueError):
                    self.send_error(500, "Frame provider returned an invalid frame")
                    return
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE)
                self.send_header("Content-Length", str(FRAME_SIZE))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(frame)
                return
            self.send_error(404)

        def log_message(self, _format, *_args):
            pass

    return SlateHandler


def create_server(frame_provider=sample_frame, host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), create_handler(frame_provider))


if __name__ == "__main__":
    server = create_server()
    address = server.server_address
    print(f"Slate preview: http://{address[0]}:{address[1]}{PREVIEW_PATH}")
    server.serve_forever()
