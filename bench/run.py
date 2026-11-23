"""Run bench prompts through `claude -p`, each job in its own throwaway HOME.

Every job gets a fresh HOME with only the variant's CLAUDE.md, output style and settings, so
the user's own CLAUDE.md, plugins, hooks and account MCP servers never reach the answer. The
OAuth credentials file is symlinked, not copied: a token refresh in a copy would rotate the
refresh token and log out the real session.

Usage:
    python -m bench.run --variants baseline,current --runs 3 [--label NAME] [--jobs 4]
                        [--only 01-fact,05-debug]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
WORK_ROOT = Path.home() / ".cache" / "claude-output-style" / "jobs"
REAL_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
EMPTY_MCP = '{"mcpServers":{}}'
TURN_TIMEOUT_S = 600
ATTEMPTS = 2

_credentials_lock = threading.Lock()


@dataclass(frozen=True)
class Variant:
    """One configuration under test."""

    name: str
    claude_md: Path | None
    style: Path | None
    system_prompt: Path | None
    settings: dict[str, Any] = field(default_factory=dict)


def _resolve(raw: str | None, repo: Path) -> Path | None:
    if raw is None:
        return None
    path = Path(raw).expanduser()
    path = path if path.is_absolute() else repo / path
    if not path.is_file():
        raise FileNotFoundError(f"variant file not found: {path}")
    return path


def load_variants(config: Path, names: list[str], repo: Path = REPO) -> list[Variant]:
    """Load the named variants from a variants.json, in the order requested.

    Args:
        config: Path to variants.json.
        names: Variant names to load.
        repo: Base for relative file paths.

    Returns:
        Resolved variants.

    Raises:
        ValueError: A name is not defined in the config.
        FileNotFoundError: A file referenced by a requested variant does not exist.
    """
    data = json.loads(config.read_text(encoding="utf-8"))
    base = data.get("settings", {})
    defined = data["variants"]
    variants = []
    for name in names:
        if name not in defined:
            raise ValueError(f"unknown variant: {name} (have: {', '.join(defined)})")
        spec = defined[name]
        variants.append(
            Variant(
                name=name,
                claude_md=_resolve(spec.get("claude_md"), repo),
                style=_resolve(spec.get("style"), repo),
                system_prompt=_resolve(spec.get("system_prompt"), repo),
                settings={**base, **spec.get("settings", {})},
            )
        )
    return variants


def style_name(path: Path) -> str:
    """Return the output style name from YAML frontmatter, or the file stem."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            if key.strip() == "name" and value.strip():
                return value.strip().strip("\"'")
    return path.stem


def build_settings(variant: Variant) -> dict[str, Any]:
    """Settings passed via --settings for this variant."""
    settings = dict(variant.settings)
    if variant.style:
        settings["outputStyle"] = style_name(variant.style)
    return settings


def build_command(prompt: str, variant: Variant, resume: str | None) -> list[str]:
    """Build the `claude -p` argv.

    The prompt goes right after ``-p`` because ``--tools`` and ``--mcp-config`` are variadic
    and would swallow a trailing positional argument.
    """
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--strict-mcp-config",
        "--mcp-config",
        EMPTY_MCP,
        "--tools",
        "",
        "--settings",
        json.dumps(build_settings(variant), ensure_ascii=False),
    ]
    if variant.system_prompt:
        cmd += ["--system-prompt-file", str(variant.system_prompt)]
    if resume:
        cmd += ["--resume", resume]
    return cmd


def make_home(job_dir: Path, variant: Variant, credentials: Path) -> tuple[Path, Path]:
    """Create an isolated HOME and working directory for one job.

    Returns:
        ``(home, cwd)``.
    """
    home = job_dir / "home"
    cwd = job_dir / "cwd"
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True)
    cwd.mkdir(parents=True)
    (claude_dir / ".credentials.json").symlink_to(credentials)
    if variant.claude_md:
        shutil.copyfile(variant.claude_md, claude_dir / "CLAUDE.md")
    if variant.style:
        (claude_dir / "output-styles").mkdir()
        shutil.copyfile(variant.style, claude_dir / "output-styles" / variant.style.name)
    trust = {
        "hasCompletedOnboarding": True,
        "projects": {str(cwd): {"hasTrustDialogAccepted": True}},
    }
    (home / ".claude.json").write_text(json.dumps(trust), encoding="utf-8")
    return home, cwd


def sync_credentials(home: Path, credentials: Path) -> str | None:
    """Copy a refreshed token back if claude replaced the symlink with a real file.

    Returns:
        A warning when the real credentials file was updated, else None.
    """
    link = home / ".claude" / ".credentials.json"
    if link.is_symlink() or not link.is_file():
        return None
    with _credentials_lock:
        fresh = link.read_bytes()
        if credentials.exists() and credentials.read_bytes() == fresh:
            return None
        tmp = credentials.with_name(f".credentials.{uuid.uuid4().hex}.tmp")
        tmp.write_bytes(fresh)
        tmp.chmod(0o600)
        os.replace(tmp, credentials)
    return f"credentials were refreshed inside {home}; copied back to {credentials}"


