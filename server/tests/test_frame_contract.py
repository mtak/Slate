import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import FRAME_PATH, PREVIEW_PATH, create_server
from frame import (
    CONTENT_TYPE,
    FRAME_SIZE,
    HEIGHT,
    WIDTH,
    pixel_is_black,
    sample_frame,
    validate_frame,
)
from providers import SampleProvider
from renderer import Renderer

DEVICE_TOKEN = "test-only-device-token"


class FrameContractTests(unittest.TestCase):
    def test_sample_frame_round_trips_as_48k_raw_bytes(self):
        frame = sample_frame()
        self.assertEqual(len(frame), FRAME_SIZE)
        self.assertEqual(FRAME_SIZE, 48_000)
        self.assertTrue(pixel_is_black(frame, 16, 16))
        self.assertTrue(pixel_is_black(frame, WIDTH - 17, 16))
        self.assertTrue(pixel_is_black(frame, 16, HEIGHT - 17))
        self.assertTrue(pixel_is_black(frame, WIDTH - 17, HEIGHT - 17))
        self.assertTrue(pixel_is_black(frame, 200, 85))
        self.assertTrue(pixel_is_black(frame, 85, 200))
        self.assertFalse(pixel_is_black(frame, 100, 100))
        self.assertIs(validate_frame(frame), frame)

    def test_first_pixel_uses_most_significant_bit(self):
        frame_data = bytearray([0xFF]) * FRAME_SIZE
        frame_data[0] = 0x7F
        frame = bytes(frame_data)
        self.assertTrue(pixel_is_black(frame, 0, 0))
        self.assertFalse(pixel_is_black(frame, 1, 0))

    def test_frame_size_is_enforced(self):
        with self.assertRaises(ValueError):
            validate_frame(b"\xff" * (FRAME_SIZE - 1))

    def test_v1_endpoint_returns_exact_frame_and_preview_page(self):
        frame = sample_frame()
        server = create_server(lambda: frame, port=0, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(Request(base + FRAME_PATH, headers={
                    "Authorization": "Bearer " + DEVICE_TOKEN,
                    "X-Slate-Refresh-Mode": "full"})) as response:
                self.assertEqual(response.headers.get_content_type(), CONTENT_TYPE)
                self.assertEqual(response.headers["X-Slate-Payload-Type"], "full")
                self.assertEqual(response.headers["X-Slate-Region-Width"], "800")
                self.assertEqual(response.read(), frame)
            with urlopen(base + PREVIEW_PATH) as response:
                page = response.read().decode("utf-8")
                self.assertIn('width="800" height="480"', page)
                self.assertIn("bytes[y*100+(x>>3)]", page)
                self.assertIn("128>>(x&7)", page)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_default_endpoint_serves_layout_rendered_frame(self):
        expected = Renderer.from_file().render(SampleProvider().get_data())
        server = create_server(port=0, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
            with urlopen(Request(url, headers={"Authorization": "Bearer " + DEVICE_TOKEN})) as response:
                self.assertEqual(response.read(), expected)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_conditional_request_uses_stable_etag_and_returns_304(self):
        frame = sample_frame()
        server = create_server(lambda: frame, port=0, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
        try:
            with urlopen(Request(url, headers={"Authorization": "Bearer " + DEVICE_TOKEN})) as response:
                etag = response.headers["ETag"]
                self.assertEqual(len(response.read()), FRAME_SIZE)
            request = Request(url, headers={"If-None-Match": etag, "Authorization": "Bearer " + DEVICE_TOKEN})
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 304)
            self.assertEqual(error.exception.headers["ETag"], etag)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_partial_request_returns_only_byte_aligned_changed_bounds(self):
        original = bytearray([0xFF]) * FRAME_SIZE
        changed = bytearray(original)
        changed[5 * (WIDTH // 8) + 2] = 0x7F
        changed[8 * (WIDTH // 8) + 5] = 0xFE
        provider_frames = iter((bytes(original), bytes(changed)))
        server = create_server(lambda: next(provider_frames), port=0,
                               refresh_seconds=1, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
        headers = {"Authorization": "Bearer " + DEVICE_TOKEN}
        try:
            with urlopen(Request(url, headers=headers)) as response:
                old_etag = response.headers["ETag"]
                self.assertEqual(len(response.read()), FRAME_SIZE)
            time.sleep(1.05)
            headers.update({
                "If-None-Match": old_etag,
                "X-Slate-Displayed-ETag": old_etag,
                "X-Slate-Refresh-Mode": "partial",
            })
            with urlopen(Request(url, headers=headers)) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-Slate-Payload-Type"], "delta")
                self.assertEqual(response.headers["X-Slate-Region-X"], "16")
                self.assertEqual(response.headers["X-Slate-Region-Y"], "5")
                self.assertEqual(response.headers["X-Slate-Region-Width"], "32")
                self.assertEqual(response.headers["X-Slate-Region-Height"], "4")
                crop = response.read()
                self.assertEqual(len(crop), 16)
                self.assertEqual(crop[:4], bytes((0x7F, 0xFF, 0xFF, 0xFF)))
                self.assertEqual(crop[12:], bytes((0xFF, 0xFF, 0xFF, 0xFE)))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_partial_request_falls_back_to_full_frame_for_unknown_displayed_etag(self):
        frame = sample_frame()
        server = create_server(lambda: frame, port=0, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
        headers = {
            "Authorization": "Bearer " + DEVICE_TOKEN,
            "X-Slate-Refresh-Mode": "partial",
            "X-Slate-Displayed-ETag": '"not-in-history"',
        }
        try:
            with urlopen(Request(url, headers=headers)) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-Slate-Payload-Type"], "full")
                self.assertEqual(response.headers["X-Slate-Fallback"],
                                 "displayed-frame-not-in-history")
                self.assertEqual(response.headers["X-Slate-Region-Width"], "800")
                self.assertEqual(len(response.read()), FRAME_SIZE)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_frame_endpoint_rejects_missing_or_invalid_device_token(self):
        server = create_server(lambda: sample_frame(), port=0, device_token=DEVICE_TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
        try:
            for headers in ({}, {"Authorization": "Bearer wrong-token"}):
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url, headers=headers))
                self.assertEqual(error.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_https_can_be_required_behind_a_tls_terminating_proxy(self):
        server = create_server(lambda: sample_frame(), port=0,
                               device_token=DEVICE_TOKEN, require_https=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}{FRAME_PATH}"
        try:
            headers = {"Authorization": "Bearer " + DEVICE_TOKEN}
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, headers=headers))
            self.assertEqual(error.exception.code, 400)
            headers["X-Forwarded-Proto"] = "https"
            with urlopen(Request(url, headers=headers)) as response:
                self.assertEqual(len(response.read()), FRAME_SIZE)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class RendererTests(unittest.TestCase):
    def test_default_layout_renders_sample_values_to_frame_contract(self):
        renderer = Renderer.from_file()
        frame = renderer.render(SampleProvider().get_data())
        self.assertEqual(len(frame), FRAME_SIZE)
        self.assertTrue(pixel_is_black(frame, 24, 24))
        self.assertTrue(pixel_is_black(frame, 50, 112))
        self.assertFalse(pixel_is_black(frame, 400, 400))

    def test_layout_is_editable_without_changing_provider(self):
        layout = {
            "width": WIDTH,
            "height": HEIGHT,
            "blocks": [{"type": "text", "key": "message", "x": 80, "y": 90, "size": 24}],
        }
        frame = Renderer(layout).render({"message": "A sample"})
        self.assertTrue(any(pixel_is_black(frame, x, y) for y in range(90, 120) for x in range(80, 200)))

    def test_invalid_layout_dimensions_and_missing_data_are_rejected(self):
        with self.assertRaises(ValueError):
            Renderer({"width": 400, "height": HEIGHT, "blocks": []})
        renderer = Renderer({"width": WIDTH, "height": HEIGHT, "blocks": [{"type": "text", "key": "missing"}]})
        with self.assertRaisesRegex(ValueError, "missing data key"):
            renderer.render({})


if __name__ == "__main__":
    unittest.main()
