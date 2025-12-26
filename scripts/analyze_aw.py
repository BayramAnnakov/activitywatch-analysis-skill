#!/usr/bin/env python3
"""
ActivityWatch Analyzer
- Smart auto-categorization of apps and window titles
- Personalized productivity scoring
- Title-level breakdown for browsers
- Weekly narrative insights
"""

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from zoneinfo import ZoneInfo

# ============================================================================
# CATEGORIZATION CONFIG - Customize these for your workflow
# ============================================================================

# Default categories - can be overridden by config file
DEFAULT_CATEGORY_RULES = {
    "deep_work": {"weight": 1.0, "apps": ["Terminal", "Cursor", "Code", "VSCode", "PyCharm"], "titles": ["claude code", "git "]},
    "ai_tools": {"weight": 0.8, "apps": ["Claude"], "titles": ["ChatGPT", "Claude", "OpenAI Platform", "Google AI Studio"]},
    "development": {"weight": 0.8, "apps": ["DBeaver", "Postman"], "titles": ["Supabase", "localhost", "GitHub"]},
    "writing": {"weight": 0.9, "apps": ["Notion", "Obsidian", "Notes"], "titles": ["Google Docs"]},
    "design": {"weight": 0.9, "apps": ["Figma", "Sketch"], "titles": ["Figma", "Canva", "Webflow"]},
    "presentations": {"weight": 0.7, "apps": ["Keynote", "Microsoft PowerPoint"], "titles": ["Google Slides"]},
    "spreadsheets": {"weight": 0.6, "apps": ["Numbers", "Microsoft Excel"], "titles": ["Google Sheets"]},
    "meetings": {"weight": 0.5, "apps": ["zoom.us", "Zoom", "Google Meet"], "titles": ["Zoom Meeting"]},
    "communication_work": {"weight": 0.3, "apps": ["Slack"], "titles": ["Slack |"]},
    "communication_personal": {"weight": 0.1, "apps": ["Telegram", "Messages", "WhatsApp"], "titles": []},
    "email": {"weight": 0.3, "apps": ["Mail", "Outlook"], "titles": ["Gmail", "Inbox"]},
    "learning": {"weight": 0.7, "apps": [], "titles": ["Coursera", "tutorial", "documentation", "Stack Overflow"]},
    "business_tools": {"weight": 0.5, "apps": ["Stripe"], "titles": ["Stripe", "Google Calendar", "Analytics"]},
    "content_creation": {"weight": 0.7, "apps": [], "titles": ["YouTube Studio", "Creator Studio"]},
    "product_work": {"weight": 0.8, "apps": [], "titles": ["Darwin", "Onsa", "Empatika"]},
    "social_media": {"weight": -0.3, "apps": [], "titles": ["Twitter", "Home / X", "LinkedIn", "Reddit"]},
    "entertainment": {"weight": -0.5, "apps": ["Netflix", "Spotify"], "titles": ["Netflix", "Prime Video", "Paramount+", "Watch ", "Landman"]},
    "news": {"weight": -0.2, "apps": [], "titles": ["News", "Редакция", "Hacker News"]},
    "system": {"weight": 0.0, "apps": ["loginwindow", "Finder", "SystemUIServer", "UserNotificationCenter"], "titles": ["Finder"]},
    "browser_idle": {"weight": 0.0, "apps": [], "titles": ["New Tab", "Untitled"]}
}

def load_category_rules(config_path: Optional[str] = None) -> dict:
    """Load category rules from config file or use defaults."""
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Remove comments
                return {k: v for k, v in config.items() if not k.startswith('_')}
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}", file=sys.stderr)
    return DEFAULT_CATEGORY_RULES

CATEGORY_RULES = dict(DEFAULT_CATEGORY_RULES)  # Mutable copy, will be updated when analyze is called

# Apps that should have title-level breakdown
BROWSER_APPS = ["Google Chrome", "Safari", "Firefox", "Arc", "Brave", "Edge",
                "ChatGPT Atlas", "Opera", "Vivaldi"]

