"""!
@file pawpal_system.py
@brief Core domain model for PawPal+: Owner, Pet, Task, Scheduler (plus the
       supporting TimeWindow value type used for Owner availability).

This module is backend-only. It has no I/O, storage, or UI concerns; it is
meant to be driven by a separate Streamlit front end.
"""

from __future__ import annotations

import heapq
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Protocol

## @name Task validation bounds
## @{
MIN_TASK_PRIORITY = 0  ##< Lowest allowed priority value (0 = most urgent).
MIN_TASK_DURATION_MINUTES = 1  ##< Smallest allowed task duration, in minutes.
## @}

## @name Task recurrence
## Maps a Task's recurrence label to the timedelta added to today's date to
## compute the next occurrence's due date, used by Task.create_next_occurrence().
## @{
TASK_RECURRENCE_DAILY = "daily"  ##< Recurs every day.
TASK_RECURRENCE_WEEKLY = "weekly"  ##< Recurs every week.
TASK_RECURRENCE_INTERVALS = {
    TASK_RECURRENCE_DAILY: timedelta(days=1),
    TASK_RECURRENCE_WEEKLY: timedelta(days=7),
}
## @}

## @name Schedule line formatting
## @{
SCHEDULE_TIME_FORMAT = "%H:%M"  ##< strftime format used for schedule times.
SCHEDULE_FIELD_SEPARATOR = " | "  ##< Joins schedule line fields, CSV-style.
DURATION_UNIT_LABEL = "min"  ##< Unit suffix shown after a duration value.
FIELD_LABEL_TIME = "Time"  ##< Label for the scheduled start time field.
FIELD_LABEL_NAME = "Name"  ##< Label for the pet's name field.
FIELD_LABEL_SPECIES = "Species"  ##< Label for the pet's species field.
FIELD_LABEL_AGE = "Age"  ##< Label for the pet's age field.
FIELD_LABEL_TASK = "Task"  ##< Label for the task name field.
FIELD_LABEL_PRIORITY = "Priority"  ##< Label for the task priority field.
FIELD_LABEL_DURATION = "Duration"  ##< Label for the task duration field.
NO_SCHEDULE_MESSAGE = (
    "No tasks could be scheduled with the available time windows."
)  ##< Returned by generate_plan() when nothing could be fit into a window.
## @}

## @name Time-of-day preference matching
## Maps a preference keyword to the range of hours (24h clock) it covers, used
## by Scheduler._apply_constraints() to prioritize matching time windows.
## @{
TIME_OF_DAY_HOURS = {
    "morning": range(5, 12),
    "afternoon": range(12, 17),
    "evening": range(17, 21),
    "night": range(21, 24),
}
## @}


class LLMClient(Protocol):
    """!
    @brief Minimal OpenAI-API-compatible client shape Scheduler expects.

    Any object with a matching @c complete(prompt) -> str method can be
    passed to Scheduler.llm; PawPal+ does not depend on a specific SDK.
    """

    def complete(self, prompt: str) -> str:
        """!
        @brief Generate a text completion for the given prompt.
        @param prompt The prompt text.
        @return The model's response text.
        """
        ...


