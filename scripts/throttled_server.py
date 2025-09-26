#!/usr/bin/env python3
"""
Throttled HTTP server for local download testing.

- Serves files from a directory with bandwidth limits and optional latency.
"""

import argparse
import http.server
import os
import socketserver
import threading
import time
from functools import partial


class ThrottledHandler(http.server.SimpleHTTPRequestHandler):
    # Bytes per second and artificial latency in seconds
    rate_limit_bps = 256 * 1024  # default 256 KB/s
    initial_latency_s = 0.2      # default 200 ms

    def copyfile(self, source, outputfile):
        # Initial latency to simulate slow start/handshake
        if self.initial_latency_s > 0:
            time.sleep(self.initial_latency_s)

        chunk_size = 32 * 1024  # 32 KB chunks
        sleep_per_chunk = chunk_size / max(1, self.rate_limit_bps)

        while True:
            data = source.read(chunk_size)
            if not data:
                break
            outputfile.write(data)
            outputfile.flush()
            if sleep_per_chunk > 0:
                time.sleep(sleep_per_chunk)


def serve(directory: str, port: int, rate_kbps: int, latency_ms: int):
    handler = partial(ThrottledHandler, directory=directory)
    ThrottledHandler.rate_limit_bps = max(1, rate_kbps) * 1024
    ThrottledHandler.initial_latency_s = max(0, latency_ms) / 1000.0

    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Throttled server on http://127.0.0.1:{port} dir={directory} rate={rate_kbps}KB/s latency={latency_ms}ms")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="Run a throttled HTTP server")
    parser.add_argument("--dir", default="test_files", help="Directory to serve")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    parser.add_argument("--rate", type=int, default=256, help="Rate limit in KB/s")
    parser.add_argument("--latency", type=int, default=200, help="Initial latency in ms")
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    serve(args.dir, args.port, args.rate, args.latency)


if __name__ == "__main__":
    main()


