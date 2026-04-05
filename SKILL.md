---
description: "Focus Engineering with ActivityWatch — analyze app usage, detect death loops, calculate focus scores, generate weekly insights. Three modes: calibrate (first run), analyze (daily/weekly), review (coaching)."
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# ActivityWatch Analysis Skill

Analyze ActivityWatch data to identify focus problems, track productivity, and generate actionable insights.

## Detect Mode

Check what the user typed:
- `/activitywatch calibrate` or first run → **Calibrate Mode**
- `/activitywatch` or `/activitywatch today` or `/activitywatch week` → **Analyze Mode**
- `/activitywatch review` → **Review Mode** (coaching perspective)

## MODE 1: Calibrate (first run)

Run this once to personalize the analyzer for the user's workflow.

### Step 1: Check ActivityWatch is running + watchers

```bash
curl -s http://localhost:5600/api/0/info 2>/dev/null
```

If not running, tell user: "Start ActivityWatch first — it needs to be collecting data."

Then check which watchers are active:
```bash
curl -s http://localhost:5600/api/0/buckets 2>/dev/null | python3 -c "import json,sys; buckets=json.load(sys.stdin); [print(k) for k in sorted(buckets.keys())]"
```

You should see at minimum:
- `aw-watcher-window_*` — tracks active app + window title (essential)
- `aw-watcher-afk_*` — tracks idle/active state (essential)

Recommend if missing:
- `aw-watcher-web-*` — **browser tab tracking** (critical for site-level analysis). Install: Chrome extension from Chrome Web Store "ActivityWatch Web Watcher", or for Safari build from https://github.com/ActivityWatch/aw-watcher-web
- `aw-watcher-vscode` — VS Code extension for code-level tracking
- `aw-watcher-input` — keyboard/mouse activity (optional, privacy-sensitive)

Tell user: "Without aw-watcher-web, all browser time shows as one block under 'Chrome' or 'Safari' — no site-level breakdown. Install the Chrome extension for much better analysis."

### Step 2: Run calibration on last 7 days

```bash
python scripts/analyze_aw.py --fetch --from week --calibrate --config scripts/category_config.json
```

This shows:
- Uncategorized apps with >5 min usage
- Default-categorized items that may need reclassification
- Telegram usage breakdown (if significant)

### Step 3: Interview the user about uncategorized items

For each uncategorized app/site shown:
1. Ask: "What is [AppName]? Is it productive work, neutral, or distracting?"
2. Based on answer, assign to the right category and weight
3. Update `scripts/category_config.json` with the new entries

### Step 4: Personalize product_work and telegram_chats

Ask:
- "What are your main product/business apps or sites? (e.g., your SaaS dashboard, CRM)"
- "Do you have work-related Telegram chats? List the ones that count as productive."

Add answers to `product_work.titles` and `telegram_chats.product_work.patterns` in the config.

### Step 5: Verify

```bash
python scripts/analyze_aw.py --fetch --from today --report --config scripts/category_config.json
```

Ask user to spot-check: "Does this report match your experience of today? Any app miscategorized?"

## MODE 2: Analyze (daily/weekly)

### Parse the request

- "today" / "yesterday" / no argument → `--from today` or `--from yesterday`
- "this week" / "week" → `--from week`
- Specific dates → `--from YYYY-MM-DD --to YYYY-MM-DD`

### Run analysis

```bash
python scripts/analyze_aw.py --fetch --from [date] --report --config scripts/category_config.json --timezone [user's timezone]
```

Present the report. Highlight:
- Productivity score and focus score
- Death loops (repetitive app switching)
- Top distraction
- AI-assisted development time
- The "One Change" recommendation

### If user asks for deeper analysis

Read `references/analysis_prompts.md` for coaching-style follow-up questions.

## MODE 3: Review (coaching perspective)

Compare this week to previous weeks. Look for:
- Score trends (improving, declining, flat)
- Recurring death loops that haven't been addressed
- Deep work hour trends
- Whether the "One Change" from last week was implemented

If the user has a coaching system (e.g., `~/GH/bayram-os/coaching/`), cross-reference with process goals.

## Features

