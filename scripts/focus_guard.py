#!/usr/bin/env python3
"""
Focus Guard - Open Source App Blocker for macOS

Monitors running apps and kills distracting ones during focus hours.
Shows macOS notifications when blocking apps.

Usage:
    # Start focus guard (runs until stopped)
    python focus_guard.py --start

    # AUTO-DETECT MODE: Automatically enables when you're in deep work
    python focus_guard.py --auto

    # Start with custom config
    python focus_guard.py --start --config focus_config.json

    # Quick focus session (2 hours, block Telegram and Slack)
    python focus_guard.py --start --duration 2 --block Telegram Slack

    # Check status
    python focus_guard.py --status

    # Stop focus guard
    python focus_guard.py --stop

Requirements:
    - macOS (uses osascript for notifications and app control)
    - Python 3.8+
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from zoneinfo import ZoneInfo

# Default configuration
DEFAULT_CONFIG = {
    "blocked_apps": [
        "Telegram",
        "Slack",
        "Discord",
        "Messages",
        "WhatsApp",
        "Twitter",
        "Facebook"
    ],
    "deep_work_apps": [
        "Terminal",
        "Cursor",
        "Code",
        "Xcode",
        "PyCharm",
        "IntelliJ IDEA",
        "WebStorm",
        "Sublime Text",
        "Neovim",
        "Vim"
    ],
    "schedule": {
        "enabled": False,
        "start_hour": 9,
        "end_hour": 17,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    },
    "auto_detect": {
        "trigger_minutes": 5,      # Minutes of deep work before auto-enabling focus mode
        "cooldown_minutes": 3,     # Minutes without deep work before auto-disabling
        "session_duration_hours": 2  # Default duration when auto-triggered
    },
    "settings": {
        "check_interval_seconds": 2,
        "show_notifications": True,
        "notification_sound": True,
        "warn_only": True,  # If True, only warn (don't quit apps). If False, quit after grace period
        "grace_period_seconds": 5,  # Time to save work before app is killed (only if warn_only=False)
        "log_violations": True
    }
}

# PID file location
PID_FILE = Path.home() / ".focus_guard.pid"
LOG_FILE = Path.home() / ".focus_guard.log"
CONFIG_FILE = Path(__file__).parent / "focus_config.json"


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from file or use defaults."""
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
        except Exception as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    # Try default config location
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
        except:
            pass

    return DEFAULT_CONFIG.copy()


def save_default_config():
    """Save default configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Default config saved to: {CONFIG_FILE}")


def get_running_apps() -> Set[str]:
    """Get list of currently running applications."""
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            apps = result.stdout.strip().split(", ")
            return set(apps)
    except Exception as e:
        print(f"Error getting running apps: {e}", file=sys.stderr)
    return set()


def get_frontmost_app() -> Optional[str]:
    """Get the currently focused/frontmost application."""
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting frontmost app: {e}", file=sys.stderr)
    return None


def quit_app(app_name: str, force: bool = False) -> bool:
    """Quit an application gracefully or forcefully."""
    try:
        if force:
            # Force quit
            subprocess.run(["pkill", "-9", "-x", app_name], capture_output=True)
        else:
            # Graceful quit via AppleScript
            subprocess.run(
                ["osascript", "-e", f'tell application "{app_name}" to quit'],
                capture_output=True
            )
        return True
    except Exception as e:
        print(f"Error quitting {app_name}: {e}", file=sys.stderr)
        return False


def show_notification(title: str, message: str, sound: bool = True):
    """Show a macOS notification."""
    sound_param = 'with sound "Basso"' if sound else ''
    script = f'display notification "{message}" with title "{title}" {sound_param}'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True)
    except Exception as e:
        print(f"Error showing notification: {e}", file=sys.stderr)


def log_violation(app_name: str, action: str):
    """Log a violation to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {action} | {app_name}\n"
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
    except:
        pass


