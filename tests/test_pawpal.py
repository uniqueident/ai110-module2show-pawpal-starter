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


def test_pet_get_tasks_orders_equal_priority_tasks_by_insertion_order() -> None:
    """!
    @brief Two tasks sharing a priority must come back in the order they
           were added (FIFO), not in an arbitrary or reversed order -- the
           heap is keyed on (priority, insertion_order, task) specifically
           to guarantee this tie-break.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    first = Task("Walk", "Morning walk", priority=1, duration_minutes=20)
    second = Task("Brush", "Brush coat", priority=1, duration_minutes=5)
    pet.add_task(first)
    pet.add_task(second)

    assert pet.get_tasks() == [first, second]


def test_pet_get_top_task_returns_highest_priority_without_removing() -> None:
    """!
    @brief get_top_task() should peek at the most urgent (lowest-numbered
           priority) task and leave the queue untouched, so repeated calls
           keep returning the same task until it is explicitly removed or
           completed.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    low_priority = Task("Play", "Fetch", priority=3, duration_minutes=15)
    urgent = Task("Meds", "Evening pill", priority=0, duration_minutes=5)
    pet.add_task(low_priority)
    pet.add_task(urgent)

    assert pet.get_top_task() is urgent
    assert pet.get_top_task() is urgent  # peeking again doesn't consume it
    assert len(pet.get_tasks()) == 2


