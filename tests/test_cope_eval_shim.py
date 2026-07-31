"""Tests for the local CoPE evaluator shim (scripts/cope_eval_shim.py).

The shim's whole job is translation: the CoPE label API on one side, a
single-token llama.cpp completion on the other. So the assertions are about the
two wires — the prompt that goes upstream is the model card's, byte for byte,
and what comes back is a label with the confidence the model actually reported,
or a loud failure. Never a quiet 0: every caller of this shim fails open, which
only works while "could not answer" and "answered 0" are different answers.

Everything runs over real loopback HTTP against a stub llama-server, because a
patched call would prove nothing about a shim whose entire surface is HTTP.
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
# The CoPE client now ships in the rbg plugin — `plugins/cope/` was renamed to
# `plugins/rbg/` in e3a8bd39/8edff6fa. The evaluator module, its `Config`, and
# its `check()` are the same surface under the new directory.
_RBG_HOOKS = _REPO_ROOT / "plugins" / "rbg" / "hooks"

for _dir in (_REPO_ROOT / "scripts", _REPO_ROOT / "lib" / "hooks", _RBG_HOOKS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import evaluator  # noqa: E402  (plugins/rbg/hooks/evaluator.py)
from cope_eval_shim import NO_LOGPROB_CONFIDENCE, Config, build_server  # noqa: E402

# The CoPE-B model card's prompt, written out here rather than imported: a
# golden copy that shares its source with the code under test is not a golden
# copy. Change this only when the model card changes.
_POLICY = "Never bypass a pre-commit hook."
_CONTENT = 'Tool: Bash\nInput: {"command": "git commit --no-verify -m x"}'
_GOLDEN_PROMPT = (
    'Examine the given POLICY and determine if the given CONTENT meets the criteria for ANY of the LABELS. Answer "1" if yes, and "0" if no.\n'
    "\n"
    "\n"
    "POLICY\n"
    "======\n"
    "\n"
    "Never bypass a pre-commit hook.\n"
    "\n"
    "\n"
    "CONTENT\n"
    "=======\n"
    "\n"
    'Tool: Bash\nInput: {"command": "git commit --no-verify -m x"}'
)

# A port nothing listens on — the upstream-is-down case, without the wait.
_DEAD_UPSTREAM = "http://127.0.0.1:1"


# ---------------------------------------------------------------------------
# A loopback llama-server
# ---------------------------------------------------------------------------


class _Upstream:
    """What the stub will say, and what it was asked."""

    def __init__(self) -> None:
        self.seen: list[dict] = []
        self.url = ""
        self.answer = "1"
        self.logprob = -0.02
        self.logprobs = True
        self.status = 200
        self.delay = 0.0
        self.healthy = True

    def completion(self, model: str) -> dict:
        choice: dict = {
            "index": 0,
            "message": {"role": "assistant", "content": self.answer},
            "finish_reason": "length",
        }
        if self.logprobs:
            choice["logprobs"] = {"content": [{"token": self.answer, "logprob": self.logprob}]}
        return {
            "id": "chatcmpl-stub",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [choice],
        }


class _UpstreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        stub = self.server.stub
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length))
        stub.seen.append(
            {
                "path": self.path,
                "payload": payload,
                "auth": self.headers.get("Authorization"),
            }
        )
        if stub.delay:
            time.sleep(stub.delay)
        if stub.status != 200:
            self._send(stub.status, {"error": "upstream is unwell"})
            return
        self._send(200, stub.completion(payload.get("model", "")))

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        stub = self.server.stub
        self._send(200 if stub.healthy else 503, {"status": "ok" if stub.healthy else "loading"})

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the default stderr access log
        pass


class _UpstreamServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, stub: _Upstream) -> None:
        self.stub = stub
        super().__init__(("127.0.0.1", 0), _UpstreamHandler)

    def handle_error(self, request, client_address):
        """The timeout test hangs up on a request still being answered. That
        broken pipe is the test working; anything else still gets a traceback."""
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


@pytest.fixture()
def upstream():
    stub = _Upstream()
    server = _UpstreamServer(stub)
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield stub
    server.shutdown()
    server.server_close()


@pytest.fixture()
def shim(upstream):
    """Starts the shim under test; returns its base URL."""
    servers = []

    def start(upstream_url: str | None = None, timeout: float = 10.0) -> str:
        config = Config(upstream=upstream_url or upstream.url, timeout=timeout)
        server = build_server("127.0.0.1", 0, config)
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def _post(url: str, payload: dict, *, headers: dict | None = None, timeout: float = 10.0):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    request.add_header("Content-Type", "application/json")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _get(url: str, timeout: float = 10.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _label_request() -> dict:
    return {"content_text": _CONTENT, "criteria_text": _POLICY, "model": "cope-b-a4b"}


# ---------------------------------------------------------------------------
# POST /v1/label
# ---------------------------------------------------------------------------


def test_label_one_carries_the_confidence_the_model_reported(upstream, shim):
    upstream.answer = "1"
    upstream.logprob = -0.02
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status == 200
    assert body["label"] == 1
    assert body["confidence"] == pytest.approx(math.exp(-0.02))
    assert body["explanation"] is None
    assert body["model"] == "cope-b-a4b"


def test_label_zero_is_a_verdict_of_its_own(upstream, shim):
    upstream.answer = "0"
    upstream.logprob = -0.5
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status == 200
    assert body["label"] == 0
    assert body["confidence"] == pytest.approx(math.exp(-0.5))


def test_the_prompt_sent_upstream_is_the_model_cards_prompt_verbatim(upstream, shim):
    """The one thing this shim must get exactly right. The content carries
    braces, as every rendered tool call does — a format-string template would
    have blown up here or eaten them."""
    status, _ = _post(shim() + "/v1/label", _label_request())
    assert status == 200

    assert len(upstream.seen) == 1
    request = upstream.seen[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["payload"] == {
        "model": "cope-b-a4b",
        "messages": [{"role": "user", "content": _GOLDEN_PROMPT}],
        "max_tokens": 1,
        "temperature": 0,
        "logprobs": True,
        "top_logprobs": 5,
    }


def test_check_is_the_same_endpoint_under_its_other_name(upstream, shim):
    status, body = _post(shim() + "/v1/check", _label_request())
    assert status == 200
    assert body["label"] == 1
    assert upstream.seen[0]["payload"]["messages"][0]["content"] == _GOLDEN_PROMPT


def test_no_logprobs_reports_the_sentinel_rather_than_inventing_a_number(upstream, shim):
    upstream.logprobs = False
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status == 200
    assert body["label"] == 1
    assert body["confidence"] == NO_LOGPROB_CONFIDENCE


def test_copes_own_client_accepts_what_the_shim_answers(upstream, shim):
    """The contract the shim exists to satisfy, proved against the real client
    in plugins/rbg/hooks/evaluator.py rather than against a reading of it: a
    verdict comes back, with a confidence, and nothing is reported as failed."""
    config = evaluator.Config(
        url=shim() + "/v1/label",
        protocol="cope",
        model="cope-b-a4b",
        api_key=None,
        timeout=10.0,
    )
    matches, failures = evaluator.check(config, [("no-verify", _POLICY)], _CONTENT, _RBG_HOOKS)

    assert failures == []
    assert [verdict.slug for verdict in matches] == ["no-verify"]
    assert matches[0].label == 1
    assert matches[0].confidence == pytest.approx(math.exp(-0.02))
    assert upstream.seen[0]["payload"]["messages"][0]["content"] == _GOLDEN_PROMPT


def test_no_credential_reaches_the_upstream(upstream, shim):
    """The shim needs no auth and forwards none: an Authorization header it is
    handed is not a credential it may spend."""
    status, _ = _post(
        shim() + "/v1/label",
        _label_request(),
        headers={"Authorization": "Bearer should-not-travel"},
    )
    assert status == 200
    assert upstream.seen[0]["auth"] is None


# ---------------------------------------------------------------------------
# Failure is loud
# ---------------------------------------------------------------------------


def test_a_non_binary_answer_is_an_error_not_a_zero(upstream, shim):
    """The load-bearing failure. A model that answered in prose has not said
    'no', and the caller's fail-open only works if it can tell the difference."""
    upstream.answer = "The content appears to violate the policy."
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status >= 500
    assert "label" not in body
    assert "not a label" in body["error"]


