# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Quick Start

```bash
# Calibrate (first run — personalizes categories)
python scripts/analyze_aw.py --fetch --from week --calibrate --config scripts/category_config.json

# Check productivity for today
python scripts/analyze_aw.py --fetch --from today --report --config scripts/category_config.json

# Check specific date range
python scripts/analyze_aw.py --fetch --from 2026-04-01 --to 2026-04-05 --report

# JSON output for automation
python scripts/analyze_aw.py --fetch --from today --config scripts/category_config.json
```

## Repository Structure

```
activitywatch-analysis-skill/
├── scripts/
│   ├── analyze_aw.py           # Main analyzer - generates productivity reports
│   ├── focus_guard.py          # App blocker for focus sessions
│   ├── category_config.json    # Category definitions + Telegram chat patterns
│   └── focus_config.json       # Focus Guard configuration
├── references/
│   ├── analysis_prompts.md     # Prompts for deeper analysis
│   └── blocking_guides.md      # App blocking setup guides
├── SKILL.md                    # Full skill documentation (Claude Code skill format)
└── README.md                   # Project overview
```

## Customization

The skill ships with generic defaults. Users personalize via `scripts/category_config.json`:

### Key sections to customize:
1. **telegram_chats** — Add work-related Telegram chat names to avoid penalizing productive Telegram time
2. **product_work** — Add your product/business app names and site titles
3. **sales_tools** — Add your CRM and prospecting tools
4. **browser_apps** — Add any alternative browsers you use

### Calibration workflow:
1. Run `--calibrate` to see uncategorized items
2. Ask user what each item is
3. Add to the right category in category_config.json
4. Re-run `--report` to verify

## AI Agent Detection

Terminal sessions running Claude Code (detected by ✳ prefix in title) are marked as `ai_assisted`. Switches between Terminal/iTerm2 and work apps during AI sessions don't penalize the Focus Score.

**Supported terminals:** Terminal, iTerm2, Warp
**Supported agents:** Claude Code (✳ prefix), Codex, Aider, GitHub Copilot

## Key Files to Edit

### Adding New App Categories

Edit `scripts/category_config.json`:

```json
{
  "my_new_category": {
    "weight": 0.8,
    "description": "Description of category",
    "apps": ["AppName"],
    "titles": ["window title pattern"]
  }
}
```

### Adding New Browser Sites

Edit `KNOWN_SITES` in `scripts/analyze_aw.py`:

```python
'newsite.com': ('NewSite', 'development', 0.8),
```

## Dependencies

- Python 3.8+
- ActivityWatch running locally (http://localhost:5600)
- Optional: `pip install aw-client` for direct API access (recommended)
- No other external dependencies (uses only stdlib)
