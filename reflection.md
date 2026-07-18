# PawPal+ Project Reflection

## 1. System Design

As of before step two, there was no real useage of AI outside of assisting in guiding my `core_actions.md` file, and ensuring that the text was simple, accurate, and actually captured the meaning of what I wanted to make. A simple back and forth to reduce ambiguity.

**a. Initial design**

- Briefly describe your initial UML design.
  - Initial UML design was okay. I chose classes by the responsibilities they should have.

Where owner should be in charge of pet, and each pet should have tasks.

Each task should be owned by a pet, since each pet may have a different set of tasks.

The scheduler should take the Owner, and tasks and see what the Owner is available to do, and generate a plan accordingly.

- What classes did you include, and what responsibilities did you assign to each?

I chose four classes: Owner, Pet, Scheduler, Task, but added one for a time slot for the owner.

Owner, has pets, Owner has timeslots.
pet has tasks, but is scheduled by the Scheduler
Tasks track priority, text description and duration.
Timeslots describe owner availablity. 

Scheduler uses a basic algorithm to measure availablity for tasks, and then sends possible planning/ description to an LLM to explain the reasoning. (Open-AI Api compatible.) If not, it has basic text to have "some" description for the choices made.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes I wanted to better have my design focus on the animal, it needed the species too. It was lacking what I would argue is critical information.

I also forced the removal of hardcoded values that would make life harder for everyone involved.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

My scheduler considers prioirity within the availability windows.

Preferences are ultimately lastly considered, as the animal is more important than personal preferences

- How did you decide which constraints mattered most?

I considered animal welfare over owner preferences. Animal welfare matters most, and personal preferences are secondary to all of the above.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

Its greedy, and never backtracks. Its also simplistic.

- Why is that tradeoff reasonable for this scenario?

Simplicity > complexity. As tasks get more difficult, and different needs to be met, then I should change it.

Currently, it checks tasks, then open windows, and greedily fills it up. Works in this case, due again to its simplicity.

With that being said as well, there is a slight nit about readability in the current system with the printing, but its fine to keep as is.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
  
Given that the AI focus is really hard here, I used it for brainstorming and idea outreach/verification. Then I also used it as a second set of eyes to quickly refactor and be able to debug parts of code.

However, I still needed to be able to judge where the AI was stating those things, and verifying that indeed that is what I wanted, as well as that it did what it stated.

- What kinds of prompts or questions were most helpful?

I found that having a accountt level system prompt for the AI to respond in a professional, helpful manner, where there is no praise, but a listing of what occured, enables me to get a better idea of what is going on without it trying to praise me.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

The AI wanted to install all sorts of packages to make life easier. But I also am not going to install random packages.
Next, I also forced it to document the test as well as provide reasoning to me. Sometimes the logic was inconsistent and iffy at best. As such I did not accept some of the suggested terminal runs, file changes, and documentations.

- How did you evaluate or verify what the AI suggested?
I evaluates what the AI suggested by doing two things. One starting a fresh session and telling it to evaluate the file. Two by looking over the file myself. I found that I can more often at least, find issues with the code that the AI seemed to gloss over. As such, I had it recheck the file, list changes, then I checked the diff to ensure that all was as said, and all was as needed to be changed.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
