"""!
@file main.py
@brief Demo entry point for PawPal+.

Builds one Owner with a handful of Pets and Tasks, generates a plan with
Scheduler, and prints a human-readable "Today's Schedule" to the terminal.
No LLM is configured here, so the explanation falls back to the rule-based
path in Scheduler.
"""

from datetime import date, datetime

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow


def build_demo_owner() -> Owner:
    """!
    @brief Construct a sample Owner with pets, tasks, and availability.
    @return A fully populated Owner ready to hand to a Scheduler.
    """
    owner = Owner()
    owner.set_preferences(["morning walks preferred"])

    # Two time windows today: an early morning block and an evening block.
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 7, 0), datetime(2026, 7, 16, 8, 30))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 16, 18, 0), datetime(2026, 7, 16, 19, 0))
    )

    rex = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    rex.add_task(Task("Feed", "Breakfast kibble", 0, 10))
    rex.add_task(Task("Walk", "Morning walk around the block", 1, 30))
    rex.add_task(Task("Meds", "Evening allergy pill", 2, 5))

    luna = Pet("Luna", "Cat", date(2021, 6, 15), date(2024, 3, 10))
    luna.add_task(Task("Feed", "Wet food breakfast", 0, 12))
    luna.add_task(Task("Groom", "Brush coat", 3, 15))

    owner.add_pet(rex)
    owner.add_pet(luna)
    return owner


def print_schedule(plan: str, explanation: str) -> None:
    """!
    @brief Print the generated plan and its explanation as a readable report.
    @param plan The plan string returned by Scheduler.generate_plan().
    @param explanation The explanation string returned by Scheduler.explain_plan().
    """
    print("=" * 40)
    print("Today's Schedule")
    print("=" * 40)
    print(plan)
    print("-" * 40)
    print("Why this plan:")
    print(explanation)
    print("=" * 40)


def main() -> None:
    """!
    @brief Demo entry point: build a sample Owner, schedule, and print it.
    """
    owner = build_demo_owner()
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan()
    explanation = scheduler.explain_plan(plan)

    print_schedule(plan, explanation)


if __name__ == "__main__":
    main()
