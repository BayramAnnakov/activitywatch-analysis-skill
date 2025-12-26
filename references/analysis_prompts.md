# ActivityWatch Analysis Prompts

Prompt templates for deeper analysis with Claude or local models.

## Basic Weekly Review

```
Analyze my ActivityWatch summary for the past week.

KEY QUESTIONS:
1. Where did my time actually go? (top 5 categories)
2. What patterns suggest distraction vs. deep work?
3. What's my combined score and what drove it?

Be direct and specific. Use the actual numbers.

DATA:
[paste summary.json or report here]
```

## Death Loop Deep Dive

```
Focus on my context switching patterns, especially death loops.

For each death loop identified:
1. What might trigger this switching pattern?
2. Is it productive (code ↔ terminal for testing) or distracting?
3. What's one specific intervention to break this loop?

Death loops data:
[paste death_loops section]
```

## Energy Mapping

```
Using my hourly activity data, help me map my energy patterns.

Create a table showing:
- Hours with highest productive activity
- Hours with highest context switching  
- Hours that might be "transition zones"

Then suggest:
- When to schedule deep work
- When to handle meetings/email
- When to take breaks

Hourly data:
[paste hourly_analysis section]
```

## Category Audit

```
Review my category breakdown and help me understand:

1. Is my time allocation aligned with my goals?
2. Which categories are eating more time than expected?
3. What's the ratio of deep work to shallow work?

For categories with negative weights, suggest specific interventions.

Category data:
[paste category_breakdown section]
```

## Week-over-Week Comparison

```
I have summaries from two weeks. Compare them:

WEEK 1:
[paste week 1 summary]

WEEK 2:
[paste week 2 summary]

Analysis needed:
1. Did combined score improve or decline? Why?
2. Any new death loops appear?
3. Did time allocation shift?
4. What intervention worked or didn't?
```

## Intervention Planning

```
Based on my analysis, I want to improve my combined score from [X] to [Y].

Current biggest issues:
1. [death loop or pattern]
2. [time sink category]
3. [distracted hours]

Help me create a SPECIFIC intervention plan:
- What to block and when
- What schedule changes to make
- What to measure next week
- One daily habit to implement
```

## Browser Activity Analysis

```
Look at my browser breakdown data:

[paste browser_breakdown section]

Questions:
1. What percentage is productive vs. entertainment?
2. Are there any surprise time sinks?
3. What browser activities should I block during work hours?
4. What legitimate work is happening in the browser that I should protect?
```

## Focus Session Design

```
Based on my hourly patterns:

[paste hourly_analysis section]

Design an ideal focus session schedule for me:
1. What hours should I block for deep work?
2. How long should each focus session be?
3. When should I schedule breaks?
4. What apps should be blocked during focus time?
```

## For Local Models (Shorter Context)

When using smaller local models, use this condensed prompt:

```
My productivity data (7 days):
- Combined score: [X]/100
- Top category: [name] at [X]h
- Top death loop: [A ↔ B, count]
- Peak hours: [X-Y]
- Danger hours: [X-Y]

What ONE change should I make this week?
```

## Russian Language Version

```
Проанализируй мои данные ActivityWatch за неделю.

КЛЮЧЕВЫЕ ВОПРОСЫ:
1. Куда реально ушло моё время? (топ-5 категорий)
2. Какие паттерны указывают на отвлечение vs глубокую работу?
3. Какой мой комбинированный показатель и что на него повлияло?

Будь конкретным. Используй реальные цифры из данных.

ДАННЫЕ:
[вставить summary.json]
```

## Monthly Trend Analysis

```
I have 4 weekly summaries. Help me identify monthly trends:

WEEK 1: [paste scores]
WEEK 2: [paste scores]
WEEK 3: [paste scores]  
WEEK 4: [paste scores]

Questions:
1. Is my productivity trending up or down?
2. Are death loops getting better or worse?
3. What day of week is consistently best/worst?
4. What systemic change would have the biggest impact?
```