def test_pet_remove_task_keeps_remaining_tasks_in_priority_order() -> None:
    """!
    @brief remove_task() rebuilds the heap by hand (list.remove + heapify)
           instead of using a library removal helper, so this checks that
           path doesn't corrupt ordering for the tasks left behind,
           including when the removed task isn't the current top.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    urgent = Task("Meds", "Evening pill", priority=0, duration_minutes=5)
    middle = Task("Walk", "Morning walk", priority=1, duration_minutes=20)
    low = Task("Play", "Fetch", priority=2, duration_minutes=15)
    pet.add_task(urgent)
    pet.add_task(middle)
    pet.add_task(low)

    pet.remove_task(middle)

    assert pet.get_tasks() == [urgent, low]
    assert pet.get_top_task() is urgent


def test_task_create_next_occurrence_daily_and_weekly() -> None:
    """!
    @brief create_next_occurrence() must add exactly one recurrence
           interval to the given reference date -- one day for a daily
           task, seven for a weekly one -- while carrying over the rest of
           the task's fields and resetting completed to False.
    """
    reference = date(2026, 7, 17)
    daily = Task("Feed", "Breakfast", priority=0, duration_minutes=10, recurrence="daily")
    weekly = Task("Groom", "Brush and trim", priority=2, duration_minutes=30, recurrence="weekly")

    next_daily = daily.create_next_occurrence(as_of=reference)
    next_weekly = weekly.create_next_occurrence(as_of=reference)

    assert next_daily is not None
    assert next_weekly is not None
    assert next_daily.get_due_date() == date(2026, 7, 18)
    assert next_daily.get_name() == "Feed"
    assert next_daily.is_complete() is False
    assert next_weekly.get_due_date() == date(2026, 7, 24)


def test_task_mark_complete_returns_none_for_non_recurring_task() -> None:
    """!
    @brief mark_complete() on a one-off (non-recurring) task must return
           None rather than a next occurrence -- Pet.complete_task() relies
           on this None to decide whether to enqueue a follow-up task.
    """
    task = Task("Walk", "Morning walk", priority=0, duration_minutes=20)

    assert task.mark_complete() is None


def test_pet_complete_task_requeues_recurring_task() -> None:
    """!
    @brief complete_task() should automatically enqueue a recurring task's
           next occurrence onto the same pet, so callers never have to
           manually re-add a daily/weekly task after finishing it.
    """
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    feed = Task("Feed", "Breakfast", priority=0, duration_minutes=10, recurrence="daily")
    pet.add_task(feed)

    next_task = pet.complete_task(feed)

    assert feed.is_complete() is True
    assert next_task is not None
    assert next_task.get_name() == "Feed"
    assert next_task.is_complete() is False
    assert pet.get_tasks() == [feed, next_task]


def test_timewindow_overlaps_true_for_two_recurring_windows_with_different_anchors() -> None:
    """!
    @brief Two recurring windows must be compared by time-of-day alone,
           regardless of how far apart their original anchor dates are --
           this exercises the both-recurring branch of overlaps(), distinct
           from the recurring-vs-one-off case already covered above.
    """
    early_anchor = TimeWindow(
        datetime(2020, 1, 1, 7, 0), datetime(2020, 1, 1, 8, 0), recurring=True
    )
    late_anchor = TimeWindow(
        datetime(2022, 6, 15, 7, 30), datetime(2022, 6, 15, 7, 45), recurring=True
    )

    assert early_anchor.overlaps(late_anchor) is True
    assert late_anchor.overlaps(early_anchor) is True


def test_owner_get_conflicting_windows_detects_recurring_pair() -> None:
    """!
    @brief Regression/integration check that Owner.get_conflicting_windows()
           actually delegates to TimeWindow.overlaps() for a pair of
           recurring windows, not just the one-off pair already covered --
           a naive datetime-range comparison would miss this since the two
           windows' anchor dates are years apart.
    """
    owner = Owner()
    recurring_a = TimeWindow(
        datetime(2020, 1, 1, 7, 0), datetime(2020, 1, 1, 8, 0), recurring=True
    )
    recurring_b = TimeWindow(
        datetime(2022, 6, 15, 7, 30), datetime(2022, 6, 15, 7, 45), recurring=True
    )
    owner.add_availability(recurring_a)
    owner.add_availability(recurring_b)

    assert owner.get_conflicting_windows() == [(recurring_a, recurring_b)]


def test_generate_plan_prioritizes_preferred_time_of_day_window() -> None:
    """!
    @brief When only one window can hold a single task, an "evening"
           preference must steer that task into the evening window instead
           of the chronologically-earlier morning one -- _apply_constraints()
           reorders windows by preference before greedy assignment runs.
    """
    owner = Owner()
    owner.set_preferences(["evening walks please"])
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 30))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 18, 0), datetime(2026, 7, 17, 18, 30))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Evening walk", priority=0, duration_minutes=30))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=date(2026, 7, 17))

    assert "Time: 18:00" in plan
    assert "Time: 07:00" not in plan


def test_generate_plan_returns_no_schedule_message_when_task_exceeds_all_windows() -> None:
    """!
    @brief A task that is longer than every available window must be
           silently skipped rather than crashing or being force-fit, and
           generate_plan() should fall back to NO_SCHEDULE_MESSAGE when
           that leaves nothing schedulable.
    """
    owner = Owner()
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 10))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Long walk", priority=0, duration_minutes=30))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=date(2026, 7, 17))

    assert plan == NO_SCHEDULE_MESSAGE


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


class _StubLLM:
    """!
    @brief Fake LLMClient that returns a fixed completion string.

    Used to verify explain_plan()'s "LLM available" branch without needing a
    real OpenAI-API-compatible client.
    """

    def __init__(self, response: str) -> None:
        self.response = response
        self.received_prompt: str | None = None

    def complete(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self.response


class _RaisingLLM:
    """!
    @brief Fake LLMClient whose complete() always raises, to verify
           explain_plan() falls back to the rule-based explanation instead
           of propagating the error.
    """

    def complete(self, prompt: str) -> str:
        raise RuntimeError("simulated LLM failure")


def test_explain_plan_uses_llm_response_when_llm_configured() -> None:
    """!
    @brief explain_plan() should return the configured LLM's completion
           verbatim, and must pass it the plan text plus the owner's
           preferences so the model has context to explain the ordering.
    """
    owner = Owner()
    owner.set_preferences(["morning walks"])
    llm = _StubLLM("Here is why your plan looks like this.")
    scheduler = Scheduler(owner, llm=llm)

    explanation = scheduler.explain_plan("Time: 07:00 | Name: Rex | Task: Walk")

    assert explanation == "Here is why your plan looks like this."
    assert llm.received_prompt is not None
    assert "morning walks" in llm.received_prompt
    assert "Time: 07:00" in llm.received_prompt


def test_explain_plan_falls_back_to_rule_based_when_llm_raises() -> None:
    """!
    @brief If the configured LLM's complete() raises for any reason,
           explain_plan() must swallow the exception and fall back to the
           deterministic rule-based explanation rather than propagating it.
    """
    owner = Owner()
    scheduler = Scheduler(owner, llm=_RaisingLLM())

    explanation = scheduler.explain_plan("Time: 07:00 | Name: Rex | Task: Walk")

    assert "scheduled into the owner's available time windows" in explanation


def test_explain_plan_uses_rule_based_explanation_without_llm() -> None:
    """!
    @brief With no LLM configured, explain_plan() should go straight to the
           deterministic explanation and mention any owner preferences that
           were considered.
    """
    owner = Owner()
    owner.set_preferences(["morning walks", "evening feedings"])
    scheduler = Scheduler(owner)

    explanation = scheduler.explain_plan("Time: 07:00 | Name: Rex | Task: Walk")

    assert "Preferences considered: morning walks, evening feedings." in explanation


def test_explain_plan_omits_preferences_note_when_none_set() -> None:
    """!
    @brief The rule-based explanation should not mention preferences at all
           when the owner has none set, rather than printing an empty list.
    """
    owner = Owner()
    scheduler = Scheduler(owner)

    explanation = scheduler.explain_plan("Time: 07:00 | Name: Rex | Task: Walk")

    assert "Preferences considered" not in explanation


def test_explain_plan_explains_no_schedule_message_distinctly() -> None:
    """!
    @brief When the plan is the NO_SCHEDULE_MESSAGE placeholder, the
           rule-based explanation must describe the lack of a schedule
           instead of talking about task ordering that didn't happen.
    """
    owner = Owner()
    scheduler = Scheduler(owner)

    explanation = scheduler.explain_plan(NO_SCHEDULE_MESSAGE)

    assert "No plan could be produced" in explanation


def test_task_set_priority_rejects_negative_value() -> None:
    """!
    @brief set_priority() must reject negative priorities with a ValueError
           and leave the task's existing priority unchanged.
    """
    task = Task("Walk", "Morning walk", priority=1, duration_minutes=20)

    try:
        task.set_priority(-1)
        assert False, "expected ValueError"
    except ValueError:
        pass

    assert task.get_priority() == 1


def test_task_set_duration_rejects_non_positive_value() -> None:
    """!
    @brief set_duration() must reject a duration below
           MIN_TASK_DURATION_MINUTES with a ValueError and leave the task's
           existing duration unchanged.
    """
    task = Task("Walk", "Morning walk", priority=1, duration_minutes=20)

    try:
        task.set_duration(0)
        assert False, "expected ValueError"
    except ValueError:
        pass

    assert task.get_duration() == 20


def test_task_set_recurrence_rejects_unsupported_value() -> None:
    """!
    @brief set_recurrence() must only accept "daily", "weekly", or None --
           any other string should raise ValueError and leave the task's
           existing recurrence unchanged.
    """
    task = Task("Feed", "Breakfast", priority=0, duration_minutes=10, recurrence="daily")

    try:
        task.set_recurrence("hourly")
        assert False, "expected ValueError"
    except ValueError:
        pass

    assert task.get_recurrence() == "daily"


def test_generate_plan_schedules_task_that_exactly_fills_window() -> None:
    """!
    @brief Boundary check: a task whose duration exactly equals a window's
           remaining minutes must still be scheduled (the ">=" comparison
           in generate_plan(), not strictly ">"), and must consume the
           entire window rather than leaving a negative remainder.
    """
    owner = Owner()
    today = date(2026, 7, 17)
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 30))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Morning walk", priority=0, duration_minutes=30))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=today)

    assert "Time: 07:00" in plan
    assert "Duration: 30 min" in plan


def test_generate_plan_ignores_unmatched_preference_keyword() -> None:
    """!
    @brief A preference string that names no recognized time-of-day keyword
           (morning/afternoon/evening/night) must leave window ordering
           untouched -- _apply_constraints() should return early instead of
           reordering on an empty preferred-hours set.
    """
    owner = Owner()
    owner.set_preferences(["no dogs on weekends"])
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 18, 0), datetime(2026, 7, 17, 18, 30))
    )
    owner.add_availability(
        TimeWindow(datetime(2026, 7, 17, 7, 0), datetime(2026, 7, 17, 7, 30))
    )
    pet = Pet("Rex", "Dog", date(2020, 1, 1), date(2024, 1, 1))
    pet.add_task(Task("Walk", "Morning walk", priority=0, duration_minutes=30))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(for_date=date(2026, 7, 17))

    # Windows stay in chronological order (7:00 before 18:00), so the task
    # is greedily assigned to the earlier 7:00 window, not the 18:00 one.
    assert "Time: 07:00" in plan
    assert "Time: 18:00" not in plan
