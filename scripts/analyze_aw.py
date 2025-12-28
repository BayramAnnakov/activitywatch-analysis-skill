#!/usr/bin/env python3
"""
ActivityWatch Analyzer
- Smart auto-categorization of apps and window titles
- Personalized productivity scoring
- Title-level breakdown for browsers
- Weekly narrative insights
- Direct ActivityWatch API integration (optional)
"""

import csv
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from zoneinfo import ZoneInfo

# Optional: ActivityWatch client for direct API access
try:
    from aw_client import ActivityWatchClient
    AW_CLIENT_AVAILABLE = True
except ImportError:
    AW_CLIENT_AVAILABLE = False

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
                "ChatGPT Atlas", "Opera", "Vivaldi", "Chromium"]

# ============================================================================
# SITE EXTRACTION FROM BROWSER TITLES
# ============================================================================

# Known sites by keyword in window title -> (site_name, category, weight)
KNOWN_SITES = {
    # Streaming / Entertainment
    'netflix': ('Netflix', 'entertainment', -0.5),
    'prime video': ('Prime Video', 'entertainment', -0.5),
    'paramount+': ('Paramount+', 'entertainment', -0.5),
    'paramount plus': ('Paramount+', 'entertainment', -0.5),
    'disney+': ('Disney+', 'entertainment', -0.5),
    'hulu': ('Hulu', 'entertainment', -0.5),
    'hbo max': ('HBO Max', 'entertainment', -0.5),
    'twitch': ('Twitch', 'entertainment', -0.4),
    'spotify': ('Spotify', 'entertainment', -0.3),

    # AI Tools
    'chatgpt': ('ChatGPT', 'ai_tools', 0.8),
    'claude.ai': ('Claude.ai', 'ai_tools', 0.8),
    'claude -': ('Claude.ai', 'ai_tools', 0.8),
    'perplexity': ('Perplexity', 'ai_tools', 0.8),
    'anthropic': ('Anthropic', 'ai_tools', 0.8),
    'openai platform': ('OpenAI', 'ai_tools', 0.8),
    'openai api': ('OpenAI', 'ai_tools', 0.8),
    'google ai studio': ('Google AI Studio', 'ai_tools', 0.8),
    'langsmith': ('LangSmith', 'ai_tools', 0.8),
    'langchain': ('LangChain', 'ai_tools', 0.8),

    # Development
    'github': ('GitHub', 'development', 0.9),
    'gitlab': ('GitLab', 'development', 0.9),
    'localhost': ('Localhost', 'development', 1.0),
    '127.0.0.1': ('Localhost', 'development', 1.0),
    'supabase': ('Supabase', 'development', 0.8),
    'vercel': ('Vercel', 'development', 0.8),
    'netlify': ('Netlify', 'development', 0.8),
    'fly.io': ('Fly.io', 'development', 0.8),
    'railway': ('Railway', 'development', 0.8),
    'render.com': ('Render', 'development', 0.8),
    'heroku': ('Heroku', 'development', 0.8),
    'aws console': ('AWS', 'development', 0.8),
    'stack overflow': ('Stack Overflow', 'development', 0.8),
    'stackoverflow': ('Stack Overflow', 'development', 0.8),
    'devtools': ('DevTools', 'development', 0.9),
    'pagespeed': ('PageSpeed', 'development', 0.7),
    'n8n': ('n8n', 'development', 0.8),
    'postman': ('Postman', 'development', 0.8),

    # Design
    'figma': ('Figma', 'design', 0.9),
    'miro': ('Miro', 'design', 0.8),
    'canva': ('Canva', 'design', 0.8),
    'webflow': ('Webflow', 'design', 0.9),
    'framer': ('Framer', 'design', 0.9),

    # Writing & Docs
    'google docs': ('Google Docs', 'writing', 0.9),
    'notion': ('Notion', 'writing', 0.9),
    'obsidian': ('Obsidian', 'writing', 0.9),
    'medium': ('Medium', 'reading', 0.5),
    'substack': ('Substack', 'reading', 0.5),

    # Productivity
    'google sheets': ('Google Sheets', 'spreadsheets', 0.6),
    'google slides': ('Google Slides', 'presentations', 0.7),
    'google calendar': ('Google Calendar', 'productivity', 0.5),
    'airtable': ('Airtable', 'productivity', 0.6),
    'linear': ('Linear', 'productivity', 0.7),
    'jira': ('Jira', 'productivity', 0.6),
    'asana': ('Asana', 'productivity', 0.6),

    # Communication
    'gmail': ('Gmail', 'email', 0.3),
    'outlook': ('Outlook', 'email', 0.3),
    'slack': ('Slack', 'communication', 0.3),
    'discord': ('Discord', 'communication', 0.2),

    # Social Media
    'twitter': ('Twitter/X', 'social_media', -0.3),
    ' / x': ('Twitter/X', 'social_media', -0.3),
    'x.com': ('Twitter/X', 'social_media', -0.3),
    'linkedin': ('LinkedIn', 'social_media', -0.2),
    'facebook': ('Facebook', 'social_media', -0.3),
    'instagram': ('Instagram', 'social_media', -0.3),
    'reddit': ('Reddit', 'social_media', -0.3),
    'tiktok': ('TikTok', 'social_media', -0.4),

    # Learning
    'coursera': ('Coursera', 'learning', 0.8),
    'udemy': ('Udemy', 'learning', 0.8),
    'arxiv': ('arXiv', 'learning', 0.9),
    'deeplearning.ai': ('DeepLearning.AI', 'learning', 0.8),

    # News
    'hacker news': ('Hacker News', 'news', 0.2),
    'techcrunch': ('TechCrunch', 'news', 0.1),

    # Business
    'stripe': ('Stripe', 'business', 0.6),
    'paypal': ('PayPal', 'business', 0.5),
    'hubspot': ('HubSpot', 'business', 0.5),
    'salesforce': ('Salesforce', 'business', 0.5),
    'google analytics': ('Google Analytics', 'business', 0.6),
    'mixpanel': ('Mixpanel', 'business', 0.6),

    # Video (mixed - could be work or entertainment)
    'youtube': ('YouTube', 'video', 0.0),  # Neutral - could be learning or entertainment
    'loom': ('Loom', 'video', 0.6),
    'vimeo': ('Vimeo', 'video', 0.3),
}