- **Smart Auto-Categorization**: Classifies activities into productive/neutral/distracting
- **AI Agent Detection**: Recognizes Claude Code, Codex, Aider, and other AI coding agents
- **Dual Scoring**: Productivity score (what you worked on) + Focus score (attention quality)
- **Deep Browser Analysis**: Site-level breakdown with productivity ratios (Netflix, GitHub, ChatGPT, etc.)
- **Death Loop Detection**: Identifies repetitive app switching patterns with fix suggestions
- **Actionable Insights**: Specific recommendations based on your data
- **Customizable Categories**: JSON config to tune for your workflow

## Quick Start

### Option 1: Direct API Fetch (Recommended)

If you have `aw-client` installed (`pip install aw-client`), you can fetch data directly:

```bash
# Analyze today's productivity
python scripts/analyze_aw.py --fetch --from today --report --timezone America/Los_Angeles

# Analyze yesterday
python scripts/analyze_aw.py --fetch --from yesterday --report

# Analyze the past week
python scripts/analyze_aw.py --fetch --from week --report

# Analyze specific date range
python scripts/analyze_aw.py --fetch --from 2025-12-20 --to 2025-12-26 --report

# Analyze last 7 days
python scripts/analyze_aw.py --fetch --from 7d --report
```

**Date formats supported:**
- `today`, `yesterday`, `week` (last 7 days)
- Relative: `7d` (7 days ago), `2w` (2 weeks ago)
- Absolute: `YYYY-MM-DD` (e.g., `2025-12-26`)

### Option 2: CSV Export (Fallback)

If you prefer manual export or don't have `aw-client`:

1. Open ActivityWatch (`http://localhost:5600`) → Raw Data → Export → CSV
2. Run analysis:

```bash
# Basic analysis (uses system timezone)
python scripts/analyze_aw.py export.csv --report

# Specify timezone explicitly
python scripts/analyze_aw.py export.csv --timezone America/Los_Angeles --report

# With custom categories
python scripts/analyze_aw.py export.csv --config scripts/category_config.json --report

# JSON output for automation
python scripts/analyze_aw.py export.csv > summary.json
```

### Recommended Workflow

Before trusting a weekly report, spot-check with a single day's data:

1. **Spot-check first** (5 min): Analyze yesterday's data
   - Verify timezone is correct (timestamps match your memory)
   - Verify idle time makes sense (screen lock duration)
   - Check if top apps/categories match your experience

2. **Fix issues if found**:
   - Wrong timezone? Use `--timezone America/Los_Angeles` (or your zone)
   - Missing apps? Add them to `scripts/category_config.json`
   - Wrong categories? Adjust weights in config

3. **Run full analysis**: Once spot-check passes, trust the weekly report

### Timezone Handling

ActivityWatch stores timestamps in UTC. The analyzer converts them to your local timezone for accurate hourly analysis.

```bash
# Common timezone examples:
--timezone America/Los_Angeles  # Pacific Time
--timezone America/New_York     # Eastern Time
--timezone Europe/London        # UK
--timezone Asia/Tokyo           # Japan
```

If not specified, the system's local timezone is used.

### Time Breakdown

The report shows three time metrics:

| Metric | Meaning |
|--------|---------|
| **Active** | Time spent in apps (excluding idle) |
| **Idle** | Screen locked / loginwindow time |
| **Tracked** | Total time computer was on (active + idle) |

## Understanding Your Scores

### Combined Score (0-100)

| Range | Interpretation |
|-------|----------------|
| 80-100 | Excellent - Deep work patterns, minimal distractions |
| 60-79 | Good - Solid productivity with room to improve |
| 40-59 | Moderate - Attention fragmented, review death loops |
| 0-39 | Needs work - High distraction, consider app blockers |

### Productivity vs Focus

- **Productivity Score**: Measures *what* you spent time on (deep work vs. entertainment)
- **Focus Score**: Measures *how* you worked (sustained attention vs. constant switching)

You can have high productivity but low focus (doing good work but constantly interrupted) or vice versa.

### Category Weights