@dataclass
class TimeWindow:
    """!
    @brief A single block of time during which an Owner is available.

    A TimeWindow can either be a one-off block (@c recurring is False) or a
    recurring block, e.g. "every day 7-8am" (@c recurring is True).
    """

    start: datetime
    end: datetime
    recurring: bool = False

    def get_start(self) -> datetime:
        """!
        @brief Get the start of the window.
        @return The window's start datetime.
        """
        return self.start

    def get_end(self) -> datetime:
        """!
        @brief Get the end of the window.
        @return The window's end datetime.
        """
        return self.end

    def is_recurring(self) -> bool:
        """!
        @brief Check whether this window repeats.
        @return True if the window is recurring, False if it is a one-off.
        """
        return self.recurring

    def occurs_on(self, day: date) -> bool:
        """!
        @brief Check whether this window has an occurrence on @p day.

        Recurring windows occur on every calendar day. One-off windows only
        occur on the single day they were scheduled for.

        @param day The calendar date to check.
        @return True if this window has an occurrence on @p day.
        """
        if self.recurring:
            return True
        return self.start.date() == day

    def for_day(self, day: date) -> "TimeWindow":
        """!
        @brief Project this window's time-of-day onto a specific calendar day.

        Keeps the window's duration and recurring flag, but replaces the
        date component of @c start (and, by extension, @c end) with @p day.
        This is what lets a recurring window (e.g. "every day 7-8am") be
        turned into a concrete, schedulable block for a given date instead
        of forever reusing whatever anchor date it was first created with.

        @param day The calendar date to project onto.
        @return A new TimeWindow occurring on @p day.
        """
        duration = self.end - self.start
        new_start = datetime.combine(day, self.start.time())
        return TimeWindow(new_start, new_start + duration, self.recurring)

    def overlaps(self, other: "TimeWindow") -> bool:
        """!
        @brief Check whether this window's time conflicts with @p other's.

        Two one-off windows conflict if their absolute datetime ranges
        intersect. If either window is recurring, both are first projected
        onto the same reference day (the one-off window's day, if there is
        one) so that, e.g., a recurring "7-8am daily" window is correctly
        flagged as conflicting with a one-off "7:30-8am" appointment on any
        day, not just the recurring window's original anchor date.

        @param other The TimeWindow to compare against.
        @return True if the two windows overlap in time.
        """
        if not self.recurring and not other.recurring:
            return self.start < other.end and other.start < self.end

        reference = (
            self.start.date() if not self.recurring else other.start.date()
        )
        a = self.for_day(reference)
        b = other.for_day(reference)
        return a.start < b.end and b.start < a.end