def extract_site_from_title(title: str) -> Tuple[str, str, float]:
    """
    Extract site name from browser window title.
    Returns (site_name, category, weight).
    """
    title_lower = title.lower()

    # Check known sites
    for keyword, (site, category, weight) in KNOWN_SITES.items():
        if keyword in title_lower:
            return (site, category, weight)

    # Try to extract site from common title patterns
    # "Page Title - Site Name" or "Page Title | Site Name"
    for separator in [' - ', ' | ', ' – ', ' — ']:
        if separator in title:
            parts = title.rsplit(separator, 1)
            if len(parts) == 2 and len(parts[1]) < 40:
                site_name = parts[1].strip()
                # Check if extracted part is a known site
                site_lower = site_name.lower()
                for keyword, (site, category, weight) in KNOWN_SITES.items():
                    if keyword in site_lower:
                        return (site, category, weight)
                return (site_name, 'uncategorized', 0.0)

    # Fallback: use truncated title
    if len(title) > 40:
        return (title[:37] + '...', 'uncategorized', 0.0)
    return (title if title else 'Unknown', 'uncategorized', 0.0)


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


# ============================================================================
# ACTIVITYWATCH API INTEGRATION
# ============================================================================

def fetch_from_activitywatch(
    start_date: datetime,
    end_date: datetime,
    tz_name: Optional[str] = None,
    bucket_id: Optional[str] = None
) -> Optional[str]:
    """
    Fetch events directly from ActivityWatch API and save to temporary CSV.

    Args:
        start_date: Start datetime (in local timezone)
        end_date: End datetime (in local timezone)
        tz_name: Timezone name (e.g., 'America/Los_Angeles')
        bucket_id: Specific bucket ID (auto-detected if None)

    Returns:
        Path to temporary CSV file, or None if failed
    """
    if not AW_CLIENT_AVAILABLE:
        print("Error: aw-client not installed. Install with: pip install aw-client", file=sys.stderr)
        return None

    try:
        # Set up timezone
        if tz_name:
            local_tz = ZoneInfo(tz_name)
        else:
            local_tz = datetime.now().astimezone().tzinfo

        # Ensure dates have timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)

        client = ActivityWatchClient("analyze-productivity")

        # Auto-detect bucket if not specified
        if not bucket_id:
            buckets = client.get_buckets()
            window_buckets = [b for b in buckets.keys() if 'aw-watcher-window' in b]
            if not window_buckets:
                print("Error: No window watcher bucket found in ActivityWatch", file=sys.stderr)
                return None
            bucket_id = window_buckets[0]
            print(f"Using bucket: {bucket_id}", file=sys.stderr)

        # Fetch events
        events = client.get_events(bucket_id, start=start_date, end=end_date, limit=-1)
        print(f"Fetched {len(events)} events from ActivityWatch", file=sys.stderr)

        if not events:
            print("Warning: No events found for the specified period", file=sys.stderr)
            return None

        # Write to temporary CSV
        fd, temp_path = tempfile.mkstemp(suffix='.csv', prefix='aw_export_')
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'duration', 'app', 'title'])
            for e in events:
                writer.writerow([
                    e.timestamp.isoformat(),
                    e.duration.total_seconds(),
                    e.data.get('app', 'Unknown'),
                    e.data.get('title', '')
                ])

        return temp_path

    except Exception as e:
        print(f"Error fetching from ActivityWatch: {e}", file=sys.stderr)
        return None


