"""
Scheduler — Automated airdrop scanning with configurable intervals.
"""

import asyncio
import time
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class ScanScheduler:
    """Manages periodic scan execution."""

    def __init__(self, scan_fn, deep_scan_fn=None, interval_minutes: int = 30):
        self.scan_fn = scan_fn
        self.deep_scan_fn = deep_scan_fn
        self.interval_minutes = interval_minutes
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def setup(self):
        """Configure scheduled jobs."""
        # Regular scan every N minutes
        self.scheduler.add_job(
            self._safe_scan,
            IntervalTrigger(minutes=self.interval_minutes),
            id="regular_scan",
            name="Regular Airdrop Scan"
        )

        # Deep scan daily at 2 AM UTC
        if self.deep_scan_fn:
            self.scheduler.add_job(
                self._safe_deep_scan,
                "cron",
                hour=2, minute=0,
                id="deep_scan",
                name="Deep Airdrop Scan"
            )

    async def start(self):
        """Start the scheduler."""
        self.setup()
        self.scheduler.start()
        self._running = True
        print(f"[Scheduler] Started — scanning every {self.interval_minutes}min")

    async def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        self._running = False
        print("[Scheduler] Stopped")

    async def _safe_scan(self):
        """Execute scan with error handling."""
        start = time.time()
        try:
            await self.scan_fn()
            duration = int((time.time() - start) * 1000)
            print(f"[Scheduler] Scan completed in {duration}ms")
        except Exception as e:
            print(f"[Scheduler] Scan error: {e}")

    async def _safe_deep_scan(self):
        """Execute deep scan with error handling."""
        start = time.time()
        try:
            await self.deep_scan_fn()
            duration = int((time.time() - start) * 1000)
            print(f"[Scheduler] Deep scan completed in {duration}ms")
        except Exception as e:
            print(f"[Scheduler] Deep scan error: {e}")

    @property
    def is_running(self) -> bool:
        return self._running