@dataclass
class Task:
    """!
    @brief A single pet care task (walk, feeding, meds, enrichment, etc.).

    Priority is a whole number where 0 is the highest priority and larger
    numbers are progressively lower priority.
    """

    name: str
    body: str
    priority: int
    duration_minutes: int
    completed: bool = False
    recurrence: Optional[str] = None
    due_date: Optional[date] = None

    def get_name(self) -> str:
        """!
        @brief Get the task's short name.
        @return The task name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """!
        @brief Rename the task.
        @param name The new task name.
        """
        self.name = name

    def get_body(self) -> str:
        """!
        @brief Get the task's descriptive body text.
        @return The task body.
        """
        return self.body

    def set_body(self, body: str) -> None:
        """!
        @brief Replace the task's descriptive body text.
        @param body The new body text.
        """
        self.body = body

    def get_priority(self) -> int:
        """!
        @brief Get the task's priority.
        @return The priority, where 0 is the most urgent.
        """
        return self.priority

    def set_priority(self, priority: int) -> None:
        """!
        @brief Change the task's priority.
        @param priority The new priority; must be a whole number >= 0.
        @throws ValueError if priority is negative.
        """
        if priority < MIN_TASK_PRIORITY:
            raise ValueError(f"priority must be a whole number >= {MIN_TASK_PRIORITY}")
        self.priority = priority

    def get_duration(self) -> int:
        """!
        @brief Get the estimated duration of the task.
        @return Duration in minutes.
        """
        return self.duration_minutes

    def set_duration(self, minutes: int) -> None:
        """!
        @brief Change the estimated duration of the task.
        @param minutes New duration in minutes; must be positive.
        @throws ValueError if minutes is not positive.
        """
        if minutes < MIN_TASK_DURATION_MINUTES:
            raise ValueError(
                f"duration_minutes must be >= {MIN_TASK_DURATION_MINUTES}"
            )
        self.duration_minutes = minutes

    def get_recurrence(self) -> Optional[str]:
        """!
        @brief Get this task's recurrence.
        @return TASK_RECURRENCE_DAILY, TASK_RECURRENCE_WEEKLY, or None if
                this task is a one-off.
        """
        return self.recurrence

    def set_recurrence(self, recurrence: Optional[str]) -> None:
        """!
        @brief Set this task's recurrence.
        @param recurrence TASK_RECURRENCE_DAILY, TASK_RECURRENCE_WEEKLY, or
               None to make the task a one-off.
        @throws ValueError if recurrence is not one of the supported values.
        """
        if recurrence is not None and recurrence not in TASK_RECURRENCE_INTERVALS:
            raise ValueError(
                f"recurrence must be one of {sorted(TASK_RECURRENCE_INTERVALS)} or None"
            )
        self.recurrence = recurrence

    def is_recurring(self) -> bool:
        """!
        @brief Check whether this task recurs.
        @return True if this task has a recurrence set.
        """
        return self.recurrence is not None

    def get_due_date(self) -> Optional[date]:
        """!
        @brief Get this task's due date.
        @return The due date, or None if it hasn't been set.
        """
        return self.due_date

    def set_due_date(self, due_date: Optional[date]) -> None:
        """!
        @brief Set this task's due date.
        @param due_date The new due date, or None to clear it.
        """
        self.due_date = due_date

    def create_next_occurrence(self, as_of: Optional[date] = None) -> Optional["Task"]:
        """!
        @brief Build the next occurrence of this task, if it recurs.

        The new due date is computed as @p as_of (or today, if not given)
        plus this task's recurrence interval -- e.g. a daily task completed
        today is due again today + timedelta(days=1).

        @param as_of Date to measure the recurrence interval from; defaults
               to today.
        @return A new, pending Task with the same name/body/priority/
                duration/recurrence as this one, due on the next occurrence
                date. None if this task doesn't recur.
        """
        if self.recurrence is None:
            return None
        reference = as_of or date.today()
        next_due = reference + TASK_RECURRENCE_INTERVALS[self.recurrence]
        return Task(
            name=self.name,
            body=self.body,
            priority=self.priority,
            duration_minutes=self.duration_minutes,
            completed=False,
            recurrence=self.recurrence,
            due_date=next_due,
        )

    def mark_complete(self) -> Optional["Task"]:
        """!
        @brief Mark this task as completed.

        If this task recurs (daily/weekly), also builds its next occurrence
        via create_next_occurrence() -- callers that want that occurrence
        actually scheduled should enqueue it themselves, or use
        Pet.complete_task() which does so automatically.

        @return The newly created next-occurrence Task, or None if this
                task doesn't recur.
        """
        self.completed = True
        return self.create_next_occurrence()

    def is_complete(self) -> bool:
        """!
        @brief Check whether this task has been completed.
        @return True if the task is complete, False otherwise.
        """
        return self.completed


@dataclass
class Pet:
    """!
    @brief A pet owned by an Owner, along with its private task priority queue.

    Tasks are stored in a private min-heap keyed on (priority, insertion
    order), so lower @c priority values are popped first, and tasks that
    share a priority are kept in FIFO order (later-added tasks sort below
    earlier ones of the same priority). No object outside of Pet may touch
    the queue directly -- only through add_task/remove_task/get_tasks/
    get_top_task.
    """

    name: str
    species: str
    dob: date
    date_added: date
    # Private priority queue: list of (priority, insertion_order, Task) tuples.
    # Lower priority value = higher urgency (0 is highest).
    # insertion_order breaks ties so equal-priority tasks keep FIFO order.
    _task_queue: list = field(default_factory=list, init=False, repr=False)
    _insertion_counter: int = field(default=0, init=False, repr=False)
    # Cache of get_tasks()'s sorted output; invalidated on add_task/remove_task
    # so repeated get_tasks() calls between mutations don't re-sort for nothing.
    _sorted_cache: Optional[list] = field(default=None, init=False, repr=False)

    def add_task(self, task: Task) -> None:
        """!
        @brief Add a task to this pet's private priority queue.
        @param task The Task to enqueue.
        """
        heapq.heappush(
            self._task_queue, (task.get_priority(), self._insertion_counter, task)
        )
        self._insertion_counter += 1
        self._sorted_cache = None

    def remove_task(self, task: Task) -> None:
        """!
        @brief Remove a specific task from the queue, if present.
        @param task The Task instance to remove (matched by identity).
        """
        for entry in self._task_queue:
            if entry[2] is task:
                self._task_queue.remove(entry)
                heapq.heapify(self._task_queue)
                self._sorted_cache = None
                return

    def complete_task(self, task: Task) -> Optional[Task]:
        """!
        @brief Mark one of this pet's queued tasks complete.

        If @p task recurs (daily/weekly), its next occurrence is
        automatically enqueued on this pet via add_task(), so a recurring
        task never needs to be manually re-added after it's done.

        @param task The Task to complete (should already be queued here).
        @return The newly enqueued next-occurrence Task, or None if
                @p task doesn't recur.
        """
        next_task = task.mark_complete()
        if next_task is not None:
            self.add_task(next_task)
        return next_task

    def get_tasks(self, completed: Optional[bool] = None) -> list[Task]:
        """!
        @brief Return a copy of the queued tasks in priority order.
        @param completed Status filter: None (default) returns every task,
               True returns only completed tasks, False returns only tasks
               still pending.
        @return A new list of Task objects, highest priority first.
        """
        if self._sorted_cache is None:
            self._sorted_cache = [entry[2] for entry in sorted(self._task_queue)]
        if completed is None:
            return list(self._sorted_cache)
        return [task for task in self._sorted_cache if task.is_complete() == completed]

    def get_top_task(self) -> Optional[Task]:
        """!
        @brief Peek at the most important queued task without removing it.
        @return The highest-priority Task, or None if the queue is empty.
        """
        if not self._task_queue:
            return None
        return min(self._task_queue)[2]

    def get_name(self) -> str:
        """!
        @brief Get the pet's name.
        @return The pet's name.
        """
        return self.name

    def get_species(self) -> str:
        """!
        @brief Get the pet's species (e.g. "Dog", "Cat", "Parrot").
        @return The pet's species.
        """
        return self.species

    def get_dob(self) -> date:
        """!
        @brief Get the pet's date of birth.
        @return The pet's DOB.
        """
        return self.dob

    def get_age_years(self, as_of: Optional[date] = None) -> int:
        """!
        @brief Compute the pet's whole-number age in years.
        @param as_of Date to measure the age against; defaults to today.
        @return Age in full years as of @p as_of.
        """
        reference = as_of or date.today()
        had_birthday = (reference.month, reference.day) >= (
            self.dob.month,
            self.dob.day,
        )
        return reference.year - self.dob.year - (0 if had_birthday else 1)

    def get_date_added(self) -> date:
        """!
        @brief Get the date this pet was added to the system.
        @return The date added.
        """
        return self.date_added


@dataclass
class Owner:
    """!
    @brief A pet owner: their availability, scheduling preferences, and pets.
    """

    availability: list[TimeWindow] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def get_availability(self) -> list[TimeWindow]:
        """!
        @brief Get the owner's available time windows.
        @return A copy of the list of TimeWindow objects.
        """
        return list(self.availability)

    def add_availability(self, window: TimeWindow) -> None:
        """!
        @brief Add a time window during which the owner is available.
        @param window The TimeWindow to add.
        """
        self.availability.append(window)

    def get_conflicting_windows(self) -> list[tuple[TimeWindow, TimeWindow]]:
        """!
        @brief Find pairs of availability windows that overlap in time.

        Compares every pair of windows with TimeWindow.overlaps(), which
        correctly accounts for recurring windows by projecting them onto a
        shared reference day before comparing.

        @return A list of (window, window) pairs that conflict. Each pair
                is only reported once, in the order the windows were added.
        """
        conflicts: list[tuple[TimeWindow, TimeWindow]] = []
        for i, first in enumerate(self.availability):
            for second in self.availability[i + 1 :]:
                if first.overlaps(second):
                    conflicts.append((first, second))
        return conflicts

    def get_preferences(self) -> list[str]:
        """!
        @brief Get the owner's scheduling preferences.
        @return A copy of the list of preference strings.
        """
        return list(self.preferences)

    def set_preferences(self, prefs: list[str]) -> None:
        """!
        @brief Replace the owner's scheduling preferences.
        @param prefs The new list of preference strings.
        """
        self.preferences = list(prefs)

    def get_pets(self) -> list[Pet]:
        """!
        @brief Get the owner's pets.
        @return A copy of the list of Pet objects.
        """
        return list(self.pets)

    def add_pet(self, pet: Pet) -> None:
        """!
        @brief Add a pet to this owner.
        @param pet The Pet to add.
        """
        self.pets.append(pet)

    def get_pet(self, name: str) -> Optional[Pet]:
        """!
        @brief Look up one of this owner's pets by name.
        @param name The pet's name to search for (exact match).
        @return The matching Pet, or None if no pet has that name.
        """
        for pet in self.pets:
            if pet.get_name() == name:
                return pet
        return None


@dataclass
class Scheduler:
    """!
    @brief Builds a daily care plan for an Owner's pets and explains it.

    Scheduler consumes an Owner (and, through it, all of the Owner's Pets
    and their queued Tasks) plus the Owner's time windows and preferences to
    produce a plan, which is always represented as a plain string.

    @c llm is an optional, duck-typed, OpenAI-API-compatible client used only
    to phrase the plan's explanation. It is expected to expose a
    @c complete(prompt: str) -> str method. If it is absent, or if calling it
    fails for any reason, explain_plan falls back to a deterministic,
    rule-based explanation.
    """

    owner: Owner
    llm: Optional[LLMClient] = None

    def generate_plan(
        self,
        pet_name: Optional[str] = None,
        include_completed: bool = False,
        for_date: Optional[date] = None,
    ) -> str:
        """!
        @brief Generate a daily care plan for the owner's pets.

        Time windows are chronologically ordered and filtered/re-ordered by
        _apply_constraints() using the owner's preferences. Each pet's tasks
        are then greedily assigned to the first window with enough remaining
        time, in priority order (highest priority, i.e. lowest priority
        number, first), subtracting each task's duration from the window as
        it is used. Windows too small for one task are kept in play for a
        later, shorter task rather than being discarded.

        Only windows that actually occur on @p for_date are considered:
        recurring windows are projected onto that date via
        TimeWindow.for_day(), and one-off windows are used only if their
        stored date matches. Scheduling works on private copies of the
        owner's TimeWindow objects, so repeated calls never shrink the
        owner's real availability.

        Tasks are assigned to windows pet-by-pet, so a later pet's task can
        legitimately land in an earlier time slot than an earlier pet's task
        (e.g. by reusing a small window's leftover time, see the loop
        above). The scheduled lines are therefore sorted by their assigned
        start time via @c sorted(..., key=lambda entry: entry[0]) before
        being joined, so the printed plan always reads in chronological
        order regardless of the order tasks were assigned in.

        @param pet_name If given, only that pet's tasks are scheduled
               (unknown names produce an empty plan). If None, every pet's
               tasks are scheduled.
        @param include_completed If True, already-completed tasks are
               scheduled too; by default they're skipped.
        @param for_date The calendar date to build the plan for; defaults to
               today. Determines which windows (especially recurring ones)
               are in play.
        @return A human-readable plan string, one line per scheduled task,
                or a placeholder message if nothing could be scheduled.
        """
        self._warn_conflicts()

        target_date = for_date or date.today()
        windows = [
            w.for_day(target_date) if w.is_recurring() else TimeWindow(
                w.get_start(), w.get_end(), w.is_recurring()
            )
            for w in self.owner.get_availability()
            if w.occurs_on(target_date)
        ]
        self._apply_constraints(windows, self.owner.get_preferences())

        if pet_name is not None:
            pet = self.owner.get_pet(pet_name)
            pets = [pet] if pet is not None else []
        else:
            pets = self.owner.get_pets()

        # Each entry is (scheduled_start_time, formatted_line); sorted below
        # so the plan reads chronologically regardless of assignment order.
        entries: list[tuple[datetime, str]] = []

        for pet in pets:
            status_filter = None if include_completed else False
            for task in pet.get_tasks(completed=status_filter):
                remaining = task.get_duration()
                for window in windows:
                    available_minutes = (
                        window.get_end() - window.get_start()
                    ).total_seconds() / 60
                    if available_minutes >= remaining:
                        start_time = window.get_start()
                        entries.append(
                            (
                                start_time,
                                SCHEDULE_FIELD_SEPARATOR.join(
                                    [
                                        f"{FIELD_LABEL_TIME}: "
                                        f"{start_time.strftime(SCHEDULE_TIME_FORMAT)}",
                                        f"{FIELD_LABEL_NAME}: {pet.get_name()}",
                                        f"{FIELD_LABEL_SPECIES}: {pet.get_species()}",
                                        f"{FIELD_LABEL_AGE}: {pet.get_age_years()}",
                                        f"{FIELD_LABEL_TASK}: {task.get_name()}",
                                        f"{FIELD_LABEL_PRIORITY}: {task.get_priority()}",
                                        f"{FIELD_LABEL_DURATION}: {remaining} "
                                        f"{DURATION_UNIT_LABEL}",
                                    ]
                                ),
                            )
                        )
                        window.start = window.get_start() + timedelta(
                            minutes=remaining
                        )
                        break

        if not entries:
            return NO_SCHEDULE_MESSAGE
        entries = sorted(entries, key=lambda entry: entry[0])
        return "\n".join(line for _, line in entries)

    def explain_plan(self, plan: str) -> str:
        """!
        @brief Explain why the plan looks the way it does.

        Tries the configured LLM first (if any); falls back to a
        deterministic rule-based explanation if no LLM is configured or the
        LLM call raises an exception.

        @param plan The plan string produced by generate_plan().
        @return A natural-language explanation of the plan.
        """
        if self.llm is not None:
            try:
                prompt = (
                    "Explain, in a friendly and concise way, why the "
                    "following pet care plan was scheduled in this order, "
                    "given the owner's stated preferences "
                    f"{self.owner.get_preferences()}:\n\n{plan}"
                )
                return self.llm.complete(prompt)
            except Exception:
                pass
        return self._rule_based_explanation(plan)

    def _warn_conflicts(self) -> None:
        """!
        @brief Print a warning for each pair of overlapping availability
               windows on the owner, via Owner.get_conflicting_windows().

        This only surfaces the conflicts; it doesn't resolve them or affect
        scheduling -- both windows in a conflicting pair remain usable.
        """
        for first, second in self.owner.get_conflicting_windows():
            print(
                f"Warning: overlapping availability windows "
                f"({first.get_start()} - {first.get_end()}) and "
                f"({second.get_start()} - {second.get_end()})",
                file=sys.stderr,
            )

    def _apply_constraints(
        self, windows: list[TimeWindow], preferences: list[str]
    ) -> None:
        """!
        @brief Order and filter time windows according to owner constraints.

        Windows are sorted chronologically by start time. If any preference
        strings name a time of day (morning/afternoon/evening/night), windows
        starting in a preferred part of the day are moved to the front,
        preserving chronological order within each group.

        @param windows The list of TimeWindow objects to reorder in place.
        @param preferences The owner's preference strings.
        """
        windows.sort(key=lambda w: w.get_start())

        preferred_hours: set[int] = set()
        for pref in preferences:
            pref_lower = pref.lower()
            for name, hours in TIME_OF_DAY_HOURS.items():
                if name in pref_lower:
                    preferred_hours.update(hours)

        if not preferred_hours:
            return

        preferred = [w for w in windows if w.get_start().hour in preferred_hours]
        other = [w for w in windows if w.get_start().hour not in preferred_hours]
        windows[:] = preferred + other

    def _rule_based_explanation(self, plan: str) -> str:
        """!
        @brief Produce a deterministic explanation without an LLM.
        @param plan The plan string produced by generate_plan().
        @return A rule-based explanation of the scheduling decisions.
        """
        if not plan or plan == NO_SCHEDULE_MESSAGE:
            return (
                "No plan could be produced: there were no available time "
                "windows large enough for any queued task."
            )

        prefs = self.owner.get_preferences()
        pref_note = (
            f" Preferences considered: {', '.join(prefs)}." if prefs else ""
        )
        return (
            "Tasks were scheduled into the owner's available time windows in "
            "chronological order, assigning each pet's highest-priority "
            "task (lowest priority number) first and moving to the next "
            "task once a window's time was used up." + pref_note
        )
