"""!
@file test_pawpal.py
@brief Unit tests for the PawPal+ core domain model.

Run with `python -m pytest` from the project root.
"""

from datetime import date, datetime

from pawpal_system import NO_SCHEDULE_MESSAGE, Owner, Pet, Scheduler, Task, TimeWindow


def test_mark_complete_changes_task_status() -> None:
    """!
    @brief mark_complete() should flip a Task's completion status.
    """
    task = Task("Walk", "Morning walk", priority=1, duration_minutes=30)

    assert task.is_complete() is False

    task.mark_complete()

    assert task.is_complete() is True


def test_add_task_increases_pet_task_count() -> None:
    """!
    @brief add_task() should grow the number of tasks queued on a Pet.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))

    assert len(pet.get_tasks()) == 0

    pet.add_task(Task("Feed", "Breakfast kibble", priority=0, duration_minutes=10))

    assert len(pet.get_tasks()) == 1

    pet.add_task(Task("Meds", "Evening pill", priority=2, duration_minutes=5))

    assert len(pet.get_tasks()) == 2


def test_timewindow_overlaps_detects_recurring_vs_one_off_conflict() -> None:
    """!
    @brief overlaps() must catch a one-off block that falls inside a
           recurring window's daily time-of-day range, even though the two
           windows were created against completely different anchor dates.
    """
    recurring = TimeWindow(
        datetime(2020, 1, 1, 7, 0), datetime(2020, 1, 1, 8, 0), recurring=True
    )
    one_off = TimeWindow(datetime(2026, 7, 17, 7, 30), datetime(2026, 7, 17, 7, 45))

    assert recurring.overlaps(one_off) is True
    assert one_off.overlaps(recurring) is True


def test_timewindow_overlaps_false_for_back_to_back_windows() -> None:
    """!
    @brief Windows that merely touch at a boundary (one ends exactly when
           the other starts) must not be reported as conflicting.
    """
    first = TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 8, 0))
    second = TimeWindow(datetime(2026, 7, 17, 8, 0), datetime(2026, 7, 17, 9, 0))

    assert first.overlaps(second) is False
    assert second.overlaps(first) is False


def test_timewindow_occurs_on() -> None:
    """!
    @brief A recurring window occurs on every day; a one-off window occurs
           only on its own stored date.
    """
    recurring = TimeWindow(
        datetime(2020, 1, 1, 7, 0), datetime(2020, 1, 1, 8, 0), recurring=True
    )
    one_off = TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 8, 0))

    assert recurring.occurs_on(date(2031, 12, 25)) is True
    assert one_off.occurs_on(date(2026, 7, 17)) is True
    assert one_off.occurs_on(date(2026, 7, 18)) is False


def test_timewindow_for_day_preserves_duration_and_time_of_day() -> None:
    """!
    @brief for_day() must move the date but keep the time-of-day and
           duration intact, including for a window that spans midnight.
    """
    overnight = TimeWindow(datetime(2020, 1, 1, 23, 30), datetime(2020, 1, 2, 0, 15))

    projected = overnight.for_day(date(2026, 7, 17))

    assert projected.get_start() == datetime(2026, 7, 17, 23, 30)
    assert projected.get_end() == datetime(2026, 7, 18, 0, 15)
    assert projected.get_end() - projected.get_start() == overnight.get_end() - overnight.get_start()


def test_owner_get_conflicting_windows_ignores_non_overlapping_pairs() -> None:
    """!
    @brief get_conflicting_windows() should report only the pairs that
           actually overlap, not every combination of stored windows.
    """
    owner = Owner()
    morning = TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 8, 0))
    overlapping = TimeWindow(datetime(2026, 7, 17, 7, 30), datetime(2026, 7, 17, 7, 45))
    evening = TimeWindow(datetime(2026, 7, 17, 18, 0), datetime(2026, 7, 17, 19, 0))
    owner.add_availability(morning)
    owner.add_availability(overlapping)
    owner.add_availability(evening)

    conflicts = owner.get_conflicting_windows()

    assert conflicts == [(morning, overlapping)]


def test_owner_get_pet_returns_none_for_unknown_name() -> None:
    """!
    @brief get_pet() should return None rather than raising when no pet
           with the given name has been added.
    """
    owner = Owner()
    owner.add_pet(Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1)))

    assert owner.get_pet("Whiskers") is None
    assert owner.get_pet("Rex") is not None


def test_pet_get_tasks_filters_by_completed_status() -> None:
    """!
    @brief get_tasks(completed=...) should return only tasks matching the
           requested status, while completed=None keeps returning all of
           them.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pending = Task("Walk", "Morning walk", priority=0, duration_minutes=20)
    done = Task("Feed", "Breakfast", priority=1, duration_minutes=10)
    done.mark_complete()
    pet.add_task(pending)
    pet.add_task(done)

    assert pet.get_tasks(completed=False) == [pending]
    assert pet.get_tasks(completed=True) == [done]
    assert pet.get_tasks() == [pending, done]