def fetch_web_watcher_data(
    start_date: datetime,
    end_date: datetime,
    tz_name: Optional[str] = None
) -> Optional[List[dict]]:
    """
    Fetch browser extension data from ActivityWatch (aw-watcher-web-chrome).

    Returns list of events with URL, title, duration, audible status.
    """
    if not AW_CLIENT_AVAILABLE:
        return None

    try:
        # Set up timezone
        if tz_name:
            local_tz = ZoneInfo(tz_name)
        else:
            local_tz = datetime.now().astimezone().tzinfo

        # Ensure dates have timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)

        client = ActivityWatchClient("analyze-productivity")

        # Find web watcher bucket
        buckets = client.get_buckets()
        web_buckets = [b for b in buckets.keys() if 'aw-watcher-web' in b]
        if not web_buckets:
            return None

        bucket_id = web_buckets[0]

        # Fetch events
        events = client.get_events(bucket_id, start=start_date, end=end_date, limit=-1)

        if not events:
            return None

        # Process events
        result = []
        for e in events:
            url = e.data.get('url', '')
            # Extract domain from URL
            domain = ''
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace('www.', '')
                except:
                    domain = url[:50]

            result.append({
                'timestamp': e.timestamp.isoformat(),
                'duration': e.duration.total_seconds(),
                'url': url,
                'domain': domain,
                'title': e.data.get('title', ''),
                'audible': e.data.get('audible', False),
                'incognito': e.data.get('incognito', False),
                'tab_count': e.data.get('tabCount', 0)
            })

        return result

    except Exception as e:
        print(f"Note: Could not fetch web watcher data: {e}", file=sys.stderr)
        return None


