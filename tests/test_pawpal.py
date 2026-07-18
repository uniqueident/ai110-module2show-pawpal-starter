"""!
@file test_pawpal.py
@brief Unit tests for the PawPal+ core domain model.

Run with `python -m pytest` from the project root.
"""

from datetime import date

from pawpal_system import Pet, Task


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