def test_generate_plan_skips_completed_tasks_by_default() -> None:
    """!
    @brief generate_plan() should not waste schedule time on tasks that are
           already marked complete unless include_completed=True is passed.
    """
    owner = Owner()
    today = date(2026, 7, 17)
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 8, 0))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    walk = Task("Walk", "Morning walk", priority=0, duration_minutes=20)
    feed = Task("Feed", "Breakfast", priority=1, duration_minutes=10)
    feed.mark_complete()
    pet.add_task(walk)
    pet.add_task(feed)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    default_plan = scheduler.generate_plan(for_date=today)
    full_plan = scheduler.generate_plan(for_date=today, include_completed=True)

    assert "Feed" not in default_plan
    assert "Walk" in default_plan
    assert "Feed" in full_plan


def test_generate_plan_filters_by_pet_name() -> None:
    """!
    @brief generate_plan(pet_name=...) should only schedule the named pet's
           tasks, and an unknown name should yield the no-schedule message
           instead of an error.
    """
    owner = Owner()
    today = date(2026, 7, 17)
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 9, 0))
    )
    rex = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    rex.add_task(Task("Walk", "Morning walk", priority=0, duration_minutes=20))
    mittens = Pet("Mittens", "Cat", date(2021, 1, 1), date(2024, 1, 1))
    mittens.add_task(Task("Litter", "Scoop litter", priority=0, duration_minutes=5))
    owner.add_pet(rex)
    owner.add_pet(mittens)
    scheduler = Scheduler(owner)

    rex_plan = scheduler.generate_plan(pet_name="Rex", for_date=today)
    unknown_plan = scheduler.generate_plan(pet_name="Ghost", for_date=today)

    assert "Rex" in rex_plan
    assert "Mittens" not in rex_plan
    assert unknown_plan == NO_SCHEDULE_MESSAGE


def test_generate_plan_projects_recurring_window_onto_target_date() -> None:
    """!
    @brief A recurring window anchored on an old date must still produce a
           schedulable slot on a later target date, and a one-off window
           for a different day must be excluded from that day's plan.
    """
    owner = Owner()
    owner.add_availability(
        TimeWindow(datetime(2020, 1, 1, 7, 0), datetime(2020, 1, 1, 8, 0), recurring=True)
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 18, 9, 0), datetime(2026, 7, 18, 10, 0))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Morning walk", priority=0, duration_minutes=20))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=date(2026, 7, 17))

    assert "Time: 07:00" in plan


def test_generate_plan_does_not_mutate_owner_availability() -> None:
    """!
    @brief Regression test: generating a plan twice must produce the same
           result both times, since scheduling should consume private
           copies of the owner's TimeWindow objects, not the originals.
    """
    owner = Owner()
    window = TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 8, 0))
    owner.add_availability(window)
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Morning walk", priority=0, duration_minutes=20))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    first_plan = scheduler.generate_plan(for_date=date(2026, 7, 17))
    second_plan = scheduler.generate_plan(for_date=date(2026, 7, 17))

    assert first_plan == second_plan
    assert window.get_start() == datetime(2026, 7, 17, 7, 0)


def test_generate_plan_reuses_leftover_window_time_for_smaller_task() -> None:
    """!
    @brief Regression test: a task too big for the first window must not
           cause that window's leftover time to be discarded -- a later,
           smaller task should still be able to use it.
    """
    owner = Owner()
    today = date(2026, 7, 17)
    small_window = TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 20))
    large_window = TimeWindow(datetime(2026, 7, 17, 8, 0), datetime(2026, 7, 17, 9, 0))
    owner.add_availability(small_window)
    owner.add_availability(large_window)
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Long walk", priority=0, duration_minutes=45))
    pet.add_task(Task("Feed", "Quick feed", priority=1, duration_minutes=10))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=today)

    assert "Time: 08:00" in plan  # the 45-minute walk uses the large window
    assert "Time: 07:00" in plan  # the 10-minute feed reuses the small window's leftover time
    # The 45-minute walk is assigned *before* the 10-minute feed (it's tried
    # first, but doesn't fit the small window), yet it starts *later* in the
    # day -- the printed plan must still read chronologically.
    assert plan.index("Time: 07:00") < plan.index("Time: 08:00")


def test_generate_plan_orders_lines_chronologically_across_pets() -> None:
    """!
    @brief Regression test: tasks are assigned pet-by-pet, so a later pet's
           task can land in an earlier time slot than an earlier pet's task
           (e.g. by backfilling a window's leftover time). generate_plan()
           sorts the finished lines with sorted(..., key=lambda entry: ...)
           on the assigned start time, so the printed order always matches
           the clock, not the assignment order.
    """
    owner = Owner()
    today = date(2026, 7, 17)
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 15))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 9, 0), datetime(2026, 7, 17, 10, 0))
    )
    # Rex is added first and gets a long task that only the 9:00 window fits.
    rex = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    rex.add_task(Task("Walk", "Long walk", priority=0, duration_minutes=50))
    # Mittens is added second but her short task backfills the 7:00 window.
    mittens = Pet("Mittens", "Cat", date(2021, 1, 1), date(2024, 1, 1))
    mittens.add_task(Task("Litter", "Scoop litter", priority=0, duration_minutes=10))
    owner.add_pet(rex)
    owner.add_pet(mittens)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=today)
    lines = plan.splitlines()

    assert "Mittens" in lines[0]
    assert "Rex" in lines[1]
