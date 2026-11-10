"""Stdlib unittest: signing, replay protection, payload validation, image helpers."""
import unittest

from app.content.image_sourcing import commons_license_ok, extract_keywords, score_relevance
from app.publishing.blog_client import build_payload, sign_request, verify_signature


class BlogClientTests(unittest.TestCase):
    def test_signature_roundtrip(self):
        sig = sign_request("s3cret", "1000", "key-1", '{"a":1}')
        self.assertTrue(verify_signature("s3cret", "1000", "key-1", '{"a":1}', sig, now=1100))

    def test_tampered_body_rejected(self):
        sig = sign_request("s3cret", "1000", "key-1", '{"a":1}')
        self.assertFalse(verify_signature("s3cret", "1000", "key-1", '{"a":2}', sig, now=1100))

    def test_wrong_secret_rejected(self):
        sig = sign_request("other", "1000", "key-1", "x")
        self.assertFalse(verify_signature("s3cret", "1000", "key-1", "x", sig, now=1000))

    def test_replay_after_window_rejected(self):
        sig = sign_request("s", "1000", "k", "x")
        self.assertFalse(verify_signature("s", "1000", "k", "x", sig, now=1000 + 301))

    def test_worker_style_empty_key(self):
        sig = sign_request("s", "1000", "", "feed")  # format: ts..message
        self.assertTrue(verify_signature("s", "1000", "", "feed", sig, now=1000))

    def test_payload_requires_fields(self):
        with self.assertRaises(ValueError):
            build_payload({"title": "x", "slug": "", "content": "c"})
        self.assertEqual(build_payload({"title": "T", "slug": "t", "content": "c"})["status"], "draft")


class ImageHelperTests(unittest.TestCase):
    def test_keywords(self):
        self.assertEqual(extract_keywords("The new chip says Nvidia is the leader in AI"), "chip Nvidia leader")

    def test_license_filter(self):
        self.assertTrue(commons_license_ok("CC BY-SA 4.0"))
        self.assertTrue(commons_license_ok("CC0"))
        self.assertFalse(commons_license_ok("CC BY-NC 4.0"))
        self.assertFalse(commons_license_ok("All rights reserved"))

    def test_relevance(self):
        self.assertGreater(score_relevance("rocket launch pad", "rocket launch"), score_relevance("cat", "rocket launch"))


if __name__ == "__main__":
    unittest.main()
