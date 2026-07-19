# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
========================================
Today's Schedule
========================================
07:00 - Rex: Feed (priority 0, 10 min)
07:10 - Rex: Walk (priority 1, 30 min)
07:40 - Rex: Meds (priority 2, 5 min)
07:45 - Luna: Feed (priority 0, 12 min)
07:57 - Luna: Groom (priority 3, 15 min)
----------------------------------------
Why this plan:
Tasks were scheduled into the owner's available time windows in chronological order, assigning each pet's highest-priority task (lowest priority number) first and moving to the next task once a window's time was used up. Preferences considered: morning walks preferred.
========================================1
```

## 🧪 Testing PawPal+

Make sure you're in your virtual environment (see [Setup](#setup)) before running tests.

```bash
# Run the full test suite:
python3 -m pytest

# Run with coverage:
pytest --cov
```

The suite in `tests/test_pawpal.py` covers the core domain model: task completion and priority-queue ordering on `Pet`, `TimeWindow` overlap/recurrence projection, owner conflict detection, and `Scheduler.generate_plan()` behavior — filtering, preference-based sorting, recurring windows, and edge cases like tasks too large for any window.

Sample test output:

```
================================================================================================ test session starts =================================================================================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/uniqueident/pawpal/ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 25 items                                                                                                                                                                                                   