def analyze_web_data(web_events: List[dict]) -> dict:
    """
    Analyze browser extension data for domain-level insights.

    Returns:
        - domain_breakdown: time by domain
        - audible_time: time with audio/video playing
        - productive_domains: categorized domains
        - tab_stats: average tab count
    """
    if not web_events:
        return {}

    domain_time = defaultdict(float)
    audible_time = 0.0
    total_time = 0.0
    tab_counts = []

    # Domain categorization
    PRODUCTIVE_DOMAINS = {
        # Development
        'github.com': ('development', 0.8),
        'gitlab.com': ('development', 0.8),
        'stackoverflow.com': ('learning', 0.7),
        'supabase.com': ('development', 0.8),
        'vercel.com': ('development', 0.8),
        'console.cloud.google.com': ('development', 0.7),
        'aws.amazon.com': ('development', 0.7),
        'cloud.google.com': ('development', 0.7),
        'us.cloud.langfuse.com': ('development', 0.7),
        'langfuse.com': ('development', 0.7),
        'fly.io': ('development', 0.7),
        'railway.app': ('development', 0.7),
        'render.com': ('development', 0.7),

        # AI Tools
        'anthropic.com': ('ai_tools', 0.8),
        'openai.com': ('ai_tools', 0.8),
        'chatgpt.com': ('ai_tools', 0.8),
        'claude.ai': ('ai_tools', 0.8),
        'ai.google.dev': ('ai_tools', 0.8),
        'aistudio.google.com': ('ai_tools', 0.8),
        'perplexity.ai': ('ai_tools', 0.7),
        'huggingface.co': ('ai_tools', 0.8),

        # Writing & Docs
        'docs.google.com': ('writing', 0.7),
        'notion.so': ('writing', 0.8),
        'coda.io': ('writing', 0.7),
        'obsidian.md': ('writing', 0.8),

        # Design
        'figma.com': ('design', 0.9),
        'canva.com': ('design', 0.7),
        'webflow.com': ('design', 0.8),

        # Business/Marketing
        'ads.google.com': ('marketing', 0.6),
        'analytics.google.com': ('analytics', 0.6),
        'search.google.com': ('research', 0.5),
        'studio.youtube.com': ('content_creation', 0.7),
        'business.facebook.com': ('marketing', 0.5),
        'stripe.com': ('business', 0.6),

        # Email
        'mail.google.com': ('email', 0.4),
        'outlook.com': ('email', 0.4),
        'outlook.office.com': ('email', 0.4),

        # Product work
        'linear.app': ('product_work', 0.8),
        'jira.atlassian.com': ('product_work', 0.6),
        'trello.com': ('product_work', 0.6),
        'asana.com': ('product_work', 0.6),

        # Learning
        'coursera.org': ('learning', 0.8),
        'udemy.com': ('learning', 0.7),
        'edx.org': ('learning', 0.8),
    }

    DISTRACTING_DOMAINS = {
        'youtube.com': ('video', -0.2),  # Neutral - could be learning or entertainment
        'netflix.com': ('entertainment', -0.5),
        'twitter.com': ('social_media', -0.3),
        'x.com': ('social_media', -0.3),
        'reddit.com': ('social_media', -0.3),
        'facebook.com': ('social_media', -0.4),
        'instagram.com': ('social_media', -0.4),
        'tiktok.com': ('social_media', -0.5),
        'linkedin.com': ('social_media', -0.2),  # Can be work-related
        'twitch.tv': ('entertainment', -0.4),
        'primevideo.com': ('entertainment', -0.5),
        'disneyplus.com': ('entertainment', -0.5),
        'hulu.com': ('entertainment', -0.5),
        'hbomax.com': ('entertainment', -0.5),
        'paramountplus.com': ('entertainment', -0.5),
    }

    for event in web_events:
        duration = event['duration']
        domain = event['domain']

        domain_time[domain] += duration
        total_time += duration

        if event['audible']:
            audible_time += duration

        if event['tab_count'] > 0:
            tab_counts.append(event['tab_count'])

    # Convert to hours and sort by time
    domain_breakdown = []
    for domain, seconds in sorted(domain_time.items(), key=lambda x: -x[1])[:20]:
        hours = seconds / 3600
        if hours < 0.01:  # Skip domains with less than 30 seconds
            continue

        # Categorize domain
        category = 'uncategorized'
        weight = 0.0
        productive = 'neutral'

        if domain in PRODUCTIVE_DOMAINS:
            category, weight = PRODUCTIVE_DOMAINS[domain]
            productive = 'yes'
        elif domain in DISTRACTING_DOMAINS:
            category, weight = DISTRACTING_DOMAINS[domain]
            productive = 'no'

        domain_breakdown.append({
            'domain': domain,
            'hours': round(hours, 2),
            'category': category,
            'weight': weight,
            'productive': productive
        })

    # Calculate stats
    avg_tabs = sum(tab_counts) / len(tab_counts) if tab_counts else 0
    max_tabs = max(tab_counts) if tab_counts else 0

    return {
        'domain_breakdown': domain_breakdown,
        'total_browser_hours': round(total_time / 3600, 2),
        'audible_hours': round(audible_time / 3600, 2),
        'audible_pct': round((audible_time / total_time * 100) if total_time > 0 else 0, 1),
        'avg_tabs': round(avg_tabs, 1),
        'max_tabs': max_tabs
    }


