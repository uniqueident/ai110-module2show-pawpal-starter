# PawPal+ Guide

PawPal assists in helping a pet owner **plan care tasks for their pet.**

## Core actions

A pet owner must have an assistant application that does the following:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan.

# Components

Focusing on how the task should be split up, we should have **four** main components: Owner, Pet, Task, Scheduler.

These four components must be an individual class within the system.

Owner, Pet, and Task must be Separate from each other.

## Owner

Owner must have the following: Time availability (total time in day, as well as slots of time (windows) for scheduling reasons), preferences that the owner would prefer to perform actions in a certain order, and a list of pets owned by the owner.

Time availablity can be reoccuring or one-off, and must encapsulate both.

## Pet

### Attributes

Pet must be able to hold all of the needed pet care tasks, within a priority queue, enabling flexibility between animals.

Pet must have the name, and DOB for the animal, as well as Date inputted into system.

### pet Actions

Pet must be able to intake and remove tasks assigned to itself.

If a task has the same priority as another task, it should be placed below the current task in the priority queue.

The priority queue must be private. No resource outside of the current pet should be allowed to modify the priority queue assigned to the pet.

Pet must be able to return a copy of the queue.

Pet must be able to return the name, DOB, and input date of the animal.

Pet must be able to return the most important task.

Pet must be allowed to remove a task from the queue.

## Task

Task is representative of pet care tasks defined in this document.

### Task Attributes

Each pet care task must have the time it takes to complete the task (est), and the priority.

Priority must be from 0 to $n$, where 0 is highest prioirty and $n$ is lowest priority.

Priority must a discrete scale of whole numbers.

Each pet care task will be inputted by the user, along with the required fields.

### Task Actions

Task should use the Getter and Setter pattern.
Task must be able to return and modify the body text of the task.
Task must be able to return and modify the prioirity of the task.
Task must be able to return and modify the duration of the task.



## Scheduler

Scheduler must use Owner (and through Owner, all of their Pets) and Task to accurately make a plan.

Scheduler must apply Owner constraints — time windows and preferences — when generating a plan.

The generated plan must be represented as a string.

Scheduler **may optionally** use an LLM that is Open-AI api Compatible to interface with for explaining decisions. If no LLM is configured, rule-based explanation is fallback. As such, there should be some default rule explanations available per rule.

# Restrictions.

This application intends on only being a backend, as it will connect to the Streamlit UI.