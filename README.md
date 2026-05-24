# 🎯 MiMo Airdrop Hunter

AI-powered airdrop detection and analysis agent using **Xiaomi MiMo V2.5** reasoning models. Scans multiple EVM chains for upcoming airdrops, evaluates eligibility, and provides actionable intelligence.

## ✨ Features

- 🔍 **Multi-chain Scanner** — Monitors Ethereum, Base, Arbitrum, Optimism, BSC, and Solana for airdrop opportunities
- 🧠 **AI-Powered Analysis** — Uses MiMo's reasoning model to evaluate airdrop legitimacy, potential value, and eligibility
- 📊 **Risk Assessment** — ML-based scoring system to filter scams and low-value opportunities
- ⏰ **Cron Scheduler** — Automated scanning with configurable intervals
- 💰 **Portfolio Tracker** — Tracks wallet interactions across chains for eligibility mapping
- 📱 **Telegram Alerts** — Real-time notifications for high-value airdrops
- 📈 **Historical Database** — SQLite storage for trend analysis and success rate tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            MiMo Airdrop Hunter              │
├─────────────┬───────────────┬───────────────┤
│   Scanner   │   Analyzer    │   Notifier    │
│  (chains)   │  (MiMo AI)    │  (Telegram)   │
├─────────────┴───────────────┴───────────────┤
│              MiMo V2.5 API                  │
│     (Reasoning + Classification)            │
├─────────────────────────────────────────────┤
│           SQLite Database                   │
│      (history, scores, alerts)              │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/MikaPrjkt/mimo-airdrop-hunter.git
cd mimo-airdrop-hunter

# Install
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys

# Run scanner
python -m hunter.main --scan

# Run full pipeline (scan + analyze + notify)
python -m hunter.main --full
```

## ⚙️ Configuration

```yaml
# config.yaml
mimo:
  api_key: "your-mimo-api-key"
  model: "MiMo-V2.5-Reasoning"
  base_url: "https://api.xiaomimimo.com/v1"

chains:
  - name: "ethereum"
    rpc: "https://eth.llamarpc.com"
    explorer: "https://api.etherscan.io/api"
  - name: "base"
    rpc: "https://mainnet.base.org"
  - name: "arbitrum"
    rpc: "https://arb1.arbitrum.io/rpc"

wallets:
  - address: "0xYourWalletAddress"
    label: "main"

telegram:
  bot_token: "your-bot-token"
  chat_id: "your-chat-id"

scheduler:
  scan_interval_minutes: 30
  deep_scan_hour: 2  # UTC
```

## 📦 Modules

| Module | Description |
|--------|-------------|
| `hunter.scanner` | Multi-chain airdrop detection via RPC calls & API polling |
| `hunter.analyzer` | MiMo AI-powered eligibility & risk assessment |
| `hunter.notifier` | Telegram alert delivery with formatting |
| `hunter.database` | SQLite persistence for opportunities & history |
| `hunter.scheduler` | Cron-like scheduling with backoff |

## 🧪 Example Output

```
🔍 Scan Results — 2026-05-24 02:00 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 [HIGH] EigenLayer Restaking Campaign
   Chain: Ethereum | Score: 92/100
   Status: Active | Ends: 2026-05-30
   Action: Stake ETH via restaking protocol
   Est. Value: $500-2000

🎯 [MED] Zora Creator Rewards
   Chain: Base | Score: 78/100
   Status: Ongoing
   Action: Mint/collect on Zora
   Est. Value: $50-300

⚠️ [LOW] RandomTokenXYZ
   Chain: BSC | Score: 15/100
   Status: Suspicious — flagged by MiMo analysis
   Reason: Fake contract, phishing pattern detected
```

## 📊 MiMo AI Analysis Pipeline

1. **Detection** — Scanner finds potential airdrop signals (contract deployments, protocol announcements, social signals)
2. **Enrichment** — Fetch contract details, TVL, team background, community metrics
3. **MiMo Reasoning** — Send enriched data to MiMo V2.5 for deep analysis:
   - Legitimacy scoring (scam detection)
   - Eligibility assessment per wallet
   - Estimated value calculation
   - Optimal action strategy
4. **Classification** — Categorize as HIGH/MEDIUM/LOW priority
5. **Alert** — Push actionable intel via Telegram

## 🛡️ Security

- API keys stored in environment variables (never committed)
- Wallet addresses are hashed in database
- No private keys needed — read-only analysis
- Rate limiting on all external API calls

## 📜 License

MIT © MikaPrjkt

## 🙏 Credits

- [Xiaomi MiMo](https://mimo.xiaomi.com/) — Reasoning AI models
- [MiMo API Platform](https://platform.xiaomimimo.com/) — API infrastructure