| Weight | Type | Examples |
|--------|------|----------|
| 1.0 | Deep work | Terminal, IDE, coding |
| 0.7-0.9 | Productive | AI tools, writing, design, learning |
| 0.5 | Mixed | Meetings, presentations |
| 0.3 | Shallow | Email, work chat |
| 0.0 | Neutral | System utilities |
| -0.2 to -0.5 | Distracting | Entertainment, social media |

## Death Loops

Death loops are repetitive A↔B app switches that fragment your attention.

| Verdict | Meaning | Action |
|---------|---------|--------|
| 🤖 ai_assisted | AI coding agent active (Claude Code, Codex) | Productive workflow |
| 🟢 productive | Normal workflow (IDE ↔ Terminal) | Consider split screen |
| 🟡 mixed | Could go either way | Batch these activities |
| 🔴 distracting | Attention leak | Block during focus hours |

Common patterns:
- **Slack ↔ IDE**: Waiting for responses → Batch check times
- **Browser ↔ IDE**: Testing/debugging → Use split screen
- **Email ↔ Work**: Anxiety/FOMO → Close email, check 2x/day
- **Social ↔ Anything**: Procrastination → Block during focus hours

## Browser Analysis

Browser time is often 30-50% of screen time. The analyzer extracts **sites** from window titles and categorizes them:

### Site Categories

| Category | Examples | Weight |
|----------|----------|--------|
| AI Tools | ChatGPT, Claude.ai, Perplexity | 🟢 0.8 |
| Development | GitHub, Supabase, localhost | 🟢 0.8-1.0 |
| Design | Figma, Webflow, Canva | 🟢 0.9 |
| Entertainment | Netflix, Prime Video, Twitch | 🔴 -0.5 |
| Social Media | Twitter/X, LinkedIn, Reddit | 🔴 -0.3 |
| Video | YouTube (neutral - could be either) | 🟡 0.0 |

### Report Output

```
## 🌐 Browser Activity

**Total browser time:** 66.1h

| Type | Hours | % |
|------|-------|---|
| 🟢 Productive | 11.9h | 18% |
| 🟡 Neutral | 25.9h | 41% |
| 🔴 Distracting | 27.0h | 41% |

### Top Sites
| Site | Hours | Category | Type |
|------|-------|----------|------|
| Netflix | 11.9h | entertainment | 🔴 |
| YouTube | 7.8h | video | 🟡 |
| ChatGPT | 1.9h | ai_tools | 🟢 |
```

### Customizing Site Categories

Add sites to `KNOWN_SITES` in `analyze_aw.py`:

```python
'mysite.com': ('MySite', 'development', 0.8),
```

## AI Agent Detection

The analyzer recognizes when you're using AI coding agents and adjusts scoring accordingly.

### Supported Agents

| Agent | Detection Pattern |
|-------|-------------------|
| Claude Code | Window title with ✳ prefix or `claude` command |
| OpenAI Codex | `codex` in terminal title |
| Aider | `aider` in terminal title |
| GitHub Copilot CLI | `gh copilot` in terminal title |

### How It Works

When you use AI coding agents, frequent Browser ↔ Terminal switching is **expected and productive** (reviewing docs, checking dashboards, supervising AI output). The analyzer:

1. Detects AI agent running in Terminal by window title
2. Marks Browser ↔ Terminal switches as "ai_assisted" instead of "distracting"
3. Excludes productive AI switches from Focus Score penalty
4. Still flags distracting switches (Telegram ↔ Terminal) even during AI sessions

### Report Section

The report includes an "AI-Assisted Development" section showing:

```
| Agent | Hours | Switches |
|-------|-------|----------|
| claude_code | 25.6h | ~6700 |
| codex | 24.2h | ~6700 |
```

## Customizing Categories

Edit `scripts/category_config.json` to match your workflow:

```json
{
  "my_product": {
    "weight": 0.8,
    "description": "My SaaS product work",
    "apps": [],
    "titles": ["MyApp", "myapp.com", "MyApp Dashboard"]
  }
}
```

**Fields:**
- `weight`: Productivity impact (-0.5 to 1.0)
- `apps`: Match by application name (exact)
- `titles`: Match by window title (case-insensitive, partial match)
- `description`: Human-readable explanation

