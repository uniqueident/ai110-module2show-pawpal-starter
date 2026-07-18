"""!
@file main.py
@brief Demo entry point for PawPal+.

Builds one Owner with a handful of Pets and Tasks -- added deliberately out
of priority order, to prove the heap-backed queue and the chronological
plan sort both work regardless of insertion order -- generates a plan with
Scheduler, and prints a human-readable "Today's Schedule" to the terminal.
No LLM is configured here, so the explanation falls back to the rule-based
path in Scheduler.
"""

from datetime import date, datetime

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow

## The calendar date every demo window and plan is anchored to.
PLAN_DATE = date(2026, 7, 16)


def build_demo_owner() -> Owner:
    """!
    @brief Construct a sample Owner with pets, tasks, and availability.

    Availability includes a recurring daily window (anchored on an old,
    unrelated date, to prove TimeWindow.for_day() projects it onto
    PLAN_DATE) and two overlapping morning windows, to exercise
    Owner.get_conflicting_windows(). Each pet's tasks are added out of
    priority order and out of the order they'll actually be scheduled in,
    so the printed plan only reads correctly if the heap queue and the
    plan's chronological sort are both doing their job.

    @return A fully populated Owner ready to hand to a Scheduler.
    """
    owner = Owner()
    owner.set_preferences(["morning walks preferred"])

    owner.add_availability(
        TimeWindow(datetime(2020, 1, 1, 6, 0), datetime(2020, 1, 1, 6, 15), recurring=True)
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 7, 0), datetime(2026, 7, 16, 7, 20))
    )
    # Deliberately overlaps the window above, so get_conflicting_windows()
    # has something to report.
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 7, 10), datetime(2026, 7, 16, 7, 30))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 8, 0), datetime(2026, 7, 16, 9, 0))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 18, 0), datetime(2026, 7, 16, 19, 0))
    )

    rex = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    # Added lowest-priority first and highest-priority last -- get_tasks()
    # must still hand them back in priority order (Feed, Walk, Meds).
    rex.add_task(Task("Meds", "Evening allergy pill", priority=2, duration_minutes=5))
    rex.add_task(Task("Walk", "Morning walk around the block", priority=1, duration_minutes=45))
    rex.add_task(Task("Feed", "Breakfast kibble", priority=0, duration_minutes=10))

    luna = Pet("Luna", "Cat", date(2021, 6, 15), date(2024, 3, 10))
    luna.add_task(Task("Groom", "Brush coat", priority=3, duration_minutes=15))
    luna.add_task(Task("Feed", "Wet food breakfast", priority=0, duration_minutes=12))
    # Mark Groom done ahead of time so we can demo the completed/pending filter.
    for task in luna.get_tasks():
        if task.get_name() == "Groom":
            task.mark_complete()

    owner.add_pet(rex)
    owner.add_pet(luna)
    return owner


def print_schedule(title: str, plan: str, explanation: str = "") -> None:
    """!
    @brief Print a generated plan (and, optionally, its explanation).
    @param title Section heading for this printout.
    @param plan The plan string returned by Scheduler.generate_plan().
    @param explanation Optional explanation string from Scheduler.explain_plan().
    """
    print("=" * 40)
    print(title)
    print("=" * 40)
    print(plan)
    if explanation:
        print("-" * 40)
        print("Why this plan:")
        print(explanation)
    print("=" * 40)
    print()


def main() -> None:
    """!
    @brief Demo entry point: build a sample Owner, schedule, and print it.

    Exercises the newer Scheduler/Owner methods end to end: conflict
    detection, the pending/completed task filter, per-pet filtering, and
    the chronologically-sorted plan output.
    """
    owner = build_demo_owner()
    scheduler = Scheduler(owner)

    conflicts = owner.get_conflicting_windows()
    print(f"Detected {len(conflicts)} overlapping availability window(s):")
    for first, second in conflicts:
        print(f"  - {first.get_start()} .. {first.get_end()}  overlaps  "
              f"{second.get_start()} .. {second.get_end()}")
    print()

    default_plan = scheduler.generate_plan(for_date=PLAN_DATE)
    explanation = scheduler.explain_plan(default_plan)
    print_schedule("Today's Schedule (pending tasks only)", default_plan, explanation)

    full_plan = scheduler.generate_plan(for_date=PLAN_DATE, include_completed=True)
    print_schedule("Today's Schedule (including completed tasks)", full_plan)

    luna_plan = scheduler.generate_plan(pet_name="Luna", for_date=PLAN_DATE)
    print_schedule("Today's Schedule (Luna only)", luna_plan)


if __name__ == "__main__":
    main()
