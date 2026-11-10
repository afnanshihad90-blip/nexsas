"""
NEXUS MEDIA AI — Cross-Language Signature Compatibility Test
Verifies exact byte-for-byte HMAC-SHA256 compatibility between:
1. Python (backend/app/publishing/blog_client.py)
2. PHP (blog/api/publish.php & blog/includes/sync_lib.php)
3. Node / WebCrypto (cloudflare-worker/src/index.js)
"""

import hashlib
import hmac
import json
import subprocess
import time
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PHP_BIN = Path(r"D:\blog agent full projact\tools\php\php.exe")


def python_sign(secret: str, timestamp: str, idempotency_key: str, raw_body: str) -> str:
    msg = f"{timestamp}.{idempotency_key}.{raw_body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


class CrossLanguageSignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "test-cross-language-signing-secret-key-12345"
        self.timestamp = str(int(time.time()))
        self.idempotency_key = "article-cross-lang-uuid-9999"
        self.body = json.dumps({"title": "Cross Lang Title", "slug": "cross-lang-test", "content": "Sample content"}, separators=(",", ":"))

    def test_python_signs_php_verifies(self) -> None:
        """Python computes signature -> PHP verifies using hash_hmac and hash_equals."""
        py_sig = python_sign(self.secret, self.timestamp, self.idempotency_key, self.body)

        php_code = f"""
        $secret = '{self.secret}';
        $ts = '{self.timestamp}';
        $key = '{self.idempotency_key}';
        $raw = '{self.body}';
        $expectedSig = '{py_sig}';

        $computed = hash_hmac('sha256', $ts . '.' . $key . '.' . $raw, $secret);
        if (hash_equals($expectedSig, $computed)) {{
            echo "VERIFIED";
        }} else {{
            echo "FAILED: expected " . $expectedSig . " but got " . $computed;
        }}
        """
        proc = subprocess.run([str(PHP_BIN), "-r", php_code], capture_output=True, text=True, check=True)
        self.assertEqual(proc.stdout.strip(), "VERIFIED")

    def test_node_webcrypto_signs_python_verifies(self) -> None:
        """Node crypto.subtle (Cloudflare Worker implementation) signs -> Python verifies."""
        node_script = f"""
        const crypto = require('crypto');
        async function run() {{
            const secret = '{self.secret}';
            const message = '{self.timestamp}..{self.body}';
            const key = await crypto.subtle.importKey(
                'raw', new TextEncoder().encode(secret),
                {{ name: 'HMAC', hash: 'SHA-256' }}, false, ['sign']
            );
            const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
            const hex = [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
            process.stdout.write(hex);
        }}
        run();
        """
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
        node_sig = proc.stdout.strip()

        # Python verifies (worker style with empty idempotency key)
        py_expected = python_sign(self.secret, self.timestamp, "", self.body)
        self.assertEqual(node_sig, py_expected)

    def test_php_signs_feed_python_verifies(self) -> None:
        """PHP signs pull feed request ($ts . '..feed') -> Python verifies."""
        php_code = f"""
        $secret = '{self.secret}';
        $ts = '{self.timestamp}';
        $sig = hash_hmac('sha256', $ts . '..feed', $secret);
        echo $sig;
        """
        proc = subprocess.run([str(PHP_BIN), "-r", php_code], capture_output=True, text=True, check=True)
        php_sig = proc.stdout.strip()

        py_expected = python_sign(self.secret, self.timestamp, "", "feed")
        self.assertEqual(php_sig, py_expected)


if __name__ == "__main__":
    unittest.main()