def is_within_schedule(config: dict) -> bool:
    """Check if current time is within the focus schedule."""
    schedule = config.get("schedule", {})

    if not schedule.get("enabled", False):
        return True  # If schedule disabled, always active

    now = datetime.now()
    current_day = now.strftime("%A")
    current_hour = now.hour

    # Check day
    allowed_days = schedule.get("days", [])
    if current_day not in allowed_days:
        return False

    # Check time
    start_hour = schedule.get("start_hour", 0)
    end_hour = schedule.get("end_hour", 24)

    return start_hour <= current_hour < end_hour


def write_pid():
    """Write current process ID to file."""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def read_pid() -> Optional[int]:
    """Read process ID from file."""
    try:
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return None


def is_running() -> bool:
    """Check if Focus Guard is already running."""
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, 0)  # Check if process exists
            return True
        except OSError:
            # Process doesn't exist, clean up stale PID file
            PID_FILE.unlink(missing_ok=True)
    return False


def stop_guard():
    """Stop the running Focus Guard process."""
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Focus Guard stopped (PID: {pid})")
            PID_FILE.unlink(missing_ok=True)
            return True
        except OSError:
            print("Focus Guard is not running")
            PID_FILE.unlink(missing_ok=True)
    else:
        print("Focus Guard is not running")
    return False


def show_status(config: dict):
    """Show current Focus Guard status."""
    running = is_running()
    pid = read_pid()

    print("=" * 50)
    print("Focus Guard Status")
    print("=" * 50)
    print(f"Status: {'RUNNING' if running else 'STOPPED'}")
    if running:
        print(f"PID: {pid}")
    print(f"\nBlocked Apps: {', '.join(config['blocked_apps'])}")

    schedule = config.get("schedule", {})
    if schedule.get("enabled"):
        print(f"\nSchedule: {schedule['start_hour']}:00 - {schedule['end_hour']}:00")
        print(f"Days: {', '.join(schedule['days'])}")
        print(f"Currently in schedule: {'Yes' if is_within_schedule(config) else 'No'}")
    else:
        print("\nSchedule: Always active (no schedule)")

    # Show recent violations
    if LOG_FILE.exists():
        print("\nRecent violations:")
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()[-5:]  # Last 5
                for line in lines:
                    print(f"  {line.strip()}")
        except:
            pass
    print("=" * 50)


def run_guard(config: dict, duration_hours: Optional[float] = None, warn_only: Optional[bool] = None):
    """Main guard loop."""

    if is_running():
        print("Focus Guard is already running!")
        print("Use --stop to stop it first, or --status to check status.")
        return

    # Calculate end time if duration specified
    end_time = None
    if duration_hours:
        end_time = datetime.now() + timedelta(hours=duration_hours)
        print(f"Focus session will end at: {end_time.strftime('%H:%M')}")

    blocked_apps = set(config["blocked_apps"])
    settings = config.get("settings", {})
    check_interval = settings.get("check_interval_seconds", 2)
    show_notifs = settings.get("show_notifications", True)
    notif_sound = settings.get("notification_sound", True)
    grace_period = settings.get("grace_period_seconds", 5)
    log_enabled = settings.get("log_violations", True)

    # Use CLI override if provided, otherwise use config
    if warn_only is None:
        warn_only = settings.get("warn_only", True)

    # Write PID file
    write_pid()

    # Set up signal handler for clean shutdown
    def cleanup(signum, frame):
        print("\nFocus Guard stopped.")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    mode = "Warning" if warn_only else "Blocking"
    print(f"Focus Guard started! {mode}: {', '.join(blocked_apps)}")
    if warn_only:
        print("Mode: Soft warnings only (apps won't be closed)")
    else:
        print(f"Mode: Hard blocking (apps will be closed after {grace_period}s)")
    print("Press Ctrl+C to stop.\n")

    # Track recently warned apps to avoid spam
    recently_warned = {}  # app -> last_warned_time

    try:
        while True:
            # Check if duration exceeded
            if end_time and datetime.now() >= end_time:
                print("\nFocus session completed!")
                show_notification("Focus Guard", "Focus session completed! Great work!", notif_sound)
                break

            # Check if within schedule
            if not is_within_schedule(config):
                time.sleep(60)  # Check less frequently when outside schedule
                continue

            # Get running apps
            running_apps = get_running_apps()

            # Check for blocked apps
            for app in blocked_apps:
                if app in running_apps:
                    now = time.time()
                    last_warned = recently_warned.get(app, 0)

                    # Only warn if we haven't warned in the last 30 seconds
                    if now - last_warned > 30:
                        if warn_only:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: {app} is open!")
                            if show_notifs:
                                show_notification(
                                    "Focus Guard",
                                    f"Hey! You're using '{app}' during focus time. Stay focused!",
                                    notif_sound
                                )
                            if log_enabled:
                                log_violation(app, "WARNING")
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Blocked: {app}")
                            if show_notifs:
                                show_notification(
                                    "Focus Guard",
                                    f"'{app}' is blocked during focus time. Closing in {grace_period}s...",
                                    notif_sound
                                )
                            if log_enabled:
                                log_violation(app, "BLOCKED")

                            # Grace period
                            if grace_period > 0:
                                time.sleep(grace_period)

                            # Check if app is still running
                            if app in get_running_apps():
                                quit_app(app)
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Quit: {app}")

                        recently_warned[app] = now

            time.sleep(check_interval)

    finally:
        PID_FILE.unlink(missing_ok=True)


