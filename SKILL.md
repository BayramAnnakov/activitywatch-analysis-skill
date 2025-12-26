---
name: activitywatch-analysis
description: Weekly Focus Engineering analysis using ActivityWatch data. Use when analyzing app usage patterns, detecting context switching problems, identifying "death loops" (repetitive app switching), calculating focus scores, or creating weekly productivity reviews.
---

# ActivityWatch Analysis Skill

Analyze ActivityWatch exports to identify focus problems, track productivity, and generate actionable weekly insights.

## Features

- **Smart Auto-Categorization**: Classifies activities into productive/neutral/distracting
- **AI Agent Detection**: Recognizes Claude Code, Codex, Aider, and other AI coding agents
- **Dual Scoring**: Productivity score (what you worked on) + Focus score (attention quality)
- **Browser Breakdown**: See exactly what you did inside browsers
- **Death Loop Detection**: Identifies repetitive app switching patterns with fix suggestions
- **Actionable Insights**: Specific recommendations based on your data
- **Customizable Categories**: JSON config to tune for your workflow

## Quick Start

### 1. Export from ActivityWatch

Open ActivityWatch (`http://localhost:5600`) → Raw Data → Export → CSV

### 2. Run Analysis

```bash
# Basic analysis
python scripts/analyze_aw.py export.csv --report

# With custom categories
python scripts/analyze_aw.py export.csv --config scripts/category_config.json --report

# JSON output for automation
python scripts/analyze_aw.py export.csv > summary.json
```

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
Use insights to configure Cold Turkey, RescueTime, or macOS Focus Modes.

## Files

```
activitywatch-analysis/
├── SKILL.md                      # This file
├── scripts/
│   ├── analyze_aw.py             # Main analyzer
│   └── category_config.json      # Customizable categories
└── references/
    └── analysis_prompts.md       # Prompts for deeper analysis
```

## Privacy

All analysis runs locally. No data leaves your machine unless you choose to share it.

## Requirements

- Python 3.8+
- ActivityWatch installed and running
- No external dependencies (uses only stdlib)