def clean_env(home: Path) -> dict[str, str]:
    """Environment for the child: no Claude/Anthropic variables, HOME pointed at the job."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ANTHROPIC_"))}
    env["HOME"] = str(home)
    return env


def parse_turn(prompt: str, stdout: str) -> dict[str, Any]:
    """Extract the fields we keep from `claude -p --output-format json` output.

    Raises:
        ValueError: stdout is not the expected JSON object.
    """
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not json: {stdout[:300]!r}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"unexpected json: {stdout[:300]!r}")
    return {
        "prompt": prompt,
        "result": data.get("result") or "",
        "session_id": data.get("session_id"),
        "is_error": bool(data.get("is_error")),
        "output_tokens": (data.get("usage") or {}).get("output_tokens"),
        "duration_ms": data.get("duration_ms"),
        "num_turns": data.get("num_turns"),
    }


@dataclass(frozen=True)
class Job:
    """One prompt, one variant, one repetition."""

    variant: Variant
    prompt_id: str
    turns: list[str]
    run: int
    out_path: Path


def _attempt(job: Job, credentials: Path) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    job_dir = WORK_ROOT / f"{job.variant.name}-{job.prompt_id}-r{job.run}-{uuid.uuid4().hex[:8]}"
    warnings: list[str] = []
    turns: list[dict[str, Any]] = []
    try:
        home, cwd = make_home(job_dir, job.variant, credentials)
        env = clean_env(home)
        resume = None
        for prompt in job.turns:
            proc = subprocess.run(
                build_command(prompt, job.variant, resume),
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=TURN_TIMEOUT_S,
                check=False,
            )
            if warning := sync_credentials(home, credentials):
                warnings.append(warning)
            if proc.returncode != 0:
                return turns, f"exit {proc.returncode}: {proc.stderr[-500:]}", warnings
            turn = parse_turn(prompt, proc.stdout)
            turns.append(turn)
            if turn["is_error"] or not turn["result"]:
                return turns, f"error result: {turn['result'][:300]!r}", warnings
            resume = turn["session_id"]
        return turns, None, warnings
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        return turns, f"{type(exc).__name__}: {exc}", warnings
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def run_job(job: Job, credentials: Path = REAL_CREDENTIALS) -> tuple[str | None, list[str]]:
    """Run one job with a retry and write its raw result file.

    Returns:
        ``(error, warnings)``; error is None on success.
    """
    error: str | None = None
    warnings: list[str] = []
    turns: list[dict[str, Any]] = []
    for _ in range(ATTEMPTS):
        turns, error, attempt_warnings = _attempt(job, credentials)
        warnings += attempt_warnings
        if error is None:
            break
    job.out_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "variant": job.variant.name,
        "prompt_id": job.prompt_id,
        "run": job.run,
        "settings": build_settings(job.variant),
        "turns": turns,
        "error": error,
    }
    job.out_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return error, warnings


def _done(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("error") is None
    except json.JSONDecodeError:
        return False


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    parser.add_argument("--variants", required=True, help="comma-separated variant names")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--label", default=datetime.now().strftime("%Y%m%d-%H%M"))
    parser.add_argument("--only", default="", help="comma-separated prompt ids")
    args = parser.parse_args(argv)

    if not REAL_CREDENTIALS.is_file():
        print(f"no credentials at {REAL_CREDENTIALS}; log in with `claude` first", file=sys.stderr)
        return 1
    variants = load_variants(REPO / "bench" / "variants.json", args.variants.split(","))
    prompts = json.loads((REPO / "bench" / "prompts.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        prompts = [p for p in prompts if p["id"] in wanted]

    results = REPO / "bench" / "results" / args.label
    jobs = [
        Job(v, p["id"], p["turns"], n, results / "raw" / v.name / f"{p['id']}-r{n}.json")
        for n in range(1, args.runs + 1)
        for v in variants
        for p in prompts
    ]
    pending = [j for j in jobs if not _done(j.out_path)]
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=False)
    results.mkdir(parents=True, exist_ok=True)
    (results / "meta.json").write_text(
        json.dumps(
            {
                "claude_version": version.stdout.strip(),
                "started": datetime.now().isoformat(timespec="seconds"),
                "runs": args.runs,
                "variants": {v.name: build_settings(v) for v in variants},
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"{len(pending)} of {len(jobs)} jobs to run -> {results}", flush=True)

    failed = 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_job, j): j for j in pending}
        for k, future in enumerate(as_completed(futures), 1):
            job = futures[future]
            error, warnings = future.result()
            failed += error is not None
            status = "ok" if error is None else f"FAIL {error[:200]}"
            elapsed = time.monotonic() - started
            print(
                f"[{k}/{len(pending)} {elapsed:.0f}s] {job.variant.name}/{job.prompt_id}"
                f"/r{job.run} {status}",
                flush=True,
            )
            for warning in warnings:
                print(f"  WARNING {warning}", flush=True)
    print(f"done, {failed} failed. Next: python -m bench.metrics {results}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