tests/test_pawpal.py .........................  
```

I am 4/5 confident with the current system's reliability.

## ✅ Features

- **Priority task queue per pet** — each `Pet` keeps its tasks in a min-heap keyed on `(priority, insertion order)`, so `get_top_task()`/`get_tasks()` always return tasks lowest-priority-number-first in O(log n) per insert, with FIFO ordering for ties.
- **Constraint-aware daily scheduling** — `Scheduler.generate_plan()` greedily assigns each pet's pending tasks to the earliest availability window with enough remaining time, consuming that window's time as it's used and carrying leftover time forward for a later, shorter task.
- **Preference-based window ordering** — `Scheduler._apply_constraints()` sorts windows chronologically, then bumps windows that start in an owner-preferred part of the day (morning/afternoon/evening/night) to the front.
- **Date-scoped, recurring availability** — `TimeWindow.for_day()` / `occurs_on()` project recurring windows (e.g. "every day 7–8am") onto any target date, so a plan for a given day only sees windows that actually occur on it.
- **Recurring tasks** — `Task.create_next_occurrence()` / `Pet.complete_task()` automatically re-enqueue a daily/weekly task's next occurrence the moment the current one is completed.
- **Availability conflict detection** — `Owner.get_conflicting_windows()` / `TimeWindow.overlaps()` flag pairs of overlapping windows (accounting for recurrence) before a plan is built; conflicts are surfaced as warnings, not silently resolved.
- **Plan filtering** — plans can be scoped to a single pet, include or exclude already-completed tasks, and gracefully report "nothing fits" instead of returning empty output.
- **Plan explanation** — `Scheduler.explain_plan()` uses a pluggable, OpenAI-API-compatible `LLMClient` to phrase why the plan looks the way it does, falling back to a deterministic rule-based explanation if no LLM is configured or the call fails.

## 📐 Smarter Scheduling

### Sorting behavior

*Methods: `Pet.get_tasks()`, `Scheduler._apply_constraints()`, `Scheduler.generate_plan()`*

Tasks are scheduled highest-priority first (lowest priority number wins), with ties broken by the order they were added. Time windows are considered chronologically, with any preferred times of day (morning/afternoon/evening/night) bumped to the front. The final plan is always printed in chronological order, regardless of the order tasks were assigned in.

### Filtering behavior

*Methods: `Scheduler.generate_plan()`, `Pet.get_tasks()`, `TimeWindow.occurs_on()`, `TimeWindow.for_day()`*

A plan can be scoped to one pet, and completed tasks are skipped by default. Only time windows that actually occur on the requested date are used — recurring windows are projected onto that date, one-off windows only count on their own date. A task is only placed in a window that's big enough for it; if nothing fits anywhere, the plan says so instead of coming back empty.

### Conflict detection logic

*Methods: `Owner.get_conflicting_windows()`, `TimeWindow.overlaps()`, `Scheduler._warn_conflicts()`*

Before building a plan, the scheduler checks the owner's availability windows for overlaps (accounting for recurring windows) and prints a warning for each pair it finds. This is just a heads-up — conflicting windows aren't removed, and both stay usable for scheduling.

### Recurring task logic

*Methods: `Task.create_next_occurrence()`, `Task.mark_complete()`, `Pet.complete_task()`, `TimeWindow.is_recurring()`, `TimeWindow.occurs_on()`, `TimeWindow.for_day()`*

Tasks can recur daily or weekly. Completing a recurring task automatically creates and re-queues its next occurrence, so it doesn't need to be manually re-added. Recurring availability windows work similarly: instead of being tied to one date, they're treated as present on every day and projected onto whatever date a plan is being built for.

## 📸 Demo Walkthrough

### Main UI features

The Streamlit app (`app.py`) lets an owner build up a schedule interactively:

- Enter owner/pet basics (owner name, pet name, species) — pets are created on the fly and reused if you enter the same name again.
- Add tasks with a title, duration (minutes), and a friendly priority label (low/medium/high, mapped to priority 2/1/0). Pending tasks are shown in a table already sorted by priority.
- Add availability windows with start/end times; a new window that overlaps an existing one is rejected up front with a warning instead of silently double-booking.
- Generate a schedule on demand, which surfaces any remaining availability conflicts, renders the plan as a table (time, pet, species, age, task, priority, duration), and displays the plan's explanation underneath.

### Example workflow

1. Enter the owner's name and add a pet (e.g. "Rex", a Dog).
2. Add a few tasks for that pet — a high-priority "Feed", a medium-priority "Walk", a low-priority "Meds" — each with a duration.
3. Add one or more availability windows (e.g. 07:00–07:20 and 08:00–09:00); if a new window overlaps one already added, the app warns and refuses to add it.
4. Click **Generate schedule**. The app checks for availability conflicts, then greedily places each pet's highest-priority task into the earliest window with enough room left.
5. Read the resulting table top-to-bottom for the day's plan, and read "Why this plan" underneath for the reasoning.

### Key scheduler behaviors

- **Priority first, then time**: within a pet, the highest-priority (lowest-numbered) pending task is placed first; ties keep insertion order.
- **Chronological output**: tasks are assigned pet-by-pet, but the final plan is always sorted by scheduled start time, so it always reads top-to-bottom by clock time regardless of assignment order.
- **Preferred time of day**: if the owner's preferences mention "morning", "afternoon", "evening", or "night", windows in that part of the day are tried first.
- **Recurring windows and tasks**: a recurring availability window (e.g. daily 6:00–6:15) is projected onto the plan's target date; a completed recurring task automatically re-queues its next occurrence.
- **Conflict warnings, not removal**: overlapping availability windows are reported but both remain usable — the scheduler doesn't decide which one "wins".
- **No LLM required**: `explain_plan()` works out of the box with a deterministic, rule-based explanation; an optional LLM client can be plugged in for a more natural explanation.

### Sample CLI output (`python3 main.py`)

```text
Warning: overlapping availability windows (2026-07-16 07:00:00 - 2026-07-16 07:20:00) and (2026-07-16 07:10:00 - 2026-07-16 07:30:00)
Detected 1 overlapping availability window(s):
  - 2026-07-16 07:00:00 .. 2026-07-16 07:20:00  overlaps  2026-07-16 07:10:00 .. 2026-07-16 07:30:00

========================================
Today's Schedule (pending tasks only)
========================================
Time: 06:00 | Name: Rex | Species: Dog | Age: 6 | Task: Feed | Priority: 0 | Duration: 10 min
Time: 06:10 | Name: Rex | Species: Dog | Age: 6 | Task: Meds | Priority: 2 | Duration: 5 min
Time: 07:00 | Name: Luna | Species: Cat | Age: 5 | Task: Feed | Priority: 0 | Duration: 12 min
Time: 08:00 | Name: Rex | Species: Dog | Age: 6 | Task: Walk | Priority: 1 | Duration: 45 min
----------------------------------------
Why this plan:
Tasks were scheduled into the owner's available time windows in chronological order, assigning each pet's highest-priority task (lowest priority number) first and moving to the next task once a window's time was used up. Preferences considered: morning walks preferred.
========================================

========================================
Today's Schedule (Luna only)
========================================
Time: 06:00 | Name: Luna | Species: Cat | Age: 5 | Task: Feed | Priority: 0 | Duration: 12 min
========================================
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
