"""A pass-through HTTP proxy in front of an OpenAI-compatible endpoint that logs the timing of every request.

One JSON line per request: client address, start, first byte of the response body, first content token,
end, prompt and completion tokens (from the response `usage` when present) and the number of streamed
chunks. Request and response bodies are never written; the `Authorization` header is forwarded, not logged.

Run: `python -m agent_harness_lab.monitoring.proxy --listen 127.0.0.1:8100 --listen 172.17.0.1:8100
--upstream http://127.0.0.1:8110 --log requests.jsonl` (needs the `monitor` extra).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from aiohttp import ClientSession, ClientTimeout, web

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}


class StreamStats:
    """Reads an SSE or JSON response body incrementally for usage and the first content token."""

    def __init__(self) -> None:
        self.buffer = b""
        self.chunks = 0
        self.first_token: float | None = None
        self.usage: dict[str, Any] | None = None
        self.finish_reason: str | None = None

    def feed(self, data: bytes, now: float) -> None:
        self.buffer += data
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            self._line(line.strip(), now)

    def finish(self, now: float, sse: bool) -> None:
        rest, self.buffer = self.buffer.strip(), b""
        if sse:
            self._line(rest, now)
        elif rest:
            self._json(rest, now, streamed=False)

    def _line(self, line: bytes, now: float) -> None:
        if line.startswith(b"data:"):
            payload = line[5:].strip()
            if payload and payload != b"[DONE]":
                self._json(payload, now, streamed=True)

    def _json(self, payload: bytes, now: float, streamed: bool) -> None:
        try:
            body = json.loads(payload)
        except ValueError:
            return
        if not isinstance(body, dict):
            return
        if streamed:
            self.chunks += 1
        if isinstance(body.get("usage"), dict):
            self.usage = body["usage"]
        for choice in body.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            part = choice.get("delta") if streamed else choice.get("message")
            if isinstance(part, dict) and self.first_token is None and _has_output(part):
                self.first_token = now
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]


def _has_output(part: dict[str, Any]) -> bool:
    return bool(
        part.get("content")
        or part.get("reasoning_content")
        or part.get("reasoning")
        or part.get("tool_calls")
    )


class Proxy:
    def __init__(self, upstream: str, log: Path) -> None:
        self.upstream = upstream.rstrip("/")
        self.log = log.open("a", encoding="utf-8")
        self.in_flight = 0
        self.session: ClientSession | None = None

    async def start(self, app: web.Application) -> None:
        self.session = ClientSession(timeout=ClientTimeout(total=None, sock_read=3600), auto_decompress=False)

    async def stop(self, app: web.Application) -> None:
        if self.session is not None:
            await self.session.close()
        self.log.close()

    async def handle(self, request: web.Request) -> web.StreamResponse:
        if self.session is None:
            raise RuntimeError("proxy not started")
        start = time.time()
        body = await request.read()
        model = stream = None
        if request.content_type == "application/json" and body:
            try:
                parsed = json.loads(body)
                model, stream = parsed.get("model"), parsed.get("stream")
            except (ValueError, AttributeError):
                pass
        self.in_flight += 1
        record: dict[str, Any] = {
            "client": request.remote,
            "method": request.method,
            "path": request.path,
            "model": model,
            "stream": stream,
            "start": start,
            "in_flight_at_start": self.in_flight,
        }
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
        stats = StreamStats()
        response: web.StreamResponse | None = None
        try:
            async with self.session.request(
                request.method, self.upstream + request.path_qs, headers=headers, data=body
            ) as upstream:
                response = web.StreamResponse(
                    status=upstream.status,
                    headers={k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP},
                )
                await response.prepare(request)
                record["status"] = upstream.status
                sse = upstream.content_type == "text/event-stream"
                async for data in upstream.content.iter_any():
                    now = time.time()
                    record.setdefault("first_byte", now)
                    if sse:
                        stats.feed(data, now)
                    else:
                        stats.buffer += data
                    await response.write(data)
                stats.finish(time.time(), sse)
                await response.write_eof()
        except (ConnectionResetError, asyncio.CancelledError) as exc:
            record["error"] = type(exc).__name__
            raise
        except Exception as exc:  # the agent sees a 502; the log keeps the reason
            record["error"] = f"{type(exc).__name__}: {exc}"[:300]
            if response is None:
                response = web.Response(status=502, text="upstream error")
        finally:
            self.in_flight -= 1
            usage = stats.usage or {}
            details = usage.get("prompt_tokens_details") or {}
            record.update(
                end=time.time(),
                first_token=stats.first_token,
                chunks=stats.chunks,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                cached_tokens=details.get("cached_tokens") if isinstance(details, dict) else None,
                finish_reason=stats.finish_reason,
            )
            self.log.write(json.dumps(record) + "\n")
            self.log.flush()
        return response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--listen", action="append", required=True, help="host:port; repeatable")
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    proxy = Proxy(args.upstream, args.log)
    app = web.Application(client_max_size=256 * 1024**2)
    app.on_startup.append(proxy.start)
    app.on_cleanup.append(proxy.stop)
    app.router.add_route("*", "/{tail:.*}", proxy.handle)

    async def serve() -> None:
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        for item in args.listen:
            host, port = item.rsplit(":", 1)
            await web.TCPSite(runner, host, int(port)).start()
        await asyncio.Event().wait()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