# ============================================================================
# AI AGENT DETECTION
# ============================================================================

def detect_ai_agent(title: str) -> Optional[str]:
    """
    Detect if a Terminal window title indicates an AI coding agent is running.
    Returns agent name or None.

    Supported agents:
    - Claude Code: "✳ Task Name" prefix or "claude" in title
    - OpenAI Codex CLI: "codex" in title
    - Aider: "aider" in title
    - Cursor Agent: "cursor" with agent indicators
    """
    title_lower = title.lower()

    # Claude Code: Uses "✳" prefix for task names, or "claude" command
    if '✳' in title or ('claude' in title_lower and 'code' not in title_lower):
        return 'claude_code'

    # OpenAI Codex CLI: "codex" in title
    if 'codex' in title_lower:
        return 'codex'

    # Aider: "aider" in title
    if 'aider' in title_lower:
        return 'aider'

    # GitHub Copilot CLI: "gh copilot" in title
    if 'gh copilot' in title_lower or 'github copilot' in title_lower:
        return 'copilot'

    return None


def categorize_activity(app: str, title: str) -> Tuple[str, float]:
    """
    Categorize an activity based on app and title.
    Returns (category_name, productivity_weight)
    """
    title_lower = title.lower()
    
    for category, rules in CATEGORY_RULES.items():
        # Check app match
        for app_pattern in rules["apps"]:
            if app_pattern.lower() in app.lower():
                return category, rules["weight"]
        
        # Check title match
        for title_pattern in rules["titles"]:
            if title_pattern.lower() in title_lower:
                return category, rules["weight"]
    
    # Default: uncategorized
    return "uncategorized", 0.0


