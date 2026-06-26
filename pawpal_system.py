from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class TimeWindow:
    start: datetime
    end: datetime
    recurring: bool = False

    def get_start(self) -> datetime:
        pass

    def get_end(self) -> datetime:
        pass

    def is_recurring(self) -> bool:
        pass


@dataclass
class Task:
    body: str
    priority: int
    duration_minutes: int

    def get_body(self) -> str:
        pass

    def set_body(self, body: str) -> None:
        pass

    def get_priority(self) -> int:
        pass

    def set_priority(self, priority: int) -> None:
        pass

    def get_duration(self) -> int:
        pass

    def set_duration(self, minutes: int) -> None:
        pass


@dataclass
class Pet:
    name: str
    dob: date
    date_added: date
    # Private priority queue: list of (priority, insertion_order, Task) tuples.
    # Lower priority value = higher urgency (0 is highest).
    # insertion_order breaks ties so equal-priority tasks keep FIFO order.
    _task_queue: list = field(default_factory=list, init=False, repr=False)
    _insertion_counter: int = field(default=0, init=False, repr=False)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def get_tasks(self) -> list:
        """Return a copy of the internal priority queue."""
        pass

    def get_top_task(self) -> Task:
        pass

    def get_name(self) -> str:
        pass

    def get_dob(self) -> date:
        pass

    def get_date_added(self) -> date:
        pass


@dataclass
class Owner:
    availability: list[TimeWindow] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def get_availability(self) -> list[TimeWindow]:
        pass

    def get_preferences(self) -> list[str]:
        pass

    def set_preferences(self, prefs: list[str]) -> None:
        pass

    def get_pets(self) -> list[Pet]:
        pass

    def add_pet(self, pet: Pet) -> None:
        pass


@dataclass
class Scheduler:
    owner: Owner
    llm: Optional[object] = None  # Any OpenAI-compatible LLMClient

    def generate_plan(self) -> str:
        pass

    def explain_plan(self, plan: str) -> str:
        pass

    def _apply_constraints(
        self, windows: list[TimeWindow], preferences: list[str]
    ) -> None:
        pass

    def _rule_based_explanation(self, plan: str) -> str:
        pass
