import http.server
import socketserver
import subprocess
import urllib.request
import urllib.error
import time
import sys

CLOUD_RUN_URL = "https://polaris-genai-studio-416490439030.us-central1.run.app"
PORT = 8080

class AuthProxyHandler(http.server.BaseHTTPRequestHandler):
    _cached_token = None
    _token_expiry = 0

    @classmethod
    def get_token(cls):
        now = time.time()
        if cls._cached_token and now < cls._token_expiry:
            return cls._cached_token
        try:
            res = subprocess.run(["gcloud", "auth", "print-identity-token"], capture_output=True, text=True, check=True)
            cls._cached_token = res.stdout.strip()
            cls._token_expiry = now + 1800
            return cls._cached_token
        except Exception as e:
            print(f"Error fetching token via gcloud: {e}", file=sys.stderr)
            return ""

    def do_GET(self):
        self.proxy_request("GET")

    def do_HEAD(self):
        self.proxy_request("HEAD")

    def do_POST(self):
        self.proxy_request("POST")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def proxy_request(self, method):
        target_url = f"{CLOUD_RUN_URL}{self.path}"
        body = None
        if "Content-Length" in self.headers:
            try:
                length = int(self.headers["Content-Length"])
                body = self.rfile.read(length)
            except Exception:
                pass

        headers = {}
        for key, val in self.headers.items():
            if key.lower() not in ["host", "authorization"]:
                headers[key] = val

        token = self.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ["transfer-encoding", "content-encoding"]:
                        self.send_header(k, v)
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ["transfer-encoding", "content-encoding"]:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AuthProxyHandler) as httpd:
        print(f"Cloud Run Auth Proxy serving on http://localhost:{PORT} -> {CLOUD_RUN_URL}", flush=True)
        httpd.serve_forever()