def analyze_csv_enhanced(filepath: str, days: Optional[int] = None, tz_name: Optional[str] = None) -> dict:
    """Enhanced analysis with categorization and AI agent detection.

    Args:
        filepath: Path to ActivityWatch CSV export
        days: Optional number of days to analyze (from most recent)
        tz_name: Timezone name (e.g., 'America/Los_Angeles'). Defaults to system local.
    """

    # Set up timezone
    if tz_name:
        try:
            local_tz = ZoneInfo(tz_name)
        except Exception:
            print(f"Warning: Unknown timezone '{tz_name}', using system local", file=sys.stderr)
            local_tz = datetime.now().astimezone().tzinfo
    else:
        local_tz = datetime.now().astimezone().tzinfo

    # Data structures
    app_time = defaultdict(float)
    category_time = defaultdict(float)
    hourly_activity = defaultdict(float)
    hourly_by_category = defaultdict(lambda: defaultdict(float))
    daily_activity = defaultdict(float)
    daily_by_category = defaultdict(lambda: defaultdict(float))
    hourly_switches = defaultdict(int)
    switches = []

    # Title-level tracking for browsers
    browser_titles = defaultdict(float)
    browser_title_categories = defaultdict(lambda: defaultdict(float))

    # AI Agent tracking
    ai_agent_time = defaultdict(float)  # agent_name -> total seconds
    ai_assisted_switches = []  # switches that occurred during AI agent sessions
    current_ai_agent = None  # currently active AI agent (if any)
    terminal_titles_by_switch = {}  # switch_index -> terminal_title (for later analysis)

    # Idle time tracking (loginwindow, screensaver, etc.)
    idle_time = 0.0
    idle_apps = {'loginwindow', 'ScreenSaverEngine', 'LockScreen'}

    # Activity details for productivity calculation
    weighted_time = 0.0
    total_active_time = 0.0

    prev_app = None
    prev_title = None
    total_events = 0
    
    cutoff = None
    if days:
        cutoff = datetime.now(local_tz) - timedelta(days=days)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_events += 1

            ts_str = row.get('timestamp', '')
            try:
                # Parse UTC timestamp and convert to local timezone
                ts_utc = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts = ts_utc.astimezone(local_tz)
            except:
                continue

            if cutoff and ts < cutoff:
                continue

            duration = float(row.get('duration', 0))
            app = row.get('app', 'Unknown')
            title = row.get('title', '')

            # Track idle time separately (loginwindow, screensaver, etc.)
            if app in idle_apps:
                idle_time += duration
                continue

            # Detect AI agent in Terminal
            if app == 'Terminal':
                agent = detect_ai_agent(title)
                if agent:
                    current_ai_agent = agent
                    ai_agent_time[agent] += duration

            # Categorize
            category, weight = categorize_activity(app, title)

            # Aggregate by app
            app_time[app] += duration

            # Aggregate by category
            category_time[category] += duration

            # Aggregate by hour (using LOCAL timezone)
            hour = ts.hour
            hourly_activity[hour] += duration
            hourly_by_category[hour][category] += duration

            # Aggregate by day (using LOCAL timezone)
            day = ts.strftime("%Y-%m-%d")
            daily_activity[day] += duration
            daily_by_category[day][category] += duration
            
            # Browser title breakdown
            if app in BROWSER_APPS:
                # Normalize title (take first 60 chars, clean up)
                clean_title = title[:60].strip()
                if clean_title and clean_title not in ['New Tab', 'Untitled', '']:
                    browser_titles[clean_title] += duration
                    browser_title_categories[category][clean_title] += duration
            
            # Productivity calculation (only for active categories)
            if category not in ['system', 'browser_idle']:
                weighted_time += duration * weight
                total_active_time += duration
            
            # Track switches
            if prev_app and prev_app != app:
                switch_idx = len(switches)
                switch_data = {
                    "from": prev_app,
                    "to": app,
                    "hour": hour,
                    "day": day,
                    "ai_agent": None
                }

                # Check if this switch involves Terminal with AI agent
                # Only count as AI-assisted if the OTHER app is NOT distracting
                if prev_app == 'Terminal' or app == 'Terminal':
                    # Get the terminal title (current or previous)
                    terminal_title = title if app == 'Terminal' else prev_title
                    if terminal_title:
                        agent = detect_ai_agent(terminal_title)
                        if agent:
                            switch_data["ai_agent"] = agent
                            terminal_titles_by_switch[switch_idx] = terminal_title
                            # Only exclude from focus penalty if other app is NOT distracting
                            other_app = prev_app if app == 'Terminal' else app
                            other_cat, _ = categorize_activity(other_app, "")
                            if other_cat not in ['communication_personal', 'social_media', 'entertainment']:
                                ai_assisted_switches.append(switch_idx)

                switches.append(switch_data)
                hourly_switches[hour] += 1

            prev_app = app
            prev_title = title
    
    # Detect death loops with AI agent awareness
    pair_counts = defaultdict(int)
    pair_ai_counts = defaultdict(int)  # Count of AI-assisted switches per pair
    pair_agents = defaultdict(lambda: defaultdict(int))  # Track which agents per pair

    for i, s in enumerate(switches):
        pair = tuple(sorted([s["from"], s["to"]]))
        pair_counts[pair] += 1
        if s.get("ai_agent"):
            pair_ai_counts[pair] += 1
            pair_agents[pair][s["ai_agent"]] += 1

    death_loops = sorted(
        [{"apps": list(k), "count": v, "description": f"{k[0]} ↔ {k[1]}"}
         for k, v in pair_counts.items() if v >= 20],
        key=lambda x: x["count"],
        reverse=True
    )[:10]

    # Annotate death loops with category info AND AI agent detection
    # PRIORITY: Check distracting apps FIRST, then AI-assisted
    distracting_categories = ['communication_personal', 'social_media', 'entertainment']

    for loop in death_loops:
        pair = tuple(sorted(loop["apps"]))
        app1_cat, _ = categorize_activity(loop["apps"][0], "")
        app2_cat, _ = categorize_activity(loop["apps"][1], "")

        # 1. FIRST check if either app is distracting - always flag these
        if app1_cat in distracting_categories:
            loop["verdict"] = "distracting"
            loop["suggestion"] = f"Block {loop['apps'][0]} during focus hours"
        elif app2_cat in distracting_categories:
            loop["verdict"] = "distracting"
            loop["suggestion"] = f"Block {loop['apps'][1]} during focus hours"
        else:
            # 2. Only check AI-assisted if neither app is distracting
            ai_count = pair_ai_counts.get(pair, 0)
            total_count = loop["count"]
            ai_ratio = ai_count / total_count if total_count > 0 else 0

            if ai_ratio > 0.3:  # More than 30% of switches had AI agent
                # Find the most common agent
                agents = pair_agents.get(pair, {})
                top_agent = max(agents.items(), key=lambda x: x[1])[0] if agents else "unknown"
                loop["verdict"] = "ai_assisted"
                loop["ai_agent"] = top_agent
                loop["ai_switches"] = ai_count
                loop["suggestion"] = f"AI-assisted development ({top_agent}) - productive workflow"
            elif app1_cat in ['deep_work', 'development'] and app2_cat in ['deep_work', 'development']:
                loop["verdict"] = "productive"
                loop["suggestion"] = "Normal dev workflow - consider split screen"
            else:
                loop["verdict"] = "mixed"
                loop["suggestion"] = "Consider batching these activities"
    
    # Calculate totals
    total_time = sum(app_time.values())
    total_switches = len(switches)
    days_tracked = len(daily_activity)
    
    # Productivity score (weighted average, scaled to 0-100)
    if total_active_time > 0:
        raw_productivity = weighted_time / total_active_time
        # Scale from [-0.5, 1.0] to [0, 100]
        productivity_score = int(((raw_productivity + 0.5) / 1.5) * 100)
        productivity_score = max(0, min(100, productivity_score))
    else:
        productivity_score = 0
    
    # Focus score (based on context switching, excluding AI-assisted switches)
    active_hours = sum(1 for h in hourly_activity.values() if h > 300)
    human_switches = total_switches - len(ai_assisted_switches)
    switches_per_active_hour = human_switches / max(1, active_hours)

    if switches_per_active_hour < 50:
        focus_score = 85
    elif switches_per_active_hour < 100:
        focus_score = 70
    elif switches_per_active_hour < 200:
        focus_score = 55
    else:
        focus_score = 40
    
    # Combined score
    combined_score = int(productivity_score * 0.6 + focus_score * 0.4)
    
    # Top apps (sorted by time)
    sorted_apps = sorted(app_time.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Category breakdown
    sorted_categories = sorted(category_time.items(), key=lambda x: x[1], reverse=True)
    
    # Top browser activities
    sorted_browser = sorted(browser_titles.items(), key=lambda x: x[1], reverse=True)[:30]
    
    # Find best and worst hours
    productive_categories = ['deep_work', 'ai_tools', 'development', 'writing', 'design']
    
    hourly_productivity = {}
    for hour in range(24):
        hour_total = hourly_activity.get(hour, 0)
        if hour_total < 300:  # Less than 5 min
            continue
        productive_time = sum(hourly_by_category[hour].get(cat, 0) for cat in productive_categories)
        hourly_productivity[hour] = {
            "total_hours": round(hour_total / 3600, 2),
            "productive_hours": round(productive_time / 3600, 2),
            "productive_pct": round(productive_time / hour_total * 100, 1) if hour_total > 0 else 0,
            "switches": hourly_switches.get(hour, 0)
        }
    
    # Find peak productive hours
    peak_hours = sorted(
        [(h, d) for h, d in hourly_productivity.items()],
        key=lambda x: x[1]["productive_pct"],
        reverse=True
    )[:5]
    
    # Find distraction danger zones
    danger_hours = sorted(
        [(h, d) for h, d in hourly_productivity.items()],
        key=lambda x: x[1]["switches"],
        reverse=True
    )[:5]
    
    # Daily productivity trend
    daily_scores = {}
    for day in sorted(daily_activity.keys()):
        day_total = daily_activity[day]
        productive_time = sum(daily_by_category[day].get(cat, 0) for cat in productive_categories)
        daily_scores[day] = {
            "total_hours": round(day_total / 3600, 2),
            "productive_hours": round(productive_time / 3600, 2),
            "productive_pct": round(productive_time / day_total * 100, 1) if day_total > 0 else 0
        }
    
    # Build summary
    summary = {
        "period": {
            "days_tracked": days_tracked,
            "total_events": total_events,
            "date_range": f"{min(daily_activity.keys())} to {max(daily_activity.keys())}" if daily_activity else "N/A"
        },
        
        "scores": {
            "combined_score": combined_score,
            "productivity_score": productivity_score,
            "focus_score": focus_score,
            "interpretation": (
                "Excellent" if combined_score >= 80 else
                "Good" if combined_score >= 60 else
                "Moderate" if combined_score >= 40 else
                "Needs improvement"
            )
        },
        
        "time_totals": {
            "tracked_hours": round((total_time + idle_time) / 3600, 2),
            "active_hours": round(total_time / 3600, 2),
            "idle_hours": round(idle_time / 3600, 2),
            "average_active_per_day": round(total_time / 3600 / max(1, days_tracked), 2),
            "timezone": str(local_tz)
        },
        
        "category_breakdown": [
            {
                "category": cat,
                "hours": round(secs / 3600, 2),
                "percentage": round(secs / total_time * 100, 1) if total_time > 0 else 0,
                "weight": CATEGORY_RULES.get(cat, {}).get("weight", 0)
            }
            for cat, secs in sorted_categories
        ],
        
        "top_apps": [
            {
                "name": app,
                "hours": round(secs / 3600, 2),
                "percentage": round(secs / total_time * 100, 1) if total_time > 0 else 0,
                "category": categorize_activity(app, "")[0]
            }
            for app, secs in sorted_apps
        ],
        
        "browser_breakdown": [
            {
                "title": title[:60],
                "hours": round(secs / 3600, 2),
                "category": categorize_activity("browser", title)[0]
            }
            for title, secs in sorted_browser
        ],
        
        "hourly_analysis": {
            "peak_productive_hours": [
                {"hour": h, **data} for h, data in peak_hours
            ],
            "danger_zones": [
                {"hour": h, **data} for h, data in danger_hours
            ],
            "full_breakdown": hourly_productivity
        },
        
        "daily_trend": daily_scores,
        
        "context_switching": {
            "total_switches": total_switches,
            "human_switches": human_switches,
            "ai_assisted_switches": len(ai_assisted_switches),
            "average_per_day": round(human_switches / max(1, days_tracked), 1),
            "switches_per_hour": round(switches_per_active_hour, 1)
        },

        "ai_assisted_development": {
            "total_hours": round(sum(ai_agent_time.values()) / 3600, 2),
            "agents_detected": {
                agent: round(secs / 3600, 2)
                for agent, secs in sorted(ai_agent_time.items(), key=lambda x: x[1], reverse=True)
            },
            "switches_during_ai": len(ai_assisted_switches),
            "interpretation": "Productive human-AI collaboration" if ai_agent_time else "No AI agents detected"
        },

        "death_loops": death_loops,
        
        "insights": generate_insights(
            sorted_categories, death_loops, peak_hours, danger_hours,
            productivity_score, focus_score, sorted_browser
        )
    }
    
    return summary


def generate_insights(categories, death_loops, peak_hours, danger_hours, 
                     prod_score, focus_score, browser_activities) -> dict:
    """Generate actionable insights from the data."""
    
    insights = {
        "top_insight": "",
        "productivity_drivers": [],
        "productivity_drains": [],
        "schedule_recommendations": [],
        "one_change": ""
    }
    
    # Productivity drivers
    productive_cats = ['deep_work', 'ai_tools', 'development', 'writing', 'design']
    for cat, secs in categories:
        if cat in productive_cats and secs > 3600:  # More than 1 hour
            insights["productivity_drivers"].append({
                "category": cat,
                "hours": round(secs / 3600, 1),
                "impact": "positive"
            })
    
    # Productivity drains
    drain_cats = ['entertainment', 'social_media', 'news']
    for cat, secs in categories:
        if cat in drain_cats and secs > 1800:  # More than 30 min
            insights["productivity_drains"].append({
                "category": cat,
                "hours": round(secs / 3600, 1),
                "impact": "negative"
            })
    
    # Schedule recommendations
    if peak_hours:
        best_hour = peak_hours[0][0]
        insights["schedule_recommendations"].append(
            f"Schedule deep work around {best_hour}:00-{(best_hour+2)%24}:00 (your peak productive time)"
        )
    
    if danger_hours:
        worst_hour = danger_hours[0][0]
        if worst_hour < 6 or worst_hour >= 23:
            insights["schedule_recommendations"].append(
                f"Late night work ({worst_hour}:00) shows high context switching - consider ending earlier"
            )
    
    # Top insight
    if focus_score < 50:
        insights["top_insight"] = "High context switching is fragmenting your attention"
    elif prod_score < 50:
        insights["top_insight"] = "Entertainment/distraction time is eating into productive hours"
    elif prod_score >= 70 and focus_score >= 70:
        insights["top_insight"] = "Strong productivity patterns - focus on maintaining consistency"
    else:
        insights["top_insight"] = "Mixed patterns - small improvements in focus will compound"
    
    # One change recommendation
    if death_loops:
        # Find the first non-AI-assisted problematic loop
        worst_loop = None
        for loop in death_loops:
            if loop.get("verdict") == "distracting":
                worst_loop = loop
                break
            elif loop.get("verdict") == "mixed" and worst_loop is None:
                worst_loop = loop

        if worst_loop and worst_loop.get("verdict") == "distracting":
            insights["one_change"] = worst_loop.get("suggestion", "Block distracting app during focus hours")
        else:
            # Look for distracting browser content
            for title, secs in browser_activities[:10]:
                cat, _ = categorize_activity("browser", title)
                if cat in ['entertainment', 'social_media'] and secs > 3600:
                    insights["one_change"] = f"Block '{title[:30]}' during work hours (spent {round(secs/3600, 1)}h)"
                    break
            else:
                insights["one_change"] = "Batch check communication apps 3x daily instead of continuously"

    if not insights["one_change"]:
        insights["one_change"] = "Protect your peak productive hours by blocking notifications"
    
    return insights


def format_report(summary: dict) -> str:
    """Format summary as a readable markdown report."""
    
    report = []
    report.append("# Weekly Focus Report\n")
    report.append(f"**Period:** {summary['period']['date_range']}")
    report.append(f"**Days tracked:** {summary['period']['days_tracked']}")

    # Time totals
    time_totals = summary.get('time_totals', {})
    tz = time_totals.get('timezone', 'Unknown')
    tracked = time_totals.get('tracked_hours', 0)
    active = time_totals.get('active_hours', 0)
    idle = time_totals.get('idle_hours', 0)
    report.append(f"**Timezone:** {tz}")
    report.append(f"**Time:** {active:.1f}h active + {idle:.1f}h idle = {tracked:.1f}h tracked\n")
    
    # Scores
    scores = summary['scores']
    report.append("## 📊 Scores\n")
    report.append(f"| Metric | Score | Interpretation |")
    report.append(f"|--------|-------|----------------|")
    report.append(f"| **Combined** | {scores['combined_score']}/100 | {scores['interpretation']} |")
    report.append(f"| Productivity | {scores['productivity_score']}/100 | How much time on productive work |")
    report.append(f"| Focus | {scores['focus_score']}/100 | How well you maintained attention |")
    report.append("")
    
    # Category breakdown
    report.append("## 🎯 Time by Category\n")
    report.append("| Category | Hours | % | Type |")
    report.append("|----------|-------|---|------|")
    for cat in summary['category_breakdown'][:10]:
        weight = cat['weight']
        if weight >= 0.7:
            cat_type = "🟢 Productive"
        elif weight >= 0.3:
            cat_type = "🟡 Mixed"
        elif weight >= 0:
            cat_type = "⚪ Neutral"
        else:
            cat_type = "🔴 Distracting"
        report.append(f"| {cat['category']} | {cat['hours']}h | {cat['percentage']}% | {cat_type} |")
    report.append("")
    
    # Browser breakdown
    if summary['browser_breakdown']:
        report.append("## 🌐 Browser Activity Breakdown\n")
        report.append("| Activity | Hours | Category |")
        report.append("|----------|-------|----------|")
        for item in summary['browser_breakdown'][:15]:
            report.append(f"| {item['title'][:50]} | {item['hours']}h | {item['category']} |")
        report.append("")
    
    # AI-Assisted Development (if detected)
    ai_dev = summary.get('ai_assisted_development', {})
    if ai_dev.get('agents_detected'):
        report.append("## 🤖 AI-Assisted Development\n")
        report.append("| Agent | Hours | Switches |")
        report.append("|-------|-------|----------|")
        switches_per_agent = ai_dev.get('switches_during_ai', 0) // max(1, len(ai_dev['agents_detected']))
        for agent, hours in ai_dev['agents_detected'].items():
            report.append(f"| {agent} | {hours}h | ~{switches_per_agent} |")
        report.append("")
        report.append(f"*{ai_dev.get('interpretation', '')}. These switches are excluded from focus score.*\n")

    # Death loops
    if summary['death_loops']:
        report.append("## 🔄 Context Switching Patterns\n")
        report.append("| Loop | Count | Verdict | Suggestion |")
        report.append("|------|-------|---------|------------|")
        for loop in summary['death_loops'][:5]:
            verdict = loop.get('verdict', 'mixed')
            if verdict == 'ai_assisted':
                verdict_emoji = "🤖"
            elif verdict == 'productive':
                verdict_emoji = "🟢"
            elif verdict == 'distracting':
                verdict_emoji = "🔴"
            else:
                verdict_emoji = "🟡"
            report.append(f"| {loop['description']} | {loop['count']} | {verdict_emoji} {verdict} | {loop.get('suggestion', '-')} |")
        report.append("")
    
    # Insights
    insights = summary['insights']
    report.append("## 💡 Key Insights\n")
    report.append(f"**Top Insight:** {insights['top_insight']}\n")
    
    if insights['schedule_recommendations']:
        report.append("**Schedule Recommendations:**")
        for rec in insights['schedule_recommendations']:
            report.append(f"- {rec}")
        report.append("")
    
    report.append(f"### 🎯 One Change for Next Week\n")
    report.append(f"> {insights['one_change']}")
    
    return "\n".join(report)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python analyze_aw.py <csv_file> [--report] [--config config.json] [--timezone America/Los_Angeles]")
        sys.exit(1)

    filepath = sys.argv[1]
    output_report = "--report" in sys.argv

    # Load custom config if provided
    config_path = None
    if "--config" in sys.argv:
        config_idx = sys.argv.index("--config")
        if config_idx + 1 < len(sys.argv):
            config_path = sys.argv[config_idx + 1]

    # Get timezone if provided (default: system local)
    tz_name = None
    if "--timezone" in sys.argv:
        tz_idx = sys.argv.index("--timezone")
        if tz_idx + 1 < len(sys.argv):
            tz_name = sys.argv[tz_idx + 1]

    # Update CATEGORY_RULES module-level variable
    if config_path:
        loaded_rules = load_category_rules(config_path)
        CATEGORY_RULES.clear()
        CATEGORY_RULES.update(loaded_rules)

    summary = analyze_csv_enhanced(filepath, tz_name=tz_name)

    if output_report:
        print(format_report(summary))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
