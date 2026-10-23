# 🛰️ HackRadar-AI: 24/7 Autonomous Hackathon Radar & AI Scorer

[![Automated Monitor](https://github.com/Pranavdeshmukhhh/HackRadar-AI/actions/workflows/monitor.yml/badge.svg)](https://github.com/Pranavdeshmukhhh/HackRadar-AI/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Nagpur Priority](https://img.shields.io/badge/Region-Nagpur%20%26%20Vidarbha-orange.svg)]()
[![Solo Friendly](https://img.shields.io/badge/Eligibility-Solo%20(1%20Member)-brightgreen.svg)]()
[![Live Web App](https://img.shields.io/badge/Web%20App-Live%20Online-brightgreen.svg?logo=googlechrome&logoColor=white)](https://pranavdeshmukhhh.github.io/HackRadar-AI/)

An autonomous intelligence monitor and opportunity radar designed specifically for **developers, students, and hackathon competitors in Nagpur & Vidarbha**. 

It continuously scans **Unstop (Dare2Compete)**, **Devfolio**, **Devpost**, **HackerEarth**, **Major League Hacking (MLH)**, and regional college tech portals, scores each event with a weighted algorithm favoring **Nagpur regional venues**, **Solo eligibility**, and **AI/Software tracks**, and dispatches alerts via **GitHub Issues (zero external API keys needed)**, **Discord**, **Telegram**, and **SMTP Email**.

---

## 🌐 Live Web App & Dashboard
- 🚀 **Interactive Web Application:** 👉 **[https://pranavdeshmukhhh.github.io/HackRadar-AI/](https://pranavdeshmukhhh.github.io/HackRadar-AI/)** *(Instant search, Nagpur & Solo filters, countdown timers, and direct apply buttons)*
- 📄 **Markdown Leaderboard:** 👉 **[View HACKATHONS.md](HACKATHONS.md)**

---

## 📂 Repository Architecture

```plaintext
HackRadar-AI/
├── .github/
│   └── workflows/
│       └── monitor.yml          # Automated GitHub Actions workflow (Daily at 8:00 AM IST + manual trigger)
├── data/
│   └── seen_hackathons.json     # Persistent state store to prevent duplicate alerts
├── src/
│   ├── __init__.py
│   ├── models.py                # Structured HackathonEvent data model with all required fields
│   ├── scrapers.py              # Multi-source connectors (Unstop, Devfolio, and Devpost APIs)
│   ├── matcher.py               # Scoring engine prioritizing Nagpur venues, AI/SW tracks, and Solo eligibility
│   ├── notifier.py              # Alert dispatchers (GitHub Issues, Discord, Telegram, SMTP Email, Markdown)
│   └── main.py                  # CLI orchestrator (--dry-run, --solo-only, --update-dashboard)
├── config.yaml                  # Configurable regional keywords, tracks, and scoring weights
├── HACKATHONS.md                # Auto-updated live dashboard table of active matches
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template for local runs
├── .gitignore
└── README.md                    # Complete setup and deployment documentation
```

---

## ⚙️ How the Automation Works

### 1. Multi-Platform Discovery (`src/scrapers.py`)
Queries public search endpoints from:
- **Unstop (Dare2Compete)**: Parses engineering hackathons, eligibility restrictions, team constraints, and college/city hosts.
- **Devfolio**: Connects to the Devfolio search index to extract hackathons, themes, prize pools, and solo/team boundaries.
- **Devpost**: Connects to open global/regional developer hackathons with prize pools, timeline dates, and AI challenge tracks.

### 2. Nagpur + Solo Prioritization Engine (`src/matcher.py`)
Each event is evaluated against customizable weights configured in [`config.yaml`](config.yaml):

| Factor | Points Boost | Criteria / Keywords |
|---|:---:|---|
| **📍 Nagpur & Vidarbha Match** | **+45 pts** | Matches Nagpur, Vidarbha, VNIT, IIIT Nagpur, IIM Nagpur, RCOEM/RBU, YCCE, GHRCE, Symbiosis Nagpur, PCE, LIT, RTMNU |
| **🏢 Maharashtra Proximity** | **+25 pts** | Matches Pune, Mumbai, Nashik, COEP, VJTI, IIT Bombay, etc. |
| **🌐 Online / Hybrid Accessibility** | **+15 pts** | Virtual or hybrid participation with no travel barrier |
| **👤 Solo Participation Boost** | **+35 pts** | Verified `min_team_size <= 1` so you can participate independently |
| **🤖 AI & Software Track Match** | **+25 pts** | Matches AI, Machine Learning, GenAI, LLM, Agentic AI, Full Stack, Software Development, Open Innovation |

*Events scoring **≥ 40 points** (customizable) qualify for alerts and dashboard listing.*

---

## 🔔 Zero-Config & Multi-Channel Alerts

### 1. GitHub Issues (Zero External Keys Needed)
Whenever a new qualifying hackathon is detected, the GitHub Actions runner automatically opens a formatted GitHub Issue labeled:
- `hackathon-alert`
- `solo-friendly` (if solo permitted)
- `nagpur-local` (if Nagpur venue)

> **💡 Why this is great:** Anyone watching the repository automatically receives native GitHub push notifications on mobile and email alerts without setting up external bot keys!

### 2. Live Repository Dashboard (`HACKATHONS.md`)
Every run automatically generates and commits an updated Markdown table and card breakdown back to the repository.

### 3. Discord Webhook (Optional)
Sends rich embeds with custom color accents (Gold for Nagpur, Purple for Solo/AI) to your team Discord channel.

### 4. Telegram Bot (Optional)
Dispatches immediate alerts with direct register links to your Telegram group or personal chat.

### 5. SMTP Email Alerts (Optional)
Dispatches formatted HTML emails via Gmail App Passwords, SendGrid, or AWS SES.

---

## 🚀 Quick Deployment Guide

### Step 1: Push Repository to GitHub
```bash
git init
git branch -M main
git add .
git commit -m "feat: initialize automated Nagpur hackathon monitor"
git remote add origin https://github.com/Pranavdeshmukhhh/HackRadar-AI.git
git push -u origin main
```

### Step 2: Enable Workflow Write Permissions
For the bot to open GitHub Issues and auto-commit dashboard updates:
1. In your GitHub repository, navigate to **Settings → Actions → General**.
2. Scroll to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Check **Allow GitHub Actions to create and approve pull requests**.
5. Click **Save**.

### Step 3: Add Optional Notification Secrets (Optional)
Go to **Settings → Secrets and variables → Actions** and add any of the following:

| Secret Name | Description | Example |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Incoming Discord webhook URL | `https://discord.com/api/webhooks/...` |
| `TELEGRAM_BOT_TOKEN` | Bot API token from `@BotFather` | `123456789:ABCdefGhI...` |
| `TELEGRAM_CHAT_ID` | Telegram user or group chat ID | `-1001234567890` |
| `SMTP_HOST` | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | `you@gmail.com` |
| `SMTP_PASSWORD` | App password (e.g., Google App Password) | `abcd efgh ijkl mnop` |
| `ALERT_RECEIVER_EMAIL` | Target email address | `alerts@domain.com` |

### Step 4: Run Workflow Instantly
1. Click on the **Actions** tab in your repository.
2. Select **Nagpur AI & Software Hackathon Monitor** in the left sidebar.
3. Click **Run workflow** → Select options → Click **Run workflow**.
4. The workflow will also trigger automatically **every day at 8:00 AM IST (02:30 UTC)**.

---

## 💻 Local Execution & Development

### 1. Setup Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. CLI Options

#### Dry Run (Inspect matches without sending notifications or mutating cache)
```bash
python -m src.main --dry-run
```

#### Solo Competitions Only (1 Member)
```bash
python -m src.main --solo-only --dry-run
```

#### Regenerate Live Dashboard
```bash
python -m src.main --update-dashboard
```

#### Set Custom Minimum Score
```bash
python -m src.main --min-score 60
```

#### Include Finished / Historical Events
```bash
python -m src.main --include-finished --dry-run
```

---

## 🛠️ Customization

Edit [`config.yaml`](config.yaml) to tune keywords, institutions, and scoring:

```yaml
scoring:
  weights:
    nagpur_regional_boost: 45
    maharashtra_regional_boost: 25
    online_hybrid_boost: 15
    solo_boost: 35
    track_match_boost: 25
  min_qualifying_score: 40
```

To add more regional colleges or keywords, simply append them to `keywords.nagpur_regional` in `config.yaml`.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