def parse_date_arg(date_str: str, tz_name: Optional[str] = None) -> Optional[datetime]:
    """
    Parse a date argument in various formats.

    Supports:
        - 'today', 'yesterday', 'week'
        - YYYY-MM-DD
        - Relative: '7d' (7 days ago), '2w' (2 weeks ago)
    """
    if tz_name:
        local_tz = ZoneInfo(tz_name)
    else:
        local_tz = datetime.now().astimezone().tzinfo

    now = datetime.now(local_tz)
    date_str = date_str.lower().strip()

    if date_str == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == 'yesterday':
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == 'week':
        return (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str.endswith('d') and date_str[:-1].isdigit():
        days = int(date_str[:-1])
        return (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str.endswith('w') and date_str[:-1].isdigit():
        weeks = int(date_str[:-1])
        return (now - timedelta(weeks=weeks)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            parsed = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed.replace(tzinfo=local_tz)
        except ValueError:
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

    # Site-level tracking for browsers (aggregated by domain/site)
    browser_sites = defaultdict(lambda: {"time": 0.0, "category": "", "weight": 0.0})
    browser_total_time = 0.0

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
                browser_total_time += duration
                # Normalize title (take first 60 chars, clean up)
                clean_title = title[:60].strip()
                if clean_title and clean_title not in ['New Tab', 'Untitled', '']:
                    browser_titles[clean_title] += duration
                    browser_title_categories[category][clean_title] += duration

                    # Extract site and aggregate
                    site_name, site_cat, site_weight = extract_site_from_title(title)
                    browser_sites[site_name]["time"] += duration
                    browser_sites[site_name]["category"] = site_cat
                    browser_sites[site_name]["weight"] = site_weight
            
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

        "browser_sites": sorted(
            [
                {
                    "site": site,
                    "hours": round(data["time"] / 3600, 2),
                    "category": data["category"],
                    "weight": data["weight"],
                    "productive": "yes" if data["weight"] >= 0.5 else ("neutral" if data["weight"] >= 0 else "no")
                }
                for site, data in browser_sites.items()
            ],
            key=lambda x: -x["hours"]
        )[:20],

        "browser_productivity": {
            "total_hours": round(browser_total_time / 3600, 2),
            "productive_hours": round(sum(d["time"] for d in browser_sites.values() if d["weight"] >= 0.5) / 3600, 2),
            "neutral_hours": round(sum(d["time"] for d in browser_sites.values() if 0 <= d["weight"] < 0.5) / 3600, 2),
            "distracting_hours": round(sum(d["time"] for d in browser_sites.values() if d["weight"] < 0) / 3600, 2),
            "productive_pct": round(sum(d["time"] for d in browser_sites.values() if d["weight"] >= 0.5) / max(1, browser_total_time) * 100, 1),
            "distracting_pct": round(sum(d["time"] for d in browser_sites.values() if d["weight"] < 0) / max(1, browser_total_time) * 100, 1),
        },

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
    
    # Browser productivity overview
    browser_prod = summary.get('browser_productivity', {})
    if browser_prod.get('total_hours', 0) > 0:
        report.append("## 🌐 Browser Activity\n")
        report.append(f"**Total browser time:** {browser_prod['total_hours']}h\n")
        report.append("| Type | Hours | % |")
        report.append("|------|-------|---|")
        report.append(f"| 🟢 Productive | {browser_prod['productive_hours']}h | {browser_prod['productive_pct']}% |")
        report.append(f"| 🟡 Neutral | {browser_prod['neutral_hours']}h | {round(100 - browser_prod['productive_pct'] - browser_prod['distracting_pct'], 1)}% |")
        report.append(f"| 🔴 Distracting | {browser_prod['distracting_hours']}h | {browser_prod['distracting_pct']}% |")
        report.append("")

    # Browser sites breakdown
    browser_sites = summary.get('browser_sites', [])
    if browser_sites:
        report.append("### Top Sites\n")
        report.append("| Site | Hours | Category | Type |")
        report.append("|------|-------|----------|------|")
        for item in browser_sites[:15]:
            if item['productive'] == 'yes':
                prod_icon = "🟢"
            elif item['productive'] == 'neutral':
                prod_icon = "🟡"
            else:
                prod_icon = "🔴"
            report.append(f"| {item['site'][:35]} | {item['hours']}h | {item['category']} | {prod_icon} |")
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

    # Check for help
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print("""ActivityWatch Analyzer

Usage:
    # Analyze from CSV file
    python analyze_aw.py <csv_file> [--report] [--timezone TZ] [--config FILE]

    # Fetch directly from ActivityWatch API
    python analyze_aw.py --fetch [--from DATE] [--to DATE] [--report] [--timezone TZ]

Options:
    --fetch             Fetch data directly from ActivityWatch API (requires aw-client)
    --from DATE         Start date: 'today', 'yesterday', 'week', '7d', '2w', or YYYY-MM-DD
    --to DATE           End date (same formats as --from). Default: end of --from day
    --report            Output human-readable markdown report instead of JSON
    --timezone TZ       Timezone (e.g., 'America/Los_Angeles'). Default: system local
    --config FILE       Custom category config JSON file

Examples:
    # Analyze today's productivity
    python analyze_aw.py --fetch --from today --report --timezone America/Los_Angeles

    # Analyze the past week
    python analyze_aw.py --fetch --from week --report

    # Analyze specific date range
    python analyze_aw.py --fetch --from 2025-12-20 --to 2025-12-26 --report

    # Analyze from exported CSV
    python analyze_aw.py export.csv --report --timezone America/New_York
""")
        sys.exit(0)

    output_report = "--report" in sys.argv

    # Get timezone if provided (default: system local)
    tz_name = None
    if "--timezone" in sys.argv:
        tz_idx = sys.argv.index("--timezone")
        if tz_idx + 1 < len(sys.argv):
            tz_name = sys.argv[tz_idx + 1]

    # Load custom config if provided
    config_path = None
    if "--config" in sys.argv:
        config_idx = sys.argv.index("--config")
        if config_idx + 1 < len(sys.argv):
            config_path = sys.argv[config_idx + 1]

    # Update CATEGORY_RULES module-level variable
    if config_path:
        loaded_rules = load_category_rules(config_path)
        CATEGORY_RULES.clear()
        CATEGORY_RULES.update(loaded_rules)

    # Determine filepath: either from argument or fetch from ActivityWatch
    filepath = None
    temp_file = False

    if "--fetch" in sys.argv:
        # Fetch directly from ActivityWatch API
        if not AW_CLIENT_AVAILABLE:
            print("Error: aw-client not installed. Install with: pip install aw-client", file=sys.stderr)
            print("Alternatively, export CSV from ActivityWatch UI and provide as argument.", file=sys.stderr)
            sys.exit(1)

        # Parse --from date
        from_date = None
        if "--from" in sys.argv:
            from_idx = sys.argv.index("--from")
            if from_idx + 1 < len(sys.argv):
                from_date = parse_date_arg(sys.argv[from_idx + 1], tz_name)
                if not from_date:
                    print(f"Error: Could not parse --from date: {sys.argv[from_idx + 1]}", file=sys.stderr)
                    sys.exit(1)
        else:
            # Default to today
            from_date = parse_date_arg("today", tz_name)

        # Parse --to date
        to_date = None
        if "--to" in sys.argv:
            to_idx = sys.argv.index("--to")
            if to_idx + 1 < len(sys.argv):
                to_date = parse_date_arg(sys.argv[to_idx + 1], tz_name)
                if not to_date:
                    print(f"Error: Could not parse --to date: {sys.argv[to_idx + 1]}", file=sys.stderr)
                    sys.exit(1)
                # Set to end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
        else:
            # Default to end of from_date day
            to_date = from_date.replace(hour=23, minute=59, second=59)

        print(f"Fetching ActivityWatch data from {from_date} to {to_date}", file=sys.stderr)

        filepath = fetch_from_activitywatch(from_date, to_date, tz_name)
        if not filepath:
            print("Error: Could not fetch data from ActivityWatch", file=sys.stderr)
            sys.exit(1)
        temp_file = True

        # Also fetch web watcher data (Chrome extension)
        web_events = fetch_web_watcher_data(from_date, to_date, tz_name)
    else:
        # Use provided CSV file
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        web_events = None  # No web data when using CSV

    try:
        summary = analyze_csv_enhanced(filepath, tz_name=tz_name)

        # Add web watcher analysis if available
        if web_events:
            web_analysis = analyze_web_data(web_events)
            if web_analysis:
                summary['chrome_extension'] = web_analysis

        if output_report:
            print(format_report(summary))
        else:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
    finally:
        # Clean up temporary file
        if temp_file and filepath and os.path.exists(filepath):
            os.unlink(filepath)