def test_an_empty_answer_is_an_error(upstream, shim):
    upstream.answer = ""
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status >= 500
    assert "label" not in body


def test_an_upstream_error_status_is_an_error(upstream, shim):
    upstream.status = 500
    status, body = _post(shim() + "/v1/label", _label_request())

    assert status >= 500
    assert "label" not in body
    assert "HTTP 500" in body["error"]


def test_an_upstream_that_is_not_listening_is_an_error(shim):
    status, body = _post(shim(upstream_url=_DEAD_UPSTREAM) + "/v1/label", _label_request())

    assert status >= 500
    assert "label" not in body
    assert "did not answer" in body["error"]


def test_an_upstream_that_is_too_slow_is_an_error(upstream, shim):
    upstream.delay = 1.5
    status, body = _post(shim(timeout=0.25) + "/v1/label", _label_request())

    assert status == 504
    assert "label" not in body


def test_a_request_missing_its_policy_is_refused(upstream, shim):
    status, body = _post(shim() + "/v1/label", {"content_text": _CONTENT})

    assert status == 400
    assert "criteria_text" in body["error"]
    assert upstream.seen == [], "an unusable request reached the model anyway"


def test_an_unknown_endpoint_is_a_404(shim):
    status, body = _post(shim() + "/v1/labels", _label_request())
    assert status == 404
    assert "error" in body


