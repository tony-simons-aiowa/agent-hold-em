"""A tiny local fake OpenAI-compatible HTTP server (stdlib `http.server` only).

Used by `scripts/probe_runtime.py` (the offline real-`AIAgent` probe) and by
`tests/controller/conftest.py` (the integration test fixture) — one implementation,
so the probe's evidence and the test suite exercise the exact same server.

Handles `POST /v1/chat/completions` (both `stream: false` JSON and `stream: true`
SSE — verified: the chat_completions wire path streams by default, see
docs/CONTRACT.md) and `GET /v1/models`. Every received request body is recorded
(`server.requests`) so a caller can assert on `tools`, message content, etc.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

__all__ = ["FakeOpenAIServer", "ReplyPlan"]


@dataclass
class ReplyPlan:
    """What the fake server should do for the NEXT `/v1/chat/completions` request."""

    content: str = '{"action": "check"}'
    delay_s: float = 0.0  # sleep before responding (simulate a slow provider)
    http_status: int = 200  # e.g. 500 to simulate a provider error
    error_body: Optional[dict] = None  # sent verbatim as the JSON body when http_status != 200
    malformed: bool = False  # send truncated/invalid JSON instead of a well-formed completion


class _Handler(BaseHTTPRequestHandler):
    server: "FakeOpenAIServer"  # type: ignore[assignment]

    def log_message(self, format: str, *args: Any) -> None:  # silence stdlib access logs
        pass

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            return {"_raw": raw.decode("utf-8", "replace")}

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        if self.path.startswith("/v1/models"):
            body = json.dumps({"object": "list", "data": [{"id": "fake-model", "object": "model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        body = self._read_body()
        with self.server.lock:
            self.server.requests.append(body)
            plan = self.server.next_reply
        if not self.path.startswith("/v1/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return

        if plan.delay_s:
            # Sleep in small slices so an interrupted client (connection closed) is noticed
            # promptly rather than after the full delay.
            slept = 0.0
            step = 0.02
            while slept < plan.delay_s:
                time.sleep(step)
                slept += step

        if plan.http_status != 200:
            payload = plan.error_body or {"error": {"message": "simulated provider error", "type": "server_error"}}
            data = json.dumps(payload).encode()
            self.send_response(plan.http_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        wants_stream = bool(body.get("stream"))
        content = "{not-json" if plan.malformed else plan.content

        if not wants_stream:
            resp = _completion_response(content)
            data = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # SSE stream: one content-delta chunk, then a finish-reason chunk, then [DONE].
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for chunk in _stream_chunks(content):
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client (agent) disconnected — expected on an interrupted call


def _completion_response(content: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-fake", "object": "chat.completion", "created": int(time.time()),
        "model": "fake-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49},
    }


def _stream_chunks(content: str) -> list[dict[str, Any]]:
    base = {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": int(time.time()), "model": "fake-model"}
    return [
        {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}]},
        {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49}},
    ]


class FakeOpenAIServer(ThreadingHTTPServer):
    """Start with `FakeOpenAIServer().start()`; stop with `.stop()`. `base_url` is ready to hand
    straight to `AIAgent(base_url=..., api_mode="chat_completions", provider="custom")`."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.lock = threading.Lock()
        self.requests: list[dict[str, Any]] = []
        self.next_reply = ReplyPlan()
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/v1"

    def set_reply(self, plan: ReplyPlan) -> None:
        with self.lock:
            self.next_reply = plan

    def start(self) -> "FakeOpenAIServer":
        self._thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.shutdown()
        self.server_close()
        if self._thread:
            self._thread.join(timeout=5.0)

    def last_request(self) -> Optional[dict[str, Any]]:
        with self.lock:
            return self.requests[-1] if self.requests else None