### Telegram Chat Categorization

Telegram chats can be categorized by chat name (extracted from window title). Add to `category_config.json`:

```json
{
  "telegram_chats": {
    "content_creation": {
      "weight": 0.7,
      "patterns": ["My Channel Name", "Zettelkasten"]
    },
    "product_work": {
      "weight": 0.8,
      "patterns": ["Course Chat", "EDU", "admin-monitoring", "bot-alerts"]
    },
    "communication_work": {
      "weight": 0.3,
      "patterns": ["Team Chat", "Project Group", "work"]
    }
  }
}
```

- Matches are case-insensitive and partial (pattern "EDU" matches "EDU Chat")
- Unmatched Telegram chats fall back to `communication_personal` (weight 0.1)
- This allows tracking productive Telegram use (content creation, course chats) vs personal messaging

### Browser Title Categorization

Browser apps (Chrome, Safari, Firefox, ChatGPT Atlas, etc.) are automatically categorized by window title using the `KNOWN_SITES` dictionary. You can override the list of browser apps in config:

```json
{
  "browser_apps": ["Google Chrome", "Safari", "Firefox", "Arc", "ChatGPT Atlas", "Edge"]
}
```

This is useful when using alternative browsers like ChatGPT Atlas that should get title-based categorization instead of being treated as a single "ai_tools" category

## Weekly Review Ritual

Every Sunday (15 min):

1. Export week's data from ActivityWatch (CSV)
2. Run: `python scripts/analyze_aw.py export.csv --report`
3. Review the "One Change" recommendation
4. Implement one intervention
5. Track score improvement next week

## Integration Ideas

### n8n Automation
```
Weekly trigger → Export AW data → Run analyzer → Send to Telegram/Slack
```

### Claude Memory
Ask Claude to remember your patterns:
- "My peak productive hours are 11am-1pm"
- "My main death loop is Telegram ↔ Terminal"

### Focus Apps
Use insights to configure blocking tools. See `references/blocking_guides.md` for step-by-step setup:
- macOS Focus Mode
- Cold Turkey (cross-platform)
- iOS Screen Time / Android Digital Wellbeing
- Browser extensions (LeechBlock, StayFocusd)

## Focus Guard - App Blocker

Focus Guard is an open-source app blocker for macOS that prevents distracting apps from running during focus hours.

### Quick Start

```bash
# Start blocking (runs until you stop it)
python scripts/focus_guard.py --start

# Quick 2-hour focus session
python scripts/focus_guard.py --start --duration 2

# Block specific apps
python scripts/focus_guard.py --start --block Telegram Slack Discord

# Check status
python scripts/focus_guard.py --status

# Stop blocking
python scripts/focus_guard.py --stop
```

### How It Works

1. Monitors running apps every 2 seconds
2. When a blocked app is detected:
   - Shows macOS notification with warning
   - Gives 5-second grace period to save work
   - Quits the app automatically
3. Logs all violations for weekly review

### Configuration

Edit `scripts/focus_config.json`:

```json
{
  "blocked_apps": ["Telegram", "Slack", "Discord"],
  "schedule": {
    "enabled": true,
    "start_hour": 9,
    "end_hour": 17,
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
  },
  "settings": {
    "grace_period_seconds": 5,
    "show_notifications": true
  }
}
```

### Integration with Analyzer

After a focus session, run the analyzer to see your productivity:

```bash
python scripts/focus_guard.py --stop
python scripts/analyze_aw.py --fetch --from today --report
```

## Files

```
activitywatch-analysis/
├── SKILL.md                      # This file
├── scripts/
│   ├── analyze_aw.py             # Main analyzer
│   ├── focus_guard.py            # App blocker for focus sessions
│   ├── category_config.json      # Customizable categories
│   └── focus_config.json         # Focus Guard configuration
└── references/
    ├── analysis_prompts.md       # Prompts for deeper analysis
    └── blocking_guides.md        # How to implement blocking recommendations
```

## Privacy

All analysis runs locally. No data leaves your machine unless you choose to share it.

## Requirements

- Python 3.8+
- ActivityWatch installed and running
- No external dependencies (uses only stdlib)
