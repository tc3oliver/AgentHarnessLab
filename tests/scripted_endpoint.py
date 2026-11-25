"""A scripted OpenAI-compatible server for integration tests. It is not a model.

The first request of a conversation gets one bash tool call; once a tool result is in the history the server
ends the conversation. It exercises a real harness's installation, endpoint wiring, tools and tokens.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MODEL = "scripted/model"
KEY = "scripted-key"
USAGE = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}


def _tool_call(body: dict[str, Any], command: str) -> dict[str, Any] | None:
    """Fill the shell tool's required arguments, whatever the harness calls them."""
    for tool in body.get("tools") or []:
        fn = tool["function"]
        if fn["name"] in {"bash", "shell"}:
            required = fn["parameters"].get("required", [])
            args = {name: command if name == "command" else "run a command" for name in required}
            args["command"] = command
            return {
                "index": 0,
                "id": "call_1",
                "type": "function",
                "function": {"name": fn["name"], "arguments": json.dumps(args)},
            }
    return None


class ScriptedEndpoint:
    def __init__(self, host: str, command: str = "true", status: int = 200) -> None:
        self.command, self.status = command, status
        self.requests: list[dict[str, Any]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None: ...

            def _json(self, status: int, body: object) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _authorized(self) -> bool:
                if self.headers.get("Authorization") == f"Bearer {KEY}":
                    return True
                self._json(401, {"error": {"message": "unauthorized"}})
                return False

            def do_GET(self) -> None:
                if not self._authorized():
                    return
                if self.path == "/v1/models":
                    self._json(200, {"data": [{"id": MODEL}]})
                elif self.path == "/version":
                    self._json(200, {"version": "scripted"})
                else:
                    self._json(404, {})

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if not self._authorized():
                    return
                outer.requests.append({"path": self.path, **body})
                if self.path != "/v1/chat/completions":
                    return self._json(404, {"error": {"message": "only chat completions"}})
                if body["model"] != MODEL:  # as vLLM does
                    return self._json(404, {"error": {"message": f"no model {body['model']}"}})
                if outer.status != 200:
                    return self._json(outer.status, {"error": {"message": "scripted failure"}})
                done = any(m["role"] == "tool" for m in body["messages"])
                call = None if done else _tool_call(body, outer.command)
                message = {"role": "assistant", "content": None if call else "Done."}
                if call:
                    message["tool_calls"] = [call]  # type: ignore[assignment]
                finish = "tool_calls" if call else "stop"
                base = {"id": "c", "created": 0, "model": body["model"]}
                if not body.get("stream"):
                    choice = {"index": 0, "message": message, "finish_reason": finish}
                    return self._json(
                        200, {**base, "object": "chat.completion", "choices": [choice], "usage": USAGE}
                    )
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for choices, usage in (
                    ([{"index": 0, "delta": message, "finish_reason": None}], None),
                    ([{"index": 0, "delta": {}, "finish_reason": finish}], None),
                    ([], USAGE),
                ):
                    chunk = {**base, "object": "chat.completion.chunk", "choices": choices, "usage": usage}
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")

        self._server = ThreadingHTTPServer((host, 0), Handler)
        self.url = f"http://{host}:{self._server.server_address[1]}/v1"

    def __enter__(self) -> ScriptedEndpoint:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args: object) -> None:
        self._server.shutdown()
        self._server.server_close()
