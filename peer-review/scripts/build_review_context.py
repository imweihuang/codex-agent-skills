#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


BLOCKED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "var",
    "logs",
    "__pycache__",
}

BLOCKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.prod",
    ".env.development",
    ".envrc",
    ".vault-token",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "known_hosts",
    "terraform.tfvars",
    "terraform.tfstate",
    "terraform.tfstate.backup",
}

BLOCKED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".log",
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".tfvars",
    ".tfstate",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bghp_[0-9A-Za-z]{30,}\b"),
    re.compile(r"\bgithub_pat_[0-9A-Za-z_]{60,}\b"),
    re.compile(r"\bsk-(?:proj-|ant-)?[0-9A-Za-z_-]{32,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|password)\b"
        r"\s*[:=]\s*['\"]?[0-9A-Za-z_./+=-]{24,}"
    ),
]


def positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().replace("_", "")
    try:
        value = int(normalized)
    except ValueError:
        print(f"[context-builder] invalid {name}={raw!r}; using default {default}", file=sys.stderr)
        return default
    if value <= 0:
        print(f"[context-builder] invalid {name}={raw!r}; using default {default}", file=sys.stderr)
        return default
    return value


def main() -> int:
    default_max_bytes_per_file = positive_int_env("PEER_REVIEW_MAX_BYTES_PER_FILE", 100_000)
    default_max_total_bytes = positive_int_env("PEER_REVIEW_MAX_TOTAL_BYTES", 1_000_000)

    parser = argparse.ArgumentParser(
        description="Build a safe text context bundle for external peer review.",
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to include.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--allow-untracked", action="store_true", help="Allow explicitly selected untracked files.")
    parser.add_argument(
        "--allow-non-git-context",
        action="store_true",
        help="Allow context building outside a git repository. Use only after inspecting selected paths.",
    )
    parser.add_argument(
        "--allow-secret-like-content",
        action="store_true",
        help="Allow files whose contents match common secret/token patterns.",
    )
    parser.add_argument("--list", action="store_true", help="List selected files instead of printing file contents.")
    parser.add_argument("--max-bytes-per-file", type=int, default=default_max_bytes_per_file)
    parser.add_argument("--max-total-bytes", type=int, default=default_max_total_bytes)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    tracked = git_tracked_files(root)
    if tracked is None:
        print(
            "[context-builder] ERROR: git ls-files unavailable; refusing non-git context by default. "
            "Pass --allow-non-git-context only after inspecting selected paths.",
            file=sys.stderr,
        )
        if not args.allow_non_git_context:
            return 2
    candidates = collect_candidates(root, args.paths, tracked, args.allow_untracked)

    if args.list:
        for path in candidates:
            if not is_blocked(path, root):
                print(display_path(path, root))
        return 0

    written = 0
    for index, path in enumerate(candidates):
        if written >= args.max_total_bytes:
            omitted = [display_path(item, root) for item in candidates[index:] if not is_blocked(item, root)]
            sys.stdout.write(
                "\n===== CONTEXT OMITTED =====\n"
                f"Total byte limit reached at {args.max_total_bytes}; "
                f"{len(omitted)} candidate file(s) were not included.\n"
            )
            for rel in omitted[:20]:
                sys.stdout.write(f"- {rel}\n")
            if len(omitted) > 20:
                sys.stdout.write(f"- ... {len(omitted) - 20} more\n")
            print(
                "[context-builder] total byte limit reached at "
                f"{args.max_total_bytes}; narrow the selected paths or raise "
                "--max-total-bytes / PEER_REVIEW_MAX_TOTAL_BYTES for a targeted review",
                file=sys.stderr,
            )
            break
        if is_blocked(path, root):
            print(f"[context-builder] skipped blocked path: {display_path(path, root)}", file=sys.stderr)
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"[context-builder] skipped unreadable path {display_path(path, root)}: {exc}", file=sys.stderr)
            continue
        if b"\x00" in data:
            print(f"[context-builder] skipped binary path: {display_path(path, root)}", file=sys.stderr)
            continue
        secret_match = find_secret_like_content(data)
        if secret_match and not args.allow_secret_like_content:
            print(
                "[context-builder] ERROR: possible secret-like content in "
                f"{display_path(path, root)} ({secret_match}); refusing to build context. "
                "Remove/redact the value or pass --allow-secret-like-content after inspection.",
                file=sys.stderr,
            )
            return 3

        truncated = len(data) > args.max_bytes_per_file
        if truncated:
            data = data[: args.max_bytes_per_file]

        remaining = args.max_total_bytes - written
        if len(data) > remaining:
            data = data[:remaining]
            truncated = True

        rel = display_path(path, root)
        sys.stdout.write(f"\n===== {rel} =====\n")
        sys.stdout.write(data.decode("utf-8", errors="replace"))
        if truncated:
            sys.stdout.write("\n[TRUNCATED]\n")
        if not data.endswith(b"\n"):
            sys.stdout.write("\n")
        written += len(data)

    return 0


def git_tracked_files(root: Path) -> set[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def collect_candidates(root: Path, raw_paths: list[str], tracked: set[Path] | None, allow_untracked: bool) -> list[Path]:
    selected: list[Path] = []
    seen: set[Path] = set()

    for raw in raw_paths:
        path = (root / raw).resolve()
        if not is_relative_to(path, root):
            print(f"[context-builder] skipped outside-root path: {raw}", file=sys.stderr)
            continue
        if not path.exists():
            print(f"[context-builder] skipped missing path: {raw}", file=sys.stderr)
            continue
        for candidate in expand_path(root, path, tracked):
            if tracked is not None and candidate not in tracked and not allow_untracked:
                print(f"[context-builder] skipped untracked path: {display_path(candidate, root)}", file=sys.stderr)
                continue
            if tracked is not None and candidate not in tracked and allow_untracked:
                print(
                    f"[context-builder] WARNING: including untracked file: {display_path(candidate, root)}",
                    file=sys.stderr,
                )
            if candidate not in seen:
                selected.append(candidate)
                seen.add(candidate)

    return selected


def expand_path(root: Path, path: Path, tracked: set[Path] | None) -> list[Path]:
    if path.is_file():
        return [path]
    if tracked is not None:
        return sorted(item for item in tracked if is_relative_to(item, path) and item.is_file())
    return sorted(item for item in path.rglob("*") if item.is_file() and not is_blocked(item, root))


def is_blocked(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.resolve().relative_to(root).parts
    except ValueError:
        return True
    name = path.name
    lower_name = name.lower()
    return (
        any(part in BLOCKED_PARTS for part in rel_parts)
        or lower_name in BLOCKED_NAMES
        or lower_name.startswith(".env.")
        or path.suffix.lower() in BLOCKED_SUFFIXES
    )


def find_secret_like_content(data: bytes) -> str | None:
    text = data.decode("utf-8", errors="ignore")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return pattern.pattern[:80]
    return None


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