# ---------------------------------------------------------------------------
# POST /v1/chat/completions
# ---------------------------------------------------------------------------


def _chat_request(message: str) -> dict:
    return {
        "model": "cope-b-a4b",
        "messages": [
            {"role": "system", "content": "You are a policy classifier."},
            {"role": "user", "content": message},
        ],
        "temperature": 0,
        "max_tokens": 512,
    }


def test_chat_completions_answers_in_the_shape_an_openai_client_parses(upstream, shim):
    """cope's `openai` protocol and reflexes' OpenAI evaluator both read
    `choices[0].message.content` and json.loads it."""
    upstream.logprob = -0.1
    framed = f"POLICY:\n{_POLICY}\n\nCONTENT:\n{_CONTENT}"
    status, body = _post(shim() + "/v1/chat/completions", _chat_request(framed))

    assert status == 200
    assert body["object"] == "chat.completion"
    assert body["model"] == "cope-b-a4b"
    choice = body["choices"][0]
    assert choice["message"]["role"] == "assistant"

    verdict = json.loads(choice["message"]["content"])
    assert verdict["label"] == 1
    assert verdict["confidence"] == pytest.approx(math.exp(-0.1))


def test_chat_completions_rebuilds_the_same_cope_prompt(upstream, shim):
    framed = f"POLICY:\n{_POLICY}\n\nCONTENT:\n{_CONTENT}"
    status, _ = _post(shim() + "/v1/chat/completions", _chat_request(framed))

    assert status == 200
    assert upstream.seen[0]["payload"]["messages"][0]["content"] == _GOLDEN_PROMPT
    assert upstream.seen[0]["payload"]["max_tokens"] == 1


def test_chat_completions_reads_the_frame_whatever_its_punctuation(upstream, shim):
    framed = f"policy\n------\n{_POLICY}\n\ncontent\n{_CONTENT}"
    status, _ = _post(shim() + "/v1/chat/completions", _chat_request(framed))

    assert status == 200
    assert upstream.seen[0]["payload"]["messages"][0]["content"] == _GOLDEN_PROMPT


def test_chat_completions_refuses_an_unframed_message_rather_than_guess(upstream, shim):
    status, body = _post(shim() + "/v1/chat/completions", _chat_request("is this tool call fine?"))

    assert status == 400
    assert "POLICY" in body["error"]
    assert upstream.seen == [], "a message with no policy was classified against something"


# ---------------------------------------------------------------------------
# GET /v1/health
# ---------------------------------------------------------------------------


def test_health_reports_a_reachable_upstream(upstream, shim):
    status, body = _get(shim() + "/v1/health")

    assert status == 200
    assert body["status"] == "ok"
    assert body["upstream"] == upstream.url
    assert body["upstream_health"] == "ok"


def test_health_is_still_ok_when_the_upstream_is_down(shim):
    """The shim is up; the model is not. Two different facts, both reported."""
    status, body = _get(shim(upstream_url=_DEAD_UPSTREAM) + "/v1/health")

    assert status == 200
    assert body["status"] == "ok"
    assert body["upstream_health"].startswith("unreachable")


def test_health_reports_an_upstream_that_is_not_ready(upstream, shim):
    upstream.healthy = False
    status, body = _get(shim() + "/v1/health")

    assert status == 200
    assert body["upstream_health"] == "HTTP 503"


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_sixteen_simultaneous_evaluations_are_all_answered_in_parallel(upstream, shim):
    """cope evaluates a rule set in parallel, so this shim is asked in
    parallel. Serialised, these sixteen would take sixteen delays."""
    upstream.delay = 0.2
    url = shim() + "/v1/label"
    results: list[tuple[int, dict]] = []
    lock = threading.Lock()

    def ask() -> None:
        outcome = _post(url, _label_request(), timeout=20.0)
        with lock:
            results.append(outcome)

    started = time.monotonic()
    threads = [threading.Thread(target=ask) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    elapsed = time.monotonic() - started

    assert len(results) == 16
    assert all(status == 200 for status, _ in results)
    assert all(body["label"] == 1 for _, body in results)
    assert len(upstream.seen) == 16
    assert elapsed < 16 * upstream.delay / 2, f"served serially: {elapsed:.2f}s"
