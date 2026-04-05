# ActivityWatch Analysis Skill

A Claude Code skill for productivity analysis using [ActivityWatch](https://activitywatch.net/) data. Calculates focus scores, detects "death loops" (repetitive app switching), and generates actionable insights.

## Features

- **Calibration Mode**: First-run setup that shows uncategorized apps, detects missing watchers, and guides personalization
- **80+ App Defaults**: JetBrains IDEs, terminals, browsers, design tools, CRMs — works out of the box for most developers
- **AI Agent Detection**: Recognizes Claude Code, Codex, Aider, GitHub Copilot as productive workflows
- **Dual Scoring**: Productivity score (what you worked on) + Focus score (attention quality)
- **Deep Browser Analysis**: Site-level breakdown with productivity ratios (requires aw-watcher-web)
- **Death Loop Detection**: Identifies repetitive app switching patterns with fix suggestions
- **Telegram Chat Categorization**: Separate work chats from personal messaging
- **Customizable Categories**: JSON config to tune for your workflow

## Requirements

- Python 3.8+
- [ActivityWatch](https://activitywatch.net/) installed and running
- Recommended: `pip install aw-client` for direct API access
- Recommended: [aw-watcher-web](https://github.com/ActivityWatch/aw-watcher-web) Chrome extension for site-level browser tracking

## Install as Claude Code Skill

```bash
cp -r activitywatch-analysis-skill ~/.claude/skills/activitywatch-analysis
```

## Quick Start

### Step 1: Calibrate (first run)

```bash
# Show what needs configuring
python scripts/analyze_aw.py --fetch --from week --calibrate --config scripts/category_config.json
```

This shows:
- Uncategorized apps with significant usage time
- Whether aw-watcher-web is installed (critical for browser analysis)
- Telegram usage that may need chat-level categorization

Then edit `scripts/category_config.json` to classify your uncategorized apps.

### Step 2: Analyze

```bash
# Today
python scripts/analyze_aw.py --fetch --from today --report

# This week
python scripts/analyze_aw.py --fetch --from week --report

# Specific dates
python scripts/analyze_aw.py --fetch --from 2026-04-01 --to 2026-04-05 --report

# With your custom config
python scripts/analyze_aw.py --fetch --from today --report --config scripts/category_config.json

# JSON output (for automation)
python scripts/analyze_aw.py --fetch --from today --config scripts/category_config.json
```

**Date formats:** `today`, `yesterday`, `week`, `7d`, `2w`, `YYYY-MM-DD`

### Step 3: CSV Fallback

If you don't have `aw-client`:

1. Open ActivityWatch (`http://localhost:5600`) -> Raw Data -> Export -> CSV
2. `python scripts/analyze_aw.py export.csv --report`

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

High productivity + low focus = good work but constantly interrupted.

## Death Loops

Repetitive A-B app switches that fragment your attention.

| Verdict | Meaning | Action |
|---------|---------|--------|
| ai_assisted | AI coding agent active | Productive workflow |
| productive | Normal workflow (IDE - Terminal) | Consider split screen |
| mixed | Could go either way | Batch these activities |
| distracting | Attention leak | Block during focus hours |

See `references/blocking_guides.md` for blocking tool setup guides.

## Customizing Categories

Edit `scripts/category_config.json`:

```json
{
  "my_product": {
    "weight": 0.8,
    "description": "My SaaS product work",
    "apps": ["MyApp"],
    "titles": ["myapp.com", "MyApp Dashboard"]
  }
}
```

**Weight scale:** `1.0` deep work, `0.7-0.9` productive, `0.5` mixed, `0.3` shallow, `0.0` neutral, `-0.2 to -0.5` distracting

### Telegram Chat Categorization

Separate productive Telegram chats from personal messaging:

```json
{
  "telegram_chats": {
    "product_work": {
      "weight": 0.8,
      "patterns": ["Team Chat", "Project Alerts", "bot-monitoring"]
    },
    "content_creation": {
      "weight": 0.7,
      "patterns": ["My Channel", "Content Ideas"]
    }
  }
}
```

Unmatched chats default to `communication_personal` (weight 0.1).

## Recommended Watchers

| Watcher | What it tracks | Install |
|---------|---------------|---------|
| aw-watcher-window | Active app + window title | Included with ActivityWatch |
| aw-watcher-afk | Idle/active state | Included with ActivityWatch |
| aw-watcher-web | Browser tab URLs + titles | [Chrome extension](https://chrome.google.com/webstore/detail/activitywatch-web-watcher) / [Safari build](https://github.com/ActivityWatch/aw-watcher-web) |
| aw-watcher-vscode | VS Code file-level tracking | VS Code marketplace |

Without aw-watcher-web, all browser time appears as one block ("Chrome") with no site-level breakdown.

## Integration with Claude Code

As a Claude Code skill:

```
/activitywatch calibrate     — first-run setup, personalize categories
/activitywatch               — analyze today
/activitywatch week          — analyze this week
/activitywatch review        — coaching-style comparison to previous weeks
```

## Files

```
activitywatch-analysis-skill/
├── SKILL.md                      # Claude Code skill definition
├── CLAUDE.md                     # Development guidance
├── README.md                     # This file
├── scripts/
│   ├── analyze_aw.py             # Main analyzer
│   ├── focus_guard.py            # App blocker for focus sessions
│   ├── category_config.json      # Customizable categories (edit this!)
│   └── focus_config.json         # Focus Guard configuration
└── references/
    ├── analysis_prompts.md       # Prompts for deeper analysis
    └── blocking_guides.md        # App blocking setup guides
```

## Privacy

All analysis runs locally. No data leaves your machine unless you choose to share it.

## License

MIT

## Author

Bayram Annakov ([@BayramAnnakov](https://github.com/BayramAnnakov))
