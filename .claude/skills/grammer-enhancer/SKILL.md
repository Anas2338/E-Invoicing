---
name: "grammer-enhancer"
description: "Automatically improve the grammatical correctness, clarity, punctuation, and fluency of user text without altering meaning. Activates when the user provides text that appears to need grammar cleanup or explicitly asks for corrections, editing, or polishing."
---

The Grammar Enhancer skill rewrites user-provided text so it is grammatical, clear, and natural-sounding. It preserves tone and original intent while correcting:

- Grammar errors  
- Punctuation  
- Sentence structure  
- Run-ons and fragments  
- Awkward phrasing  
- Redundancy  
- Word choice (only when needed for clarity)

The skill avoids unnecessary creativity and does not introduce new information.

## Trigger Conditions
Activate automatically when the user:

- Provides text with grammar or clarity issues  
- Requests grammar correction or editing  
- Asks to “fix,” “clean up,” “polish,” “rewrite,” or “improve” text  
- Submits long-form writing intended for refinement

Do **not** activate when the user:

- Requests exact verbatim repetition  
- Requests style-preserving creative work without grammar correction  
- Asks for translation unless grammar cleanup is explicitly requested  
- Provides code (unless surrounding natural language needs correction)

## Behavior
When triggered, the skill:

1. Reads the provided text as a single unit.  
2. Produces a corrected and clarified version.  
3. Preserves meaning, tone, and style unless explicitly asked to modify them.  
4. Does not add new ideas or assumptions.  
5. Resolves ambiguous phrasing minimally and conservatively.  
6. Provides explanations only when asked.

## Examples

### Example 1 — Automatic Activation
**User:** “I send you the report yesterday but didnt got any reply yet.”  
**Output:** “I sent you the report yesterday, but I haven’t received a reply yet.”

### Example 2 — Explicit Request
**User:** “Please fix the grammar: The experiments was runned two times and results wasn’t consistent.”  
**Output:** “The experiments were run twice, and the results were not consistent.”

### Example 3 — Preservation of Tone
**User:** “hey can u clean this up a bit without making it too formal? i wanna send it to a friend: sorry for the late message i totally forgot lol”  
**Output:** “Hey, can you clean this up a bit without making it too formal? I want to send it to a friend: Sorry for the late message—I totally forgot, lol.”

### Example 4 — Declining Activation
**User:** “Repeat the following exactly: I has a apple.”  
**Output:** No activation; the user requested verbatim repetition.