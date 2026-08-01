"""Reflexes evaluator client — the qualitative judgment behind cope's advisory.

cope asks a small language model whether a tool call matches a rule. The
question, the answer shape, and the error semantics are the Reflexes evaluator
contract (SPEC.md §4; see plugins/rbg/README.md for where to find it): given a
``policy`` (the rule's own markdown, frontmatter stripped) and ``content`` (the
tool call), return a ``label`` of 0 or 1, optionally with a ``confidence`` and a
reason. One policy, one verdict — so a match names the rule it matched, which is
the whole point of the advisory.

Two wire protocols are supported, chosen by ``COPE_EVALUATOR_PROTOCOL``:

``cope``
    The CoPE label API: ``POST`` with ``{"content_text", "criteria_text",
    "model"}``, answering ``{"label", "confidence", "explanation"}``. Spoken by
    the hosted service and by a self-hosted CoPE server alike — the model is
    open-weights, so "remote API" and "local inference" are the same protocol
    pointed at different hosts.

``openai``
    Any OpenAI-compatible ``/v1/chat/completions`` server — Ollama, vLLM,
    LocalAI, llama.cpp, or a hosted provider. The classifier instruction lives
    in ``messages/classifier-prompt.md``; the model answers with the same
    ``{"label", "confidence"}`` JSON object.

No host, model name, or credential is compiled in. Absent configuration is not
an error — it is cope's tool-call evaluation being switched off, and the caller
gets ``None``.

**Fail-open, always.** This runs in front of every tool call. A dead socket,
a slow endpoint, a 500, a body that will not parse — none of them
produce a verdict, and per SPEC §4.3 an evaluator error is not ``label=0``, so
none of them produce an advisory either. They are reported and the tool call
proceeds untouched. There are no retries: a retry in this position multiplies
the stall the agent is waiting through.

A misconfiguration (``_note``) is reported on stderr on every occurrence — it
is a mistake someone made and is rare enough that repetition costs little. An
evaluator that was configured correctly but could not be reached is different:
it can recur on every single tool call for a session's whole duration, so
``claim_outage_once`` rate-limits that specific case to one hook response per
session; see ``handlers.evaluate``. A session with nothing configured is not a
degraded one, and stays silent either way — see ``resolve``.

The whole check runs inside one deadline. Two things enforce it, because either
alone leaks: the remaining budget is passed down as the socket timeout, so no
request outlives it, and the pool is shut down without waiting, so a transport
that ignores its timeout cannot hold up the response either.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from dispatch import load_message_pair

#: Where the once-per-session outage marker lives, under
#: ``tempfile.gettempdir()``. Plugin-local by design — see ``claim_outage_once``.
_OUTAGE_MARKER_DIR = "aops-rbg-evaluator-outage"

#: Wire protocols ``COPE_EVALUATOR_PROTOCOL`` accepts.
PROTOCOLS = ("cope", "openai")

#: Someone configured an evaluator and it did not come out usable — a missing
#: variable, a protocol that is not one of ours, an unreadable timeout.
DEGRADED_CONFIG = "cope-config"

#: A configured evaluator could not answer, so the rules it was asked about
#: went unchecked.
DEGRADED_EVALUATOR = "cope-evaluator"


def claim_outage_once(session_id: str) -> bool:
    """True for exactly one hook process in this session; every other call
    for the same session gets ``False``.

    An unreachable evaluator can recur on every tool call for a session's
    whole duration, so the outage is worth naming to the agent and the person
    watching exactly once — see ``handlers.evaluate``, the only caller. One
    hook invocation is one process, so the gate cannot live in memory; it is a
    zero-length marker file per session, claimed with ``O_CREAT | O_EXCL``
    under the directory the OS names for temporary files. No path is compiled
    in, and the marker name is a digest so a session id read from the payload
    can never name a path of its own.

    A failure to claim and an already-claimed marker are the same answer on
    purpose: both mean this process does not speak, and the stderr line
    (``handlers.evaluate``) has already been written either way. A session id
    that is empty or missing can never claim — an unbounded notice would be
    worse than the stderr line by itself.
    """
    if not session_id:
        return False
    try:
        root = Path(tempfile.gettempdir()) / _OUTAGE_MARKER_DIR
        root.mkdir(parents=True, exist_ok=True)
        marker = root / hashlib.sha256(session_id.encode()).hexdigest()[:32]
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except OSError:
        return False


#: Ceiling on the whole evaluation, in seconds, when ``COPE_EVALUATOR_TIMEOUT``
#: is unset. Every rule is evaluated inside this one budget, so it is the
#: longest a tool call can be held up — not a per-request allowance.
DEFAULT_TIMEOUT_SECONDS = 5.0

#: How many rules are evaluated at once. Rules are independent, so they go in
#: parallel; the cap keeps a large rule set from opening a socket per rule.
MAX_CONCURRENCY = 8

#: Longest rendered tool input sent to the evaluator. A Write carries its whole
#: file body, which is neither affordable nor necessary to judge the call.
MAX_CONTENT_CHARS = 4000

#: Everything a failed evaluation can raise on its way back: transport,
#: protocol, and every shape a response can be wrong in. All of them are the
#: same outcome — no verdict — and none of them may escape into dispatch.
_EVALUATION_ERRORS = (
    urllib.error.URLError,
    OSError,
    TimeoutError,
    ValueError,  # includes json.JSONDecodeError
    KeyError,
    IndexError,
    TypeError,
    AttributeError,
)


@dataclass(frozen=True)
class Config:
    url: str
    protocol: str
    model: str
    api_key: str | None
    timeout: float


@dataclass(frozen=True)
class Verdict:
    slug: str
    label: int
    confidence: float | None
    reason: str | None


@dataclass(frozen=True)
class EvalOutcome:
    """One rule's result from one ``check()`` sweep — matched, clean, or failed.

    ``check()``'s own return is a *view* of these built for the advisory: only
    the matches, and only the failures as strings. A trace sink sees every one
    of them, which is the point of it existing — a false positive and a true
    negative are equally load-bearing tuning data, and a view that already
    dropped one of them cannot be reconstructed from downstream.

    ``label`` and ``error`` are mutually exclusive: a successful call carries a
    label and no error; a failed or timed-out one carries an error and no
    label, confidence, or reason. ``latency_s`` is always populated — for a
    cancelled (timed-out) call it is the budget it was cancelled at, an upper
    bound on the wait rather than a measurement of the call itself, since a
    cancelled future never reports how long the server actually took.
    """

    slug: str
    label: int | None
    confidence: float | None
    reason: str | None
    error: str | None
    latency_s: float


#: Claude Code exports every declared ``userConfig`` option into a hook's
#: environment as ``CLAUDE_PLUGIN_OPTION_<KEY>``, where ``<KEY>`` is the option
#: key uppercased (Claude Code plugins reference, "User configuration"). cope's
#: hook command is shell form, which rejects ``${user_config.*}`` substitution
#: outright, so this is the only route a userConfig value can take to get here.
#: The option keys in manifest/plugin.template.json are named so that
#: uppercasing one yields exactly the plain variable below — one lookup rule
#: covers both paths, and tests/test_cope.py pins the two names together.
_PLUGIN_OPTION_PREFIX = "CLAUDE_PLUGIN_OPTION_"


def _note(message: str) -> None:
    """One configuration mistake, to the log and to the person who made it.

    Every caller is a value someone set and meant to work. Nothing set at all
    never reaches here — that is ``resolve`` returning ``None`` in silence.

    stderr, not stdout: stdout is the hook's JSON response channel, and a
    print here would corrupt it.
    """
    print(f"DEGRADED: cope: {message}", file=sys.stderr)


def _setting(name: str) -> str:
    """One configuration value: the plugin option first, then the plain variable.

    Claude Code ignores the ``pluginConfigs`` block — the settings key a
    ``userConfig`` answer is recorded under — when it appears in a project's
    ``.claude/settings.json`` or ``.claude/settings.local.json``, a restriction
    documented as a security measure and specific to ``pluginConfigs`` rather
    than to settings generally (Claude Code plugins reference, "User
    configuration"). Both those files live in the workspace, so a cloned
    repository cannot supply one. That makes it the more trustworthy of the two
    sources, and it wins. The plain environment variable is the fallback that
    agy and container sessions rely on, neither of which has userConfig at all.
    """
    for key in (_PLUGIN_OPTION_PREFIX + name, name):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def resolve() -> Config | None:
    """Read the evaluator configuration from the environment.

    Returns ``None`` when cope has no evaluator to talk to. Two different
    silences, deliberately distinguished:

    - Nothing set at all — cope's tool-call evaluation is simply not switched
      on for this session. Silent: an unconfigured session is a legitimate
      state, and a line on every tool call would be noise, not information.
    - Some of it set — a misconfiguration someone meant to work. It is reported
      once, naming what is missing, then cope stays out of the way. Guessing
      the missing value is exactly the default this plugin may not have.

    This is the line everything else in the plugin follows for what is worth
    reporting: absence nobody asked for is silent, intent that did not land is
    not.
    """
    url = _setting("COPE_EVALUATOR_URL")
    protocol = _setting("COPE_EVALUATOR_PROTOCOL")
    model = _setting("COPE_EVALUATOR_MODEL")
    api_key = _setting("COPE_EVALUATOR_API_KEY") or None

    if not (url or protocol or model):
        return None

    missing = [
        name
        for name, value in (
            ("COPE_EVALUATOR_URL", url),
            ("COPE_EVALUATOR_PROTOCOL", protocol),
            ("COPE_EVALUATOR_MODEL", model),
        )
        if not value
    ]
    if missing:
        _note(f"evaluator partially configured; {', '.join(missing)} unset — not evaluating")
        return None

    if protocol not in PROTOCOLS:
        _note(
            f"COPE_EVALUATOR_PROTOCOL={protocol!r} is not one of "
            f"{', '.join(PROTOCOLS)} — not evaluating"
        )
        return None

    return Config(url=url, protocol=protocol, model=model, api_key=api_key, timeout=_timeout())


def _timeout() -> float:
    raw = _setting("COPE_EVALUATOR_TIMEOUT")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        _note(f"COPE_EVALUATOR_TIMEOUT={raw!r} is not a number; using {DEFAULT_TIMEOUT_SECONDS}s")
        return DEFAULT_TIMEOUT_SECONDS
    if value <= 0:
        _note(f"COPE_EVALUATOR_TIMEOUT={raw!r} is not positive; using {DEFAULT_TIMEOUT_SECONDS}s")
        return DEFAULT_TIMEOUT_SECONDS
    return value


def _post(config: Config, payload: dict, timeout: float) -> dict:
    # The URL is operator configuration, never a value from the session or the
    # tool call — nothing an agent does can redirect where this posts.
    request = urllib.request.Request(
        config.url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    if config.api_key:
        request.add_header("Authorization", f"Bearer {config.api_key}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError(f"evaluator returned {type(parsed).__name__}, not an object")
    return parsed


def _as_confidence(value: object) -> float | None:
    """Narrow a decoded JSON value to a confidence, or reject it.

    The Reflexes contract makes ``confidence`` optional and does not pin its
    JSON type, so this is a genuine boundary: the value is whatever a remote
    server chose to send. Narrowing before converting is the point — a blanket
    conversion would turn ``{"confidence": {}}`` into a TypeError from inside
    ``float()`` rather than a stated reason, and ``check()`` would report the
    failure as an unhelpful ``TypeError(...)``.

    ``bool`` is rejected explicitly because it is a subclass of ``int``: a
    ``true`` confidence would otherwise silently become ``1.0``, the maximum
    value, which is the worst possible thing to invent.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"confidence must be a number, got {value!r}")
    return float(value)


