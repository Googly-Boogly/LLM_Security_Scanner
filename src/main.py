"""LLM Security Scanner entry point.

All configuration is read from the .env file (or environment variables).
Copy .env.example to .env, fill in your values, then run:

    python -m src.main
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime

from rich.console import Console

from src.config import settings
from src.llm_client import LLMClient, LLMConfig
from src.probes import Category, get_probes
from src.report import ReportGenerator
from src.scanner import Scanner

console = Console()

VALID_CATEGORIES = [c.value for c in Category]
VALID_PROVIDERS = ["anthropic", "openai", "google"]


async def async_main() -> int:
    # Validate provider
    if settings.llm_provider not in VALID_PROVIDERS:
        console.print(f"[red]Unknown provider '{settings.llm_provider}'. Valid: {VALID_PROVIDERS}[/red]")
        return 1

    # Parse and validate categories
    raw_cats = [c.strip().lower() for c in settings.categories.split(",") if c.strip()]
    invalid = [c for c in raw_cats if c not in VALID_CATEGORIES]
    if invalid:
        console.print(f"[red]Unknown categories: {invalid}. Valid: {VALID_CATEGORIES}[/red]")
        return 1

    categories = [Category(c) for c in raw_cats]
    probes = get_probes(categories)
    if not probes:
        console.print("[yellow]No probes matched the specified categories.[/yellow]")
        return 0

    # Build LLM clients
    target_config = LLMConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )
    judge_model = settings.judge_model or settings.llm_model
    judge_config = LLMConfig(
        provider=settings.llm_provider,
        model=judge_model,
        api_key=settings.llm_api_key,
    )

    target_client = LLMClient(target_config)
    judge_client = LLMClient(judge_config)

    # Print scan header
    console.print()
    console.rule("[bold cyan]LLM Security Scanner[/bold cyan]")
    console.print(f"  [bold]Target:[/bold]  {settings.llm_provider} / {settings.llm_model}")
    console.print(f"  [bold]Judge:[/bold]   {settings.llm_provider} / {judge_model}")
    console.print(f"  [bold]Probes:[/bold]  {len(probes)} across {len(categories)} category/ies")
    console.print(f"  [bold]System:[/bold]  {settings.system_prompt[:60]}...")
    console.rule()
    console.print()

    with console.status("[bold green]Running probes...[/bold green]", spinner="dots"):
        scanner = Scanner(
            target=target_client,
            judge=judge_client,
            default_system_prompt=settings.system_prompt,
            concurrency=settings.concurrency,
        )
        results = await scanner.run(probes)

    reporter = ReportGenerator(console=console)
    reporter.print_terminal(results)

    output_path = settings.output or f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    reporter.save_json(results, output_path)
    console.print(f"[dim]Full results saved to: {output_path}[/dim]")

    any_vuln = any(r.compromised for r in results)
    return 1 if any_vuln else 0


def main() -> None:
    sys.exit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
