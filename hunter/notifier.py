"""
Telegram Notifier — Sends formatted airdrop alerts via Telegram bot.
"""

import httpx
from typing import Optional


PRIORITY_EMOJI = {
    "HIGH": "🔥",
    "MEDIUM": "🟡",
    "LOW": "⚪",
    "SKIP": "⛔",
}

PRIORITY_BOLD = {
    "HIGH": True,
    "MEDIUM": False,
    "LOW": False,
    "SKIP": False,
}


class TelegramNotifier:
    """Sends airdrop alerts to Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_alert(self, analysis, wallet_address: Optional[str] = None) -> bool:
        """Send formatted airdrop alert."""
        emoji = PRIORITY_EMOJI.get(analysis.priority, "❓")
        bold = PRIORITY_BOLD.get(analysis.priority, False)

        text = self._format_alert(analysis, emoji, bold, wallet_address)
        return await self._send(text)

    async def send_batch_alert(self, analyses: list, wallet_address: Optional[str] = None) -> bool:
        """Send batched summary of multiple airdrops."""
        if not analyses:
            return True

        lines = [f"📡 **Airdrop Scan Report** — {len(analyses)} found\n"]

        for a in sorted(analyses, key=lambda x: x.overall_score, reverse=True):
            emoji = PRIORITY_EMOJI.get(a.priority, "❓")
            lines.append(
                f"{emoji} **{a.name}** ({a.chain})\n"
                f"   Score: {a.overall_score}/100 | Value: {a.estimated_value_usd}\n"
                f"   {a.action_required[:100]}"
            )

        lines.append(f"\n🏦 Wallet: `{wallet_address[:10]}...{wallet_address[-6:]}`" if wallet_address else "")
        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("Powered by MiMo V2.5 🧠")

        return await self._send("\n".join(lines))

    def _format_alert(self, analysis, emoji: str, bold: bool, wallet: Optional[str]) -> str:
        risk_text = ""
        if analysis.risk_flags:
            risk_text = "\n⚠️ Risks: " + ", ".join(analysis.risk_flags[:3])

        wallet_line = ""
        if wallet:
            short = f"{wallet[:10]}...{wallet[-6:]}"
            wallet_line = f"\n🏦 Wallet: `{short}`"

        return (
            f"{emoji} **{'[PRIORITY] ' if bold else ''}{analysis.name}**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 Chain: {analysis.chain}\n"
            f"📊 Legitimacy: {analysis.legitimacy_score}/100\n"
            f"🎯 Eligibility: {analysis.eligibility_score}/100\n"
            f"💰 Est. Value: {analysis.estimated_value_usd}\n"
            f"⚡ Priority: {analysis.priority}{risk_text}\n\n"
            f"📋 **Action:**\n{analysis.action_required}\n"
            f"{wallet_line}\n\n"
            f"🧠 _MiMo Analysis:_ {analysis.reasoning[:300]}"
        )

    async def _send(self, text: str) -> bool:
        """Send message via Telegram API."""
        try:
            resp = await self.client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"[Notifier] Error: {e}")
            return False

    async def send_status(self, stats: dict, scan_time: str):
        """Send scan status update."""
        text = (
            f"✅ **Scan Complete** — {scan_time}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Total Opportunities: {stats['total']}\n"
            f"🔥 High Priority: {stats['high_priority']}\n"
            f"📨 Notified: {stats['notified']}"
        )
        return await self._send(text)

    async def close(self):
        await self.client.aclose()