def _label_call(
    config: Config, policy: str, content: str, timeout: float
) -> tuple[int, float | None, str | None]:
    """The CoPE label API: one policy, one classification."""
    data = _post(
        config,
        {"content_text": content, "criteria_text": policy, "model": config.model},
        timeout,
    )
    return int(data["label"]), _as_confidence(data.get("confidence")), data.get("explanation")


def _chat_call(
    config: Config, policy: str, content: str, timeout: float, system_prompt: str
) -> tuple[int, float | None, str | None]:
    """An OpenAI-compatible chat completion, read back as the same verdict."""
    data = _post(
        config,
        {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"POLICY:\n{policy}\n\nCONTENT:\n{content}"},
            ],
            "temperature": 0,
            "max_tokens": 256,
        },
        timeout,
    )
    raw = data["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"evaluator answered with {type(parsed).__name__}, not an object")
    return int(parsed["label"]), _as_confidence(parsed.get("confidence")), None


def check(
    config: Config,
    policies: list[tuple[str, str]],
    content: str,
    hooks_dir: Path,
    *,
    on_outcome: Callable[[EvalOutcome], None] | None = None,
) -> tuple[list[Verdict], list[str]]:
    """Evaluate ``content`` against every ``(slug, policy_text)`` in parallel.

    Returns the matching verdicts (``label == 1``) and a list of human-readable
    failures. A failure is never a match: an evaluator that could not answer
    has said nothing, so the tool call proceeds.

    ``on_outcome``, when given, is called once per policy with an
    ``EvalOutcome`` — matched, clean, or failed alike — as each one finishes.
    It is the research trace's whole hook into this function and changes
    nothing about the return value: existing callers that ignore it see no
    behavioural difference. A callback that raises is not this function's
    failure to carry, so it is never allowed to interrupt a sweep — see the
    call sites below.
    """
    if not policies:
        return [], []

    system_prompt = (
        load_message_pair(hooks_dir, "classifier-prompt")[0] if config.protocol == "openai" else ""
    )
    deadline = time.monotonic() + config.timeout

    def _emit(outcome: EvalOutcome) -> None:
        if on_outcome is None:
            return
        try:
            on_outcome(outcome)
        except Exception:  # noqa: BLE001 - a trace sink must never break the sweep it traces
            pass

    def run(slug: str, policy: str) -> Verdict:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"budget of {config.timeout}s spent before {slug} was evaluated")
        started = time.monotonic()
        try:
            if config.protocol == "cope":
                label, confidence, reason = _label_call(config, policy, content, remaining)
            else:
                label, confidence, reason = _chat_call(
                    config, policy, content, remaining, system_prompt
                )
        except _EVALUATION_ERRORS as exc:
            _emit(EvalOutcome(slug, None, None, None, repr(exc), time.monotonic() - started))
            raise
        _emit(EvalOutcome(slug, label, confidence, reason, None, time.monotonic() - started))
        return Verdict(slug=slug, label=label, confidence=confidence, reason=reason)

    matches: list[Verdict] = []
    failures: list[str] = []

    pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENCY)
    try:
        futures = {pool.submit(run, slug, policy): slug for slug, policy in policies}
        _, pending = wait(futures, timeout=max(deadline - time.monotonic(), 0))
        for future in pending:
            future.cancel()
            slug = futures[future]
            failures.append(f"{slug}: no answer within the {config.timeout}s budget")
            # Cancelled before run() could report its own outcome (or before it
            # was ever scheduled) — traced here so a timed-out rule is not
            # silently missing from the record. latency_s is the budget it was
            # cancelled at, not a measurement of the call itself: see EvalOutcome.
            _emit(
                EvalOutcome(
                    slug, None, None, None, "no answer within the timeout budget", config.timeout
                )
            )
        for future, slug in futures.items():
            if future in pending:
                continue
            try:
                verdict = future.result()
            except _EVALUATION_ERRORS as exc:
                failures.append(f"{slug}: {exc!r}")
                continue
            if verdict.label == 1:
                matches.append(verdict)
    finally:
        # Never wait: the budget above is the promise, and a transport that
        # ignores its own timeout must not be able to extend it.
        pool.shutdown(wait=False, cancel_futures=True)

    matches.sort(key=lambda verdict: verdict.slug)
    return matches, failures


def render_content(tool: str, tool_input: object) -> str:
    """The tool call, as the text the evaluator judges."""
    if isinstance(tool_input, (dict, list)):
        rendered = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    else:
        rendered = "" if tool_input is None else str(tool_input)
    if len(rendered) > MAX_CONTENT_CHARS:
        rendered = rendered[:MAX_CONTENT_CHARS] + " …[truncated]"
    return f"Tool: {tool}\nInput: {rendered}"
