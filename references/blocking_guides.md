# App Blocking Guides

Step-by-step setup for common blocking tools. Use these after running the analyzer to implement your "One Change" recommendation.

## macOS Focus Mode (Built-in, Free)

Best for: Blocking specific apps during scheduled hours

### Setup Deep Work Mode

1. **Open Settings**: System Settings → Focus
2. **Create Focus**: Click `+` → Custom → Name it "Deep Work"
3. **Block Apps**:
   - Click "Allowed Apps" → Add Filter → "Not Allowed"
   - Add your distraction apps (Telegram, Slack, etc.)
4. **Set Schedule**:
   - Scroll to "Set a Schedule" → Add Schedule → Time
   - Set your peak hours (e.g., 10:00-12:00)
   - Choose days (weekdays recommended)
5. **Enable**: Toggle on "Silence Notifications"

### Quick Toggle
- Menu bar → Focus icon (moon) → Click to toggle on/off
- Useful when you need temporary access to blocked apps

### Tips
- Create multiple Focus modes (Deep Work, Meetings, Evening)
- "Time Sensitive Notifications" lets urgent messages through
- Focus syncs across all Apple devices

---

## Cold Turkey (Cross-platform, Free/Paid)

Best for: Hardcore blocking that's hard to bypass

**Download**: https://getcoldturkey.com

### Setup

1. **Install** and create account
2. **Create Block List**:
   - Click "Blocks" → New Block
   - Name: "Focus Time"
   - Add apps: Telegram, Twitter, Reddit, etc.
   - Add websites: twitter.com, reddit.com, youtube.com
3. **Schedule**:
   - Set recurring schedule for your peak hours
   - Or use "Lock" for unbreakable blocks
4. **Allowlist** (optional):
   - Add work-related exceptions
   - e.g., allow Telegram Web but block desktop app

### Nuclear Option
- "Frozen Turkey" blocks EVERYTHING except allowlist
- Cannot be disabled until timer expires
- Use for deadline crunches

---

## Windows Focus Assist

Best for: Windows users, notification blocking

### Setup

1. **Open**: Settings → System → Focus Assist
2. **Choose Level**:
   - Priority only: Only allowed apps notify
   - Alarms only: Complete silence
3. **Automatic Rules**:
   - Set times for automatic activation
   - Enable during presentations, gaming, etc.
4. **Priority List**: Customize which apps can interrupt

### Limitations
- Doesn't block app access, only notifications
- Pair with Cold Turkey for full blocking

---

## Android Digital Wellbeing

Best for: Phone distractions

### Setup App Timers

1. **Open**: Settings → Digital Wellbeing
2. **Dashboard**: See time spent per app
3. **Set Timer**:
   - Tap app → Set timer
   - e.g., Telegram: 30 min/day
4. **Focus Mode**:
   - Select distracting apps
   - Schedule or manually activate
   - Paused apps are grayed out

### Bedtime Mode
- Grayscale screen after set time
- Silences notifications
- Helps end late-night phone use

---

## iOS Screen Time

Best for: iPhone/iPad distractions

### Setup

1. **Open**: Settings → Screen Time
2. **App Limits**:
   - Tap "App Limits" → Add Limit
   - Choose category or specific apps
   - Set daily time limit
3. **Downtime**:
   - Schedule "off" hours
   - Only allowed apps work during downtime
4. **Always Allowed**: Whitelist essential apps

### Tips
- Set a Screen Time passcode (have someone else set it)
- "One More Minute" can be disabled
- Syncs with Focus modes

---

## Browser Extensions

Best for: Blocking websites while allowing apps

### Recommended Extensions

| Extension | Browser | Features |
|-----------|---------|----------|
| LeechBlock | Firefox | Highly customizable schedules |
| StayFocusd | Chrome | Daily time limits |
| Freedom | All | Cross-device sync |
| uBlacklist | Chrome | Block sites from search results |

### Quick Setup (LeechBlock/StayFocusd)

1. Install extension
2. Add blocked sites: reddit.com, twitter.com, youtube.com
3. Set schedule or daily limit
4. Enable "Nuclear option" for unbreakable blocks

---

## Recommended Configurations

Based on common analyzer recommendations:

### "Block Telegram during focus hours"
```
Tool: macOS Focus Mode
Block: Telegram
Schedule: 10:00-12:00 weekdays
Exception: Allow for Telegram bot development
```

### "Block social media"
```
Tool: Cold Turkey + Browser Extension
Block apps: Twitter, Instagram, TikTok
Block sites: twitter.com, instagram.com, tiktok.com, reddit.com
Schedule: 9:00-17:00 weekdays
```

### "Reduce entertainment during work"
```
Tool: Cold Turkey
Block: Netflix, YouTube, Twitch, Spotify
Schedule: 9:00-18:00 weekdays
Allowlist: YouTube channels for tutorials (via browser extension)
```

### "End late-night sessions"
```
Tool: macOS Focus Mode + Cold Turkey
Block: All work apps after midnight
Schedule: 00:00-08:00 daily
Purpose: Force yourself to stop working
```

---

## Choosing the Right Tool

| Need | Recommended Tool |
|------|------------------|
| Block apps on Mac | macOS Focus Mode |
| Block websites | Browser extension |
| Unbreakable blocks | Cold Turkey (locked) |
| Phone distractions | iOS Screen Time / Android Digital Wellbeing |
| Cross-device sync | Freedom ($) or Cold Turkey Pro ($) |
| Free + simple | macOS Focus Mode + LeechBlock |

---

## After Setup

1. Run the analyzer again next week
2. Compare Focus scores
3. Adjust blocking schedule based on results
4. Iterate until Focus score > 60
