#!/usr/bin/env python3
"""Serve the CoPE label API from a local llama.cpp server.

The open CoPE classifier (``zentropi-ai/cope-b-a4b``) answers a policy question
with a single token — "1" or "0" — given the prompt its model card specifies.
cope's evaluator client speaks the CoPE label API and the ``reflexes`` package's
OpenAI evaluator speaks chat completions; neither speaks single-token
completion. This shim sits between them and ``llama-server``:

    llama-server --model cope-b-a4b.gguf --port 8090
    python3 scripts/cope_eval_shim.py --port 8099 --upstream http://127.0.0.1:8090

    POST /v1/label             {"content_text", "criteria_text", "model"}
    POST /v1/check             the same endpoint under its other name
    POST /v1/chat/completions  the same judgment, framed as a chat completion
    GET  /v1/health            liveness, and whether the upstream answers

Standard library only, so it runs under a bare ``python3``. One thread per
connection, so a rule set evaluated in parallel is served in parallel.

**It fails loud.** Every caller of this shim fails open — an evaluator that
cannot answer produces no advisory. That only holds while "could not answer" is
distinguishable from "answered 0", so an upstream that is down, slow, or
emitting anything other than a bare 0 or 1 gets a 5xx and a reason, never a
label.

No credentials, anywhere: nothing here reads an ``Authorization`` header and
nothing sends one upstream.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import urlsplit

#: Reported as the confidence when the upstream answered without logprobs. The
#: label is still the model's; nothing in the answer says how sure it was, and
#: this is the sentinel that says so rather than a number pretending to.
NO_LOGPROB_CONFIDENCE = 0.5

#: The health probe is a liveness question, not an evaluation, so it gets its
#: own short deadline instead of the upstream's generous one.
HEALTH_PROBE_TIMEOUT = 2.0

_INSTRUCTION = (
    "Examine the given POLICY and determine if the given CONTENT meets the "
    'criteria for ANY of the LABELS. Answer "1" if yes, and "0" if no.'
)


@dataclass(frozen=True)
class Config:
    upstream: str
    timeout: float


class UpstreamError(Exception):
    """The upstream could not be reached, or did not answer with a label."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class FrameError(Exception):
    """A chat message that does not carry both a POLICY and a CONTENT."""


def build_prompt(policy: str, content: str) -> str:
    """The model card's prompt, verbatim.

    Assembled by interpolation rather than ``str.format``: a policy or a
    rendered tool call carries braces of its own, and a format string would
    either raise on them or substitute them away.
    """
    return f"{_INSTRUCTION}\n\n\nPOLICY\n======\n\n{policy}\n\n\nCONTENT\n=======\n\n{content}"


def classify(config: Config, policy: str, content: str, model: str | None) -> tuple[int, float]:
    """One policy, one tool call, one label — or an ``UpstreamError``."""
    payload: dict[str, object] = {}
    if model:
        payload["model"] = model
    payload.update(
        {
            "messages": [{"role": "user", "content": build_prompt(policy, content)}],
            "max_tokens": 1,
            "temperature": 0,
            "logprobs": True,
            "top_logprobs": 5,
        }
    )
    return _read_label(_post_upstream(config, "/v1/chat/completions", payload))


def _post_upstream(config: Config, path: str, payload: dict[str, object]) -> dict:
    request = urllib.request.Request(
        config.upstream + path,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise UpstreamError(502, f"upstream answered HTTP {exc.code}: {detail}") from exc
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        status = 504 if _is_timeout(exc) else 502
        raise UpstreamError(status, f"upstream did not answer: {exc!r}") from exc
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise UpstreamError(502, f"upstream answered unparseable JSON: {body[:200]!r}") from exc
    if not isinstance(data, dict):
        raise UpstreamError(502, f"upstream answered {type(data).__name__}, not an object")
    return data


def _is_timeout(exc: BaseException) -> bool:
    """A read timeout raises ``TimeoutError``; a connect timeout arrives
    wrapped in ``URLError``. Both are the deadline, and both are a 504."""
    return isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError)


