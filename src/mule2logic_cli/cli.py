#!/usr/bin/env python3
"""mule2logic CLI — Convert MuleSoft XML flows to Azure Logic Apps Standard workflow JSON.

Usage:
    mule2logic convert <input> [options]
    cat flow.xml | mule2logic convert [options]
"""

from __future__ import annotations

import argparse
import sys

from mule2logic_agent.core.agent import DEFAULT_MODEL, DEFAULT_TIMEOUT
from mule2logic_cli.commands.convert import convert_command


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mule2logic",
        description=(
            "Convert MuleSoft XML flows to Azure Logic Apps Standard "
            "workflow JSON — powered by Microsoft Agent Framework."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 2.0.0",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- convert sub-command ---
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a MuleSoft XML flow to Logic Apps JSON",
    )
    convert_parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to a MuleSoft XML file (omit to read from stdin)",
    )
    convert_parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write JSON to file instead of stdout",
    )
    convert_parser.add_argument(
        "--report",
        metavar="FILE",
        help="Write a migration analysis report (Markdown) to file",
    )
    convert_parser.add_argument(
        "--explain",
        action="store_true",
        help="Include explanation alongside the workflow JSON",
    )
    convert_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )
    convert_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit debug information to stderr",
    )
    convert_parser.add_argument(
        "--debug",
        action="store_true",
        help="Dump the raw agent response to stderr",
    )
    convert_parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Foundry model deployment name (default: {DEFAULT_MODEL})",
    )
    convert_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per agent call in seconds (default: {DEFAULT_TIMEOUT})",
    )
    convert_parser.add_argument(
        "--no-review",
        action="store_true",
        help="Skip the QC review agent step",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "convert":
        convert_command(args)


if __name__ == "__main__":
    main()
