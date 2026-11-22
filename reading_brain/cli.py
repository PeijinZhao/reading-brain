"""Command-line interface for Milestone 0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit_source_directory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reading-brain-audit",
        description=(
            "Parse WeRead Markdown files in read-only mode and export a normalized "
            "evidence dataset plus an audit report."
        ),
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Directory containing WeRead Markdown files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory for audit.json and JSONL exports (default: ./output).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Parse only the first N discovered files for a dry run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        print("错误：--limit 必须是正整数。", file=sys.stderr)
        return 2

    try:
        report = audit_source_directory(args.source, args.output, limit=args.limit)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"未预期的错误：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    summary = {
        "files_discovered": report.files_discovered,
        "files_parsed": report.files_parsed,
        "files_failed": report.files_failed,
        "entries_exported": report.entries_exported,
        "highlights": report.highlights_exported,
        "thoughts": report.thoughts_exported,
        "reviews": report.reviews_exported,
        "popular_highlights": report.popular_highlights_exported,
        "unknown_entries": report.unknown_entries_exported,
        "warnings": report.warnings_total,
        "duplicate_entry_ids": len(report.duplicate_entry_ids),
        "output_directory": args.output.expanduser().resolve().as_posix(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report.files_failed == 0 else 3

if __name__ == "__main__":
    raise SystemExit(main())