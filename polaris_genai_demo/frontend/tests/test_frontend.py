#!/usr/bin/env python3
"""
Automated Test Suite for Polaris Demo Frontend & GCS Streaming Service
"""

import sys
import unittest
import requests

BASE_URL = "http://127.0.0.1:5001"

class TestPolarisFrontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify server is reachable
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=5)
            assert r.status_code == 200
        except Exception as e:
            raise RuntimeError(f"API server is not running on {BASE_URL}. Error: {e}")

    def test_01_health_endpoint(self):
        """Verify API health status and GCS configuration."""
        res = requests.get(f"{BASE_URL}/api/health", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("bucket"), "polaris-demo-files")
        self.assertEqual(data.get("project"), "polaris-genai-demo")

    def test_02_models_catalog(self):
        """Verify models catalog returns all models with proper metadata and <= 5 images."""
        res = requests.get(f"{BASE_URL}/api/models", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        models = data.get("models", [])
        self.assertGreaterEqual(len(models), 5)

        # Check required model IDs
        model_ids = [m["id"] for m in models]
        self.assertIn("G27G5X99AZ", model_ids)
        self.assertIn("G27GXK99AD", model_ids)
        self.assertIn("R27CCA5AE8", model_ids)
        self.assertIn("R27X6W1RB9", model_ids)
        self.assertIn("Z27XPE92AH", model_ids)

        for model in models:
            mid = model["id"]
            # 1. Video must strictly be sample_360_rotation.mp4
            self.assertIn("video", model)
            self.assertEqual(
                model["video"]["filename"],
                "sample_360_rotation.mp4",
                f"Model {mid} must use sample_360_rotation.mp4",
            )
            self.assertTrue(model["video"]["url"].startswith(f"/api/models/{mid}/video"))

            # 2. Images must be up to 5 static images
            images = model.get("images", [])
            self.assertGreater(len(images), 0, f"Model {mid} should have static images")
            self.assertLessEqual(len(images), 5, f"Model {mid} must have at most 5 images")

            for img in images:
                self.assertIn("filename", img)
                self.assertIn("label", img)
                self.assertIn("url", img)

    def test_03_video_streaming_and_range_requests(self):
        """Verify 360 video stream handles full requests and HTTP 206 range requests."""
        model_id = "G27G5X99AZ"
        video_url = f"{BASE_URL}/api/models/{model_id}/video"

        # HEAD request
        head_res = requests.head(video_url, timeout=10)
        self.assertEqual(head_res.status_code, 200)
        self.assertEqual(head_res.headers.get("Content-Type"), "video/mp4")
        self.assertIn("Content-Length", head_res.headers)
        total_length = int(head_res.headers["Content-Length"])
        self.assertGreater(total_length, 1000000)

        # Range request (bytes 0-1023)
        range_res = requests.get(video_url, headers={"Range": "bytes=0-1023"}, timeout=10)
        self.assertIn(range_res.status_code, [200, 206])
        if range_res.status_code == 206:
            self.assertEqual(len(range_res.content), 1024)
            self.assertIn("Content-Range", range_res.headers)

    def test_04_static_images_serving(self):
        """Verify static model images can be served properly."""
        res = requests.get(f"{BASE_URL}/api/models", timeout=5)
        models = res.json().get("models", [])
        
        # Test the first image of each model
        for model in models:
            mid = model["id"]
            first_img = model["images"][0]
            img_url = f"{BASE_URL}{first_img['url']}"
            img_res = requests.get(img_url, timeout=10)
            self.assertEqual(
                img_res.status_code, 200,
                f"Failed to fetch image {first_img['filename']} for model {mid}"
            )
            self.assertTrue(
                img_res.headers.get("Content-Type", "").startswith("image/"),
                f"Unexpected content type for {img_url}"
            )
            self.assertGreater(len(img_res.content), 5000)

    def test_05_frontend_html_and_assets(self):
        """Verify production SPA is served at root."""
        res = requests.get(f"{BASE_URL}/", timeout=5)
        res.encoding = "utf-8"
        self.assertEqual(res.status_code, 200)
        self.assertIn("Polaris 360° Studio", res.text)
        self.assertIn('<div id="root"></div>', res.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
