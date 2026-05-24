"""
MiMo AI Analyzer — Uses Xiaomi MiMo V2.5 for airdrop intelligence.

Sends enriched airdrop data to MiMo's reasoning model for:
- Legitimacy scoring (scam/phishing detection)
- Eligibility assessment per wallet
- Estimated value calculation
- Optimal action strategy
"""

import httpx
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AirdropAnalysis:
    """Result of MiMo AI analysis on an airdrop opportunity."""
    name: str
    chain: str
    legitimacy_score: int  # 0-100
    eligibility_score: int  # 0-100
    estimated_value_usd: str
    priority: str  # HIGH, MEDIUM, LOW, SKIP
    action_required: str
    risk_flags: list[str]
    reasoning: str

    @property
    def overall_score(self) -> int:
        return int((self.legitimacy_score + self.eligibility_score) / 2)


MIMO_ANALYSIS_PROMPT = """You are an expert crypto airdrop analyst. Analyze the following airdrop opportunity and provide a structured assessment.

## Airdrop Data
{airdrop_data}

## Wallet Context
- Main wallet: {wallet_address}
- Chains active: {active_chains}
- Past interactions: {past_interactions}

## Analysis Required
1. **Legitimacy** (0-100): Is this a real project? Check for red flags (anonymous team, no audit, copy-paste contracts, suspicious tokenomics)
2. **Eligibility** (0-100): How likely is this wallet to qualify based on past activity?
3. **Estimated Value**: Realistic USD range for this airdrop
4. **Priority**: HIGH (>$500, confirmed real) / MEDIUM ($50-500, likely real) / LOW (<$50, uncertain) / SKIP (scam or not worth gas)
5. **Action**: Specific steps to maximize eligibility
6. **Risk Flags**: Any concerns (high gas cost, time-sensitive, requires custody, etc.)

Respond in strict JSON format:
{{
    "legitimacy_score": <int>,
    "eligibility_score": <int>,
    "estimated_value_usd": "<string>",
    "priority": "<HIGH|MEDIUM|LOW|SKIP>",
    "action_required": "<string>",
    "risk_flags": [<list of strings>],
    "reasoning": "<string>"
}}"""


class MiMoAnalyzer:
    """Analyzes airdrop opportunities using MiMo V2.5 reasoning model."""

    def __init__(self, api_key: str, base_url: str = "https://api.xiaomimimo.com/v1",
                 model: str = "MiMo-V2.5-Reasoning"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def analyze(self, airdrop_data: dict, wallet_address: str,
                      active_chains: list[str],
                      past_interactions: dict) -> AirdropAnalysis:
        """Send airdrop data to MiMo for analysis."""

        prompt = MIMO_ANALYSIS_PROMPT.format(
            airdrop_data=json.dumps(airdrop_data, indent=2),
            wallet_address=wallet_address,
            active_chains=", ".join(active_chains),
            past_interactions=json.dumps(past_interactions, indent=2)
        )

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a crypto security expert and airdrop analyst. "
                                   "Always respond with valid JSON. Be conservative in estimates."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1024
            }
        )

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        analysis = json.loads(content.strip())

        return AirdropAnalysis(
            name=airdrop_data.get("name", "Unknown"),
            chain=airdrop_data.get("chain", "unknown"),
            legitimacy_score=analysis["legitimacy_score"],
            eligibility_score=analysis["eligibility_score"],
            estimated_value_usd=analysis["estimated_value_usd"],
            priority=analysis["priority"],
            action_required=analysis["action_required"],
            risk_flags=analysis.get("risk_flags", []),
            reasoning=analysis["reasoning"]
        )

    async def batch_analyze(self, airdrops: list[dict], **kwargs) -> list[AirdropAnalysis]:
        """Analyze multiple airdrops concurrently."""
        import asyncio
        tasks = [self.analyze(a, **kwargs) for a in airdrops]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def close(self):
        await self.client.aclose()