def _read_label(data: dict) -> tuple[int, float]:
    try:
        choice = data["choices"][0]
        answer = (choice["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise UpstreamError(502, f"upstream answer carries no completion: {exc!r}") from exc
    if answer not in ("0", "1"):
        raise UpstreamError(502, f"upstream answered {answer[:200]!r}, which is not a label")
    return int(answer), _confidence(choice)


def _confidence(choice: dict) -> float:
    """``exp(logprob)`` of the token the model actually emitted.

    Clamped to 1.0: a probability above 1 is wrong wherever it came from.
    """
    logprobs = choice.get("logprobs")
    entries = logprobs.get("content") if isinstance(logprobs, dict) else None
    if not isinstance(entries, list) or not entries:
        return NO_LOGPROB_CONFIDENCE
    first = entries[0]
    value = first.get("logprob") if isinstance(first, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return NO_LOGPROB_CONFIDENCE
    return min(1.0, math.exp(value))


# A client frames its question as a ``POLICY:`` line, the policy, a ``CONTENT:``
# line, then the content. The colon, the case, and an underline row are not
# load-bearing; the two marker words are.
_FRAME_MARKER = re.compile(
    r"^[ \t]*(POLICY|CONTENT)[ \t]*:?[ \t]*\n(?:[=-]{2,}[ \t]*\n)?",
    re.IGNORECASE | re.MULTILINE,
)


def split_framed(message: str) -> tuple[str, str]:
    """Pull the policy and the content out of an evaluator's user message.

    With no POLICY there is no policy, and inventing one would answer a
    question nobody asked — so an unframed message is refused, not guessed at.
    """
    policy_at: int | None = None
    for match in _FRAME_MARKER.finditer(message):
        if match.group(1).upper() == "POLICY":
            if policy_at is None:
                policy_at = match.end()
        elif policy_at is not None:
            return message[policy_at : match.start()].strip(), message[match.end() :].strip()
    raise FrameError("the last user message carries no POLICY / CONTENT frame")


def probe_upstream(config: Config) -> str:
    """Whether llama-server is answering, as a phrase.

    Never raises: this shim is up either way, and that is the question
    ``/v1/health`` was asked.
    """
    try:
        with urllib.request.urlopen(
            config.upstream + "/health", timeout=HEALTH_PROBE_TIMEOUT
        ) as response:
            return "ok" if response.status == 200 else f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        return f"unreachable: {exc!r}"


def _required_text(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValueError(f"{field} is required and must be a string")
    return value


def _optional_model(payload: dict) -> str | None:
    model = payload.get("model")
    if model is not None and not isinstance(model, str):
        raise ValueError("model must be a string")
    return model


def _last_user_message(payload: dict) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise ValueError("messages is required and must be a list")
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            text = message.get("content")
            if not isinstance(text, str):
                raise ValueError("the last user message has no text content")
            return text
    raise ValueError("no user message to evaluate")


class _Handler(BaseHTTPRequestHandler):
    server_version = "cope-local-eval"

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        route = _route(self.path)
        if route in ("/v1/label", "/v1/check"):
            self._answer(self._label)
        elif route == "/v1/chat/completions":
            self._answer(self._chat)
        else:
            self._send(404, {"error": f"no such endpoint: {route}"})

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        route = _route(self.path)
        if route != "/v1/health":
            self._send(404, {"error": f"no such endpoint: {route}"})
            return
        config = self._config()
        self._send(
            200,
            {
                "status": "ok",
                "upstream": config.upstream,
                "upstream_health": probe_upstream(config),
            },
        )

    def _config(self) -> Config:
        return cast("_Server", self.server).config

    def _answer(self, action: Callable[[dict], dict]) -> None:
        try:
            body = action(self._read_json())
        except (ValueError, FrameError) as exc:
            self._send(400, {"error": str(exc)})
        except UpstreamError as exc:
            self._send(exc.status, {"error": exc.message})
        else:
            self._send(200, body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw or b"null")
        except ValueError as exc:
            raise ValueError(f"request body is not JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _label(self, payload: dict) -> dict:
        model = _optional_model(payload)
        label, confidence = classify(
            self._config(),
            _required_text(payload, "criteria_text"),
            _required_text(payload, "content_text"),
            model,
        )
        return {"label": label, "confidence": confidence, "explanation": None, "model": model}

    def _chat(self, payload: dict) -> dict:
        policy, content = split_framed(_last_user_message(payload))
        model = _optional_model(payload)
        label, confidence = classify(self._config(), policy, content, model)
        return {
            "id": "chatcmpl-cope-local",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model or "",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({"label": label, "confidence": confidence}),
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _route(path: str) -> str:
    return urlsplit(path).path.rstrip("/") or "/"


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], config: Config) -> None:
        self.config = config
        super().__init__(address, _Handler)


def build_server(host: str, port: int, config: Config) -> _Server:
    """A bound, unstarted server. Pass port 0 for an ephemeral one."""
    return _Server((host, port), config)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the CoPE label API from a local llama.cpp server."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--upstream", required=True, help="base URL of llama-server")
    parser.add_argument(
        "--upstream-timeout",
        type=float,
        default=120.0,
        help="seconds allowed for one upstream completion (default: 120)",
    )
    args = parser.parse_args(argv)

    config = Config(upstream=args.upstream.rstrip("/"), timeout=args.upstream_timeout)
    server = build_server(args.host, args.port, config)
    host, port = server.server_address[0], server.server_address[1]
    print(f"cope-local-eval on http://{host}:{port} -> {config.upstream}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
