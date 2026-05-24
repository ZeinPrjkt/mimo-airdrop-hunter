"""
SQLite Database — Persists airdrop opportunities, analysis results, and alerts.
"""

import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "airdrops.db"


async def init_db(db_path: str = None):
    """Initialize database with schema."""
    path = db_path or str(DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS airdrops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chain TEXT NOT NULL,
                contract_address TEXT,
                description TEXT,
                source TEXT,
                legitimacy_score INTEGER,
                eligibility_score INTEGER,
                overall_score INTEGER,
                estimated_value TEXT,
                priority TEXT,
                action_required TEXT,
                risk_flags TEXT,
                reasoning TEXT,
                status TEXT DEFAULT 'detected',
                detected_at TEXT,
                analyzed_at TEXT,
                notified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallet_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                chain TEXT NOT NULL,
                protocol TEXT NOT NULL,
                interaction_type TEXT,
                tx_hash TEXT,
                block_number INTEGER,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT NOT NULL,
                signals_found INTEGER DEFAULT 0,
                scan_duration_ms INTEGER,
                scanned_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


class AirdropDB:
    """Database operations for airdrop data."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)

    async def save_analysis(self, analysis, signal=None):
        """Save MiMo analysis result to database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO airdrops
                (name, chain, contract_address, description, source,
                 legitimacy_score, eligibility_score, overall_score,
                 estimated_value, priority, action_required, risk_flags,
                 reasoning, detected_at, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.name,
                analysis.chain,
                signal.contract_address if signal else None,
                signal.description if signal else None,
                signal.source if signal else None,
                analysis.legitimacy_score,
                analysis.eligibility_score,
                analysis.overall_score,
                analysis.estimated_value_usd,
                analysis.priority,
                analysis.action_required,
                json.dumps(analysis.risk_flags),
                analysis.reasoning,
                signal.detected_at if signal else None,
                datetime.now(timezone.utc).isoformat(),
            ))
            await db.commit()

    async def get_recent(self, limit: int = 20) -> list[dict]:
        """Get recent airdrop analyses."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM airdrops ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_by_priority(self, priority: str) -> list[dict]:
        """Get airdrops by priority level."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM airdrops WHERE priority = ? ORDER BY overall_score DESC",
                (priority,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def mark_notified(self, airdrop_id: int):
        """Mark an airdrop as notified."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE airdrops SET notified_at = ?, status = 'notified' WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), airdrop_id)
            )
            await db.commit()

    async def log_scan(self, chain: str, signals: int, duration_ms: int):
        """Log a scan event."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO scan_history (chain, signals_found, scan_duration_ms) VALUES (?, ?, ?)",
                (chain, signals, duration_ms)
            )
            await db.commit()

    async def get_stats(self) -> dict:
        """Get database statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM airdrops")
            total = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM airdrops WHERE priority = 'HIGH'"
            )
            high = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM airdrops WHERE notified_at IS NOT NULL"
            )
            notified = (await cursor.fetchone())[0]
            return {"total": total, "high_priority": high, "notified": notified}
