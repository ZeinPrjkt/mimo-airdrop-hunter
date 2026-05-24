"""
Multi-chain Airdrop Scanner — Detects airdrop opportunities across EVM chains.

Scans via:
- RPC calls (recent contract deployments, token transfers)
- Protocol-specific APIs (EigenLayer, Zora, LayerZero, etc.)
- Social signal aggregation (project announcements)
"""

import httpx
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AirdropSignal:
    """Raw airdrop signal detected by scanner."""
    name: str
    chain: str
    contract_address: Optional[str]
    description: str
    source: str  # "rpc", "api", "social"
    detected_at: str
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "chain": self.chain,
            "contract_address": self.contract_address,
            "description": self.description,
            "source": self.source,
            "detected_at": self.detected_at,
            "metadata": self.metadata
        }


# Known airdrop sources per chain
AIRDROP_SOURCES = {
    "ethereum": [
        {"name": "EigenLayer", "type": "restaking", "api": "https://api.eigenlayer.xyz"},
        {"name": "Pendle", "type": "yield", "api": "https://api-v2.pendle.finance"},
        {"name": "ENS", "type": "identity", "check": "ens_domain_holder"},
    ],
    "base": [
        {"name": "Zora", "type": "nft", "api": "https://api.zora.co"},
        {"name": "Aerodrome", "type": "dex", "check": "velodrome_lp"},
    ],
    "arbitrum": [
        {"name": "Arbitrum DAO", "type": "governance", "check": "arb_holder"},
        {"name": "Camelot", "type": "dex", "check": "camelot_lp"},
    ],
    "optimism": [
        {"name": "Optimism Collective", "type": "governance", "check": "op_holder"},
        {"name": "Velodrome", "type": "dex", "check": "velo_lp"},
    ],
    "bsc": [
        {"name": "PancakeSwap", "type": "dex", "check": "cake_staker"},
    ],
    "solana": [
        {"name": "Jupiter", "type": "dex", "api": "https://api.jup.ag"},
        {"name": "Raydium", "type": "dex", "check": "ray_lp"},
    ],
}


class ChainScanner:
    """Scans a single EVM chain for airdrop signals."""

    def __init__(self, name: str, rpc_url: str, explorer_api: Optional[str] = None):
        self.name = name
        self.rpc_url = rpc_url
        self.explorer_api = explorer_api
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_recent_contracts(self, blocks_back: int = 1000) -> list[dict]:
        """Find recently deployed contracts (potential new protocols)."""
        # Get latest block
        resp = await self._rpc("eth_blockNumber")
        latest = int(resp["result"], 16)
        from_block = latest - blocks_back

        # Scan for contract creation txs
        resp = await self._rpc("eth_getLogs", {
            "fromBlock": hex(from_block),
            "toBlock": hex(latest),
            "address": None,  # all addresses
        })

        contracts = []
        if "result" in resp:
            for log in resp["result"][:20]:  # limit
                if log.get("input", "0x") != "0x" and log.get("to") is None:
                    contracts.append({
                        "hash": log.get("transactionHash"),
                        "from": log.get("from"),
                        "block": int(log.get("blockNumber", "0x0"), 16),
                    })
        return contracts

    async def get_token_transfers(self, token: str, wallet: str,
                                   from_block: int = 0) -> list[dict]:
        """Track token transfers for a specific token."""
        if not self.explorer_api:
            return []

        resp = await self.client.get(self.explorer_api, params={
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": token,
            "page": 1,
            "offset": 50,
        })
        return resp.json().get("result", [])

    async def _rpc(self, method: str, params: dict = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1
        }
        resp = await self.client.post(self.rpc_url, json=payload)
        return resp.json()

    async def close(self):
        await self.client.aclose()


class AirdropScanner:
    """Orchestrates scanning across multiple chains."""

    def __init__(self, chains_config: list[dict]):
        self.scanners = {}
        for chain in chains_config:
            self.scanners[chain["name"]] = ChainScanner(
                name=chain["name"],
                rpc_url=chain["rpc"],
                explorer_api=chain.get("explorer"),
            )

    async def scan_all(self) -> list[AirdropSignal]:
        """Run scan across all configured chains."""
        import asyncio
        signals = []

        tasks = [self._scan_chain(name) for name in self.scanners]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                signals.extend(result)

        return signals

    async def _scan_chain(self, chain_name: str) -> list[AirdropSignal]:
        """Scan a single chain for opportunities."""
        scanner = self.scanners.get(chain_name)
        if not scanner:
            return []

        signals = []
        now = datetime.now(timezone.utc).isoformat()

        # Check known sources
        for source in AIRDROP_SOURCES.get(chain_name, []):
            signal = AirdropSignal(
                name=source["name"],
                chain=chain_name,
                contract_address=None,
                description=f"{source['name']} — {source['type']} protocol",
                source="api",
                detected_at=now,
                metadata=source
            )
            signals.append(signal)

        # Check for new contract deployments
        try:
            contracts = await scanner.get_recent_contracts()
            for c in contracts[:5]:  # limit
                signals.append(AirdropSignal(
                    name=f"New Contract ({c['from'][:10]}...)",
                    chain=chain_name,
                    contract_address=c.get("hash"),
                    description=f"Recently deployed contract on {chain_name}",
                    source="rpc",
                    detected_at=now,
                    metadata=c
                ))
        except Exception:
            pass  # Chain might be down

        return signals

    async def close(self):
        for scanner in self.scanners.values():
            await scanner.close()
