"""!
@file pawpal_system.py
@brief Core domain model for PawPal+: Owner, Pet, Task, Scheduler (plus the
       supporting TimeWindow value type used for Owner availability).

This module is backend-only. It has no I/O, storage, or UI concerns; it is
meant to be driven by a separate Streamlit front end.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Protocol

## @name Task validation bounds
## @{
MIN_TASK_PRIORITY = 0  ##< Lowest allowed priority value (0 = most urgent).
MIN_TASK_DURATION_MINUTES = 1  ##< Smallest allowed task duration, in minutes.
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

    def mark_complete(self) -> None:
        """!
        @brief Mark this task as completed.
        """
        self.completed = True

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

    def add_task(self, task: Task) -> None:
        """!
        @brief Add a task to this pet's private priority queue.
        @param task The Task to enqueue.
        """
        heapq.heappush(
            self._task_queue, (task.get_priority(), self._insertion_counter, task)
        )
        self._insertion_counter += 1

    def remove_task(self, task: Task) -> None:
        """!
        @brief Remove a specific task from the queue, if present.
        @param task The Task instance to remove (matched by identity).
        """
        for entry in self._task_queue:
            if entry[2] is task:
                self._task_queue.remove(entry)
                heapq.heapify(self._task_queue)
                return

    def get_tasks(self) -> list[Task]:
        """!
        @brief Return a copy of the queued tasks in priority order.
        @return A new list of Task objects, highest priority first.
        """
        return [entry[2] for entry in sorted(self._task_queue)]

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

    def generate_plan(self) -> str:
        """!
        @brief Generate a daily care plan for the owner's pets.

        Time windows are chronologically ordered and filtered/re-ordered by
        _apply_constraints() using the owner's preferences. Each pet's tasks
        are then greedily assigned to the remaining windows in priority
        order (highest priority, i.e. lowest priority number, first),
        subtracting each task's duration from the window as it is used.

        @return A human-readable plan string, one line per scheduled task,
                or a placeholder message if nothing could be scheduled.
        """
        windows = self.owner.get_availability()
        self._apply_constraints(windows, self.owner.get_preferences())

        lines: list[str] = []
        window_iter = iter(windows)
        current = next(window_iter, None)

        for pet in self.owner.get_pets():
            for task in pet.get_tasks():
                remaining = task.get_duration()
                while current is not None:
                    available_minutes = (
                        current.get_end() - current.get_start()
                    ).total_seconds() / 60
                    if available_minutes >= remaining:
                        lines.append(
                            SCHEDULE_FIELD_SEPARATOR.join(
                                [
                                    f"{FIELD_LABEL_TIME}: "
                                    f"{current.get_start().strftime(SCHEDULE_TIME_FORMAT)}",
                                    f"{FIELD_LABEL_NAME}: {pet.get_name()}",
                                    f"{FIELD_LABEL_SPECIES}: {pet.get_species()}",
                                    f"{FIELD_LABEL_AGE}: {pet.get_age_years()}",
                                    f"{FIELD_LABEL_TASK}: {task.get_name()}",
                                    f"{FIELD_LABEL_PRIORITY}: {task.get_priority()}",
                                    f"{FIELD_LABEL_DURATION}: {remaining} "
                                    f"{DURATION_UNIT_LABEL}",
                                ]
                            )
                        )
                        current.start = current.get_start() + timedelta(
                            minutes=remaining
                        )
                        break
                    current = next(window_iter, None)
                if current is None:
                    break

        if not lines:
            return NO_SCHEDULE_MESSAGE
        return "\n".join(lines)

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
