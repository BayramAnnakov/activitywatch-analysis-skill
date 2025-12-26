# ActivityWatch Analysis Skill

A Claude Code skill for weekly productivity analysis using [ActivityWatch](https://activitywatch.net/) data. Calculates focus scores, detects "death loops" (repetitive app switching), and generates actionable insights.

## Features

- **Smart Auto-Categorization**: Classifies activities into productive/neutral/distracting
- **Dual Scoring**: Productivity score (what you worked on) + Focus score (attention quality)
- **Browser Breakdown**: See exactly what you did inside browsers
- **Death Loop Detection**: Identifies repetitive app switching patterns with fix suggestions
- **Actionable Insights**: Specific recommendations based on your data
- **Customizable Categories**: JSON config to tune for your workflow

## Requirements

- Python 3.8+
- [ActivityWatch](https://activitywatch.net/) installed and running
- No external dependencies (uses only stdlib)

## Quick Start

### 1. Export from ActivityWatch

Open ActivityWatch (`http://localhost:5600`) → Raw Data → Export → CSV

### 2. Run Analysis

```bash
# Basic analysis (JSON output)
python scripts/analyze_aw.py export.csv

# Human-readable report
python scripts/analyze_aw.py export.csv --report

# With custom categories
python scripts/analyze_aw.py export.csv --config scripts/category_config.json --report
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

## Death Loops

Death loops are repetitive A↔B app switches that fragment your attention.

| Verdict | Meaning | Action |
|---------|---------|--------|
| productive | Normal workflow (IDE ↔ Terminal) | Consider split screen |
| mixed | Could go either way | Batch these activities |
| distracting | Attention leak | Block during focus hours |

## Customizing Categories

Edit `scripts/category_config.json` to match your workflow:

```json
{
  "my_product": {
    "weight": 0.8,
    "description": "My SaaS product work",
    "apps": [],
    "titles": ["MyApp", "myapp.com"]
  }
}
```

**Weight scale:**
- `1.0` = Deep work (Terminal, IDE)
- `0.7-0.9` = Productive (AI tools, writing)
- `0.5` = Mixed (meetings)
- `0.3` = Shallow (email, chat)
- `0.0` = Neutral (system utilities)
- `-0.2 to -0.5` = Distracting (entertainment, social)

## Weekly Review Ritual

Every Sunday (15 min):

1. Export week's data from ActivityWatch (CSV)
2. Run: `python scripts/analyze_aw.py export.csv --report`
3. Review the "One Change" recommendation
4. Implement one intervention
5. Track score improvement next week

## Integration with Claude Code

As a Claude Code skill, you can ask:

```
"Analyze my ActivityWatch export from this week"
"Show me my death loops and how to fix them"
"What are my peak productive hours?"
```

## Files

```
activitywatch-analysis-skill/
├── SKILL.md                      # Skill definition (AgentSkills.io format)
├── README.md                     # This file
├── scripts/
│   ├── analyze_aw.py             # Main analyzer
│   └── category_config.json      # Customizable categories
└── references/
    └── analysis_prompts.md       # Prompts for deeper analysis with LLMs
```

## Privacy

All analysis runs locally. No data leaves your machine unless you choose to share it.

## License

MIT

## Author

Bayram Annakov ([@BayramAnnakov](https://github.com/BayramAnnakov))
