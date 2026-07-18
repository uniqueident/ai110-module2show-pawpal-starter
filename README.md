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

I am 4/5 confident with the current system's a month.

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

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
