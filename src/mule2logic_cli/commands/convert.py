"""Convert command — orchestrates the conversion pipeline via the agent package."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from mule2logic_agent.core.io import read_input
from mule2logic_agent.core.prompt import build_prompt
from mule2logic_agent.core.validate import validate_json, validate_workflow_structure
from mule2logic_agent.models import ConvertRequest
from mule2logic_agent.service import convert
from mule2logic_cli.display import (
    Spinner,
    bold,
    cyan,
    dim,
    green,
    red,
    stop_all_spinners,
    yellow,
)


def convert_command(args: Any) -> None:
    """Entry-point called by the CLI argument parser."""
    try:
        asyncio.run(_convert_async(args))
    except KeyboardInterrupt:
        stop_all_spinners()
        print(f"\n{red('✖')} {red('Cancelled')}", file=sys.stderr)
        sys.exit(130)


async def _convert_async(args: Any) -> None:
    try:
        print(
            bold("\n🔄 mule2logic") + dim(" — MuleSoft → Azure Logic Apps\n"),
            file=sys.stderr,
        )

        # 1. Load input
        if args.verbose:
            print("[verbose] Loading input...", file=sys.stderr)
        spinner1 = Spinner(dim("Reading MuleSoft XML..."))
        xml = await read_input(args.input)
        spinner1.stop(
            f"{green('✔')} {bold('Input loaded')} {dim(f'({len(xml)} chars)')}"
        )

        # 2. Build prompt (for verbose display only)
        prompt = build_prompt(xml)
        if args.verbose:
            print("[verbose] Prompt:\n" + prompt, file=sys.stderr)
        print(f"{green('✔')} {bold('Prompt built')}", file=sys.stderr)

        model = args.model
        timeout = args.timeout
        if args.verbose:
            print(f"[verbose] Using model: {model}", file=sys.stderr)
            print(f"[verbose] Timeout: {timeout}s", file=sys.stderr)

        # 3. Call the agent service (the full pipeline)
        spinner3 = Spinner(
            f"{yellow('Calling Foundry Agent')} {dim('(this may take a moment...)')}"
        )
        start_time = time.monotonic()

        request = ConvertRequest(
            xml=xml,
            model=model,
            timeout=timeout,
            verbose=args.verbose,
            skip_review=args.no_review,
            include_explanation=args.explain,
            generate_report=bool(args.report),
        )

        result = await convert(request)
        elapsed = f"{time.monotonic() - start_time:.1f}"
        spinner3.stop(
            f"{green('✔')} {bold('Agent responded')} {dim(f'({elapsed}s)')}"
        )

        if args.debug:
            print(
                f"\n{cyan('━━━ Raw Agent Response ━━━')}",
                file=sys.stderr,
            )
            print(result.raw_response, file=sys.stderr)
            print(f"{cyan('━━━ End Raw Response ━━━')}\n", file=sys.stderr)

        # Display validation / review status
        print(f"{green('✔')} {bold('Output validated')}", file=sys.stderr)

        if not args.no_review:
            if result.review_issues:
                issue_count = len(result.review_issues)
                print(
                    f"{yellow('⚠')}  {bold('Review complete')} "
                    f"— {issue_count} issue(s) remain",
                    file=sys.stderr,
                )
                if args.verbose:
                    for issue in result.review_issues:
                        print(f"{dim('   •')} {issue}", file=sys.stderr)
            else:
                print(
                    f"{green('✔')} {bold('QC review passed')}",
                    file=sys.stderr,
                )
        else:
            print(dim("⏭  Review skipped (--no-review)"), file=sys.stderr)

        # 4. Format output
        if args.explain:
            output: dict[str, Any] = {
                "workflow": result.workflow,
                "explanation": result.raw_response,
            }
        else:
            output = result.workflow

        json_string = (
            json.dumps(output, indent=2) if args.pretty else json.dumps(output)
        )

        # 5. Write output
        if args.output:
            Path(args.output).write_text(json_string, encoding="utf-8")
            print(
                f"{green('✔')} {bold('Written to')} {cyan(args.output)}",
                file=sys.stderr,
            )
        else:
            print(json_string)

        # 6. Write migration report
        if args.report and result.report:
            Path(args.report).write_text(result.report, encoding="utf-8")
            print(
                f"{green('✔')} {bold('Report written to')} {cyan(args.report)}",
                file=sys.stderr,
            )

        print(f"\n{green('🎉 Conversion complete!')}\n", file=sys.stderr)

    except Exception as exc:
        stop_all_spinners()
        print(f"\n{red('✖')} {red('Error:')} {exc}", file=sys.stderr)
        sys.exit(1)
