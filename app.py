from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow

## Maps the UI's friendly priority labels to Task's numeric priority scale
## (0 = most urgent).
PRIORITY_BY_LABEL = {"high": 0, "medium": 1, "low": 2}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owner" not in st.session_state:
    st.session_state.owner = Owner()
owner: Owner = st.session_state.owner


def get_or_create_pet(name: str, species: str) -> Pet:
    """!
    @brief Find the owner's existing pet by name, or add a new one.
    @param name The pet's name, as entered in the UI.
    @param species The pet's species, as entered in the UI.
    @return The matching or newly created Pet.
    """
    for pet in owner.get_pets():
        if pet.get_name() == name:
            return pet
    pet = Pet(name, species, date.today(), date.today())
    owner.add_pet(pet)
    return pet


pet = get_or_create_pet(pet_name, species)

st.markdown("### Tasks")
st.caption("Add a few tasks. They go straight into this pet's task queue.")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    pet.add_task(
        Task(task_title, task_title, PRIORITY_BY_LABEL[priority_label], int(duration))
    )

tasks = pet.get_tasks()
if tasks:
    st.write("Current tasks:")
    st.table(
        [
            {
                "name": t.get_name(),
                "priority": t.get_priority(),
                "duration_minutes": t.get_duration(),
            }
            for t in tasks
        ]
    )
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Availability")
st.caption("Add a time window the owner is free today.")

col_a, col_b = st.columns(2)
with col_a:
    start_time = st.time_input("Start", value=time(7, 0))
with col_b:
    end_time = st.time_input("End", value=time(8, 0))

if st.button("Add availability window"):
    today = date.today()
    owner.add_availability(
        TimeWindow(datetime.combine(today, start_time), datetime.combine(today, end_time))
    )

windows = owner.get_availability()
if windows:
    st.write("Current availability:")
    st.table(
        [
            {
                "start": w.get_start().strftime("%H:%M"),
                "end": w.get_end().strftime("%H:%M"),
            }
            for w in windows
        ]
    )
else:
    st.info("No availability windows yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Generates a plan from the owner's availability and each pet's tasks.")

if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()
    explanation = scheduler.explain_plan(plan)

    st.write("Today's Schedule:")
    st.code(plan)
    st.write("Why this plan:")
    st.write(explanation)
