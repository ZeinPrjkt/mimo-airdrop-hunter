"""
MiMo Airdrop Hunter — Main Entry Point

Usage:
    python -m hunter.main --scan          # Single scan
    python -m hunter.main --full          # Scan + analyze + notify
    python -m hunter.main --daemon        # Continuous scheduler mode
    python -m hunter.main --stats         # Show statistics
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from hunter.scanner import AirdropScanner
from hunter.analyzer import MiMoAnalyzer
from hunter.notifier import TelegramNotifier
from hunter.database import AirdropDB, init_db
from hunter.scheduler import ScanScheduler


console = Console()


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        console.print("[red]Config not found![/red] Copy config.example.yaml → config.yaml")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


async def run_scan(config: dict, analyze: bool = False, notify: bool = False):
    """Execute full scan pipeline."""
    start_time = time.time()
    db = AirdropDB()

    console.print(Panel("🔍 Starting Airdrop Scan", style="bold cyan"))

    # 1. Initialize scanner
    scanner = AirdropScanner(config["chains"])

    # 2. Run scan
    console.print("  [dim]Scanning chains...[/dim]")
    signals = await scanner.scan_all()
    console.print(f"  [green]✓ Found {len(signals)} signals[/green]")

    for sig in signals[:5]:
        console.print(f"    • {sig.name} ({sig.chain}) — {sig.description[:60]}")

    if not analyze:
        await scanner.close()
        return signals

    # 3. Analyze with MiMo
    analyzer = MiMoAnalyzer(
        api_key=config["mimo"]["api_key"],
        base_url=config["mimo"].get("base_url", "https://api.xiaomimimo.com/v1"),
        model=config["mimo"].get("model", "MiMo-V2.5-Reasoning")
    )

    wallet = config["wallets"][0]["address"]
    active_chains = [c["name"] for c in config["chains"]]

    console.print("  [dim]Analyzing with MiMo AI...[/dim]")

    signal_dicts = [s.to_dict() for s in signals[:10]]  # Limit to 10
    analyses = await analyzer.batch_analyze(
        signal_dicts,
        wallet_address=wallet,
        active_chains=active_chains,
        past_interactions={}  # TODO: load from DB
    )

    # 4. Save to database
    for analysis, signal in zip(analyses, signals[:10]):
        await db.save_analysis(analysis, signal)

    duration_ms = int((time.time() - start_time) * 1000)
    for chain in active_chains:
        await db.log_scan(chain, len(signals), duration_ms)

    # 5. Display results
    display_results(analyses)

    # 6. Notify
    if notify and config.get("telegram"):
        notifier = TelegramNotifier(
            bot_token=config["telegram"]["bot_token"],
            chat_id=config["telegram"]["chat_id"]
        )
        high_priority = [a for a in analyses if a.priority == "HIGH"]
        if high_priority:
            await notifier.send_batch_alert(high_priority, wallet)
            console.print(f"  [green]✓ Sent {len(high_priority)} alerts to Telegram[/green]")
        else:
            stats = await db.get_stats()
            await notifier.send_status(stats, datetime.now(timezone.utc).strftime("%H:%M UTC"))
        await notifier.close()

    await scanner.close()
    await analyzer.close()

    console.print(f"\n[dim]Completed in {duration_ms}ms[/dim]")
    return analyses


def display_results(analyses):
    """Display analysis results in a table."""
    table = Table(title="🎯 Airdrop Analysis Results", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Chain")
    table.add_column("Score", justify="center")
    table.add_column("Value")
    table.add_column("Priority")
    table.add_column("Action", max_width=40)

    priority_colors = {
        "HIGH": "bold red",
        "MEDIUM": "yellow",
        "LOW": "dim",
        "SKIP": "strike dim",
    }

    for a in sorted(analyses, key=lambda x: x.overall_score, reverse=True):
        color = priority_colors.get(a.priority, "")
        table.add_row(
            a.name,
            a.chain,
            f"{a.overall_score}/100",
            a.estimated_value_usd,
            f"[{color}]{a.priority}[/{color}]",
            a.action_required[:40] + "..." if len(a.action_required) > 40 else a.action_required
        )

    console.print(table)


async def show_stats(config: dict):
    """Show database statistics."""
    db = AirdropDB()
    stats = await db.get_stats()

    console.print(Panel(
        f"📊 Total: {stats['total']} | "
        f"🔥 High: {stats['high_priority']} | "
        f"📨 Notified: {stats['notified']}",
        title="Airdrop Hunter Stats"
    ))


async def daemon_mode(config: dict):
    """Run in continuous scheduler mode."""
    console.print(Panel("🤖 MiMo Airdrop Hunter — Daemon Mode", style="bold magenta"))

    interval = config.get("scheduler", {}).get("scan_interval_minutes", 30)

    async def scan_job():
        await run_scan(config, analyze=True, notify=True)

    scheduler = ScanScheduler(
        scan_fn=scan_job,
        interval_minutes=interval
    )

    await scheduler.start()

    # Run initial scan immediately
    await run_scan(config, analyze=True, notify=True)

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        await scheduler.stop()
        console.print("[dim]Daemon stopped[/dim]")


def main():
    parser = argparse.ArgumentParser(description="MiMo Airdrop Hunter")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--scan", action="store_true", help="Run single scan")
    parser.add_argument("--full", action="store_true", help="Scan + analyze + notify")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon with scheduler")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    if args.stats:
        config = load_config(args.config)
        asyncio.run(show_stats(config))
    elif args.daemon:
        config = load_config(args.config)
        asyncio.run(init_db())
        asyncio.run(daemon_mode(config))
    elif args.full:
        config = load_config(args.config)
        asyncio.run(init_db())
        asyncio.run(run_scan(config, analyze=True, notify=True))
    elif args.scan:
        config = load_config(args.config)
        asyncio.run(run_scan(config, analyze=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