def run_auto_guard(config: dict):
    """Auto-detect deep work and enable focus mode automatically."""

    if is_running():
        print("Focus Guard is already running!")
        print("Use --stop to stop it first, or --status to check status.")
        return

    deep_work_apps = set(config.get("deep_work_apps", DEFAULT_CONFIG["deep_work_apps"]))
    blocked_apps = set(config["blocked_apps"])
    settings = config.get("settings", {})
    auto_config = config.get("auto_detect", {})

    trigger_minutes = auto_config.get("trigger_minutes", 5)
    cooldown_minutes = auto_config.get("cooldown_minutes", 3)
    check_interval = settings.get("check_interval_seconds", 2)
    show_notifs = settings.get("show_notifications", True)
    notif_sound = settings.get("notification_sound", True)
    log_enabled = settings.get("log_violations", True)

    # Write PID file
    write_pid()

    # Set up signal handler for clean shutdown
    def cleanup(signum, frame):
        print("\nFocus Guard (auto-detect) stopped.")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    print(f"Focus Guard AUTO-DETECT mode started!")
    print(f"Deep work apps: {', '.join(deep_work_apps)}")
    print(f"Blocked apps: {', '.join(blocked_apps)}")
    print(f"Will activate after {trigger_minutes} min of deep work")
    print(f"Will deactivate after {cooldown_minutes} min of no deep work")
    print("Press Ctrl+C to stop.\n")

    # State tracking
    deep_work_start = None  # When deep work session started
    last_deep_work = None   # Last time a deep work app was focused
    focus_active = False    # Is focus mode currently active
    recently_warned = {}    # app -> last_warned_time

    try:
        while True:
            frontmost = get_frontmost_app()
            now = time.time()
            now_dt = datetime.now()

            # Check if frontmost app is a deep work app
            is_deep_work = frontmost in deep_work_apps if frontmost else False

            if is_deep_work:
                last_deep_work = now
                if deep_work_start is None:
                    deep_work_start = now
                    print(f"[{now_dt.strftime('%H:%M:%S')}] Deep work detected: {frontmost}")

                # Check if we should activate focus mode
                if not focus_active:
                    minutes_in_deep_work = (now - deep_work_start) / 60
                    if minutes_in_deep_work >= trigger_minutes:
                        focus_active = True
                        print(f"\n[{now_dt.strftime('%H:%M:%S')}] ⚡ FOCUS MODE ACTIVATED (after {trigger_minutes} min of deep work)")
                        if show_notifs:
                            show_notification(
                                "Focus Guard",
                                f"Focus mode activated! Blocking {', '.join(blocked_apps)}",
                                notif_sound
                            )
                        if log_enabled:
                            log_violation("FOCUS_MODE", "ACTIVATED")
            else:
                # Not in deep work app
                if last_deep_work is not None:
                    minutes_since_deep_work = (now - last_deep_work) / 60

                    # Check if we should deactivate focus mode
                    if focus_active and minutes_since_deep_work >= cooldown_minutes:
                        focus_active = False
                        deep_work_start = None
                        print(f"\n[{now_dt.strftime('%H:%M:%S')}] 💤 Focus mode deactivated (no deep work for {cooldown_minutes} min)")
                        if show_notifs:
                            show_notification(
                                "Focus Guard",
                                "Focus mode ended. Take a break!",
                                notif_sound
                            )
                        if log_enabled:
                            log_violation("FOCUS_MODE", "DEACTIVATED")

            # If focus mode is active, check for blocked apps
            if focus_active:
                running_apps = get_running_apps()

                for app in blocked_apps:
                    if app in running_apps:
                        last_warned = recently_warned.get(app, 0)

                        # Only warn if we haven't warned in the last 30 seconds
                        if now - last_warned > 30:
                            print(f"[{now_dt.strftime('%H:%M:%S')}] ⚠️  Warning: {app} is open during focus time!")
                            if show_notifs:
                                show_notification(
                                    "Focus Guard",
                                    f"Hey! '{app}' is open during focus time. Stay focused!",
                                    notif_sound
                                )
                            if log_enabled:
                                log_violation(app, "WARNING")
                            recently_warned[app] = now

            time.sleep(check_interval)

    finally:
        PID_FILE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Focus Guard - Open Source App Blocker for macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start focus guard:
    python focus_guard.py --start

  AUTO-DETECT mode (recommended for flexible schedules):
    python focus_guard.py --auto
    # Automatically enables focus mode after 5 min of Terminal/Cursor use
    # Automatically disables after 3 min of no deep work

  Quick 2-hour session blocking specific apps:
    python focus_guard.py --start --duration 2 --block Telegram Slack

  Check status:
    python focus_guard.py --status

  Stop focus guard:
    python focus_guard.py --stop

  Create default config file:
    python focus_guard.py --init-config
