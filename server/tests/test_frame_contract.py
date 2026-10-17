import threading
import unittest
from urllib.request import urlopen

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
        server = create_server(lambda: frame, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(base + FRAME_PATH) as response:
                self.assertEqual(response.headers.get_content_type(), CONTENT_TYPE)
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


if __name__ == "__main__":
    unittest.main()