"""
    )

    parser.add_argument("--start", action="store_true", help="Start Focus Guard (manual mode)")
    parser.add_argument("--auto", action="store_true", help="Start in auto-detect mode (enables when deep work detected)")
    parser.add_argument("--stop", action="store_true", help="Stop Focus Guard")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--init-config", action="store_true", help="Create default config file")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--duration", type=float, help="Focus session duration in hours")
    parser.add_argument("--block", nargs="+", help="Apps to block (overrides config)")
    parser.add_argument("--trigger-minutes", type=int, help="Minutes of deep work before auto-enabling (default: 5)")
    parser.add_argument("--warn-only", action="store_true", help="Only show warnings, don't close apps (default)")
    parser.add_argument("--hard-block", action="store_true", help="Close apps after grace period")

    args = parser.parse_args()

    if args.init_config:
        save_default_config()
        return

    config = load_config(args.config)

    # Override blocked apps if specified
    if args.block:
        config["blocked_apps"] = args.block

    # Determine warn_only mode
    warn_only = None  # Use config default
    if args.warn_only:
        warn_only = True
    elif args.hard_block:
        warn_only = False

    # Handle trigger-minutes override for auto mode
    if args.trigger_minutes:
        if "auto_detect" not in config:
            config["auto_detect"] = {}
        config["auto_detect"]["trigger_minutes"] = args.trigger_minutes

    if args.stop:
        stop_guard()
    elif args.status:
        show_status(config)
    elif args.auto:
        run_auto_guard(config)
    elif args.start:
        run_guard(config, args.duration, warn_only)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
