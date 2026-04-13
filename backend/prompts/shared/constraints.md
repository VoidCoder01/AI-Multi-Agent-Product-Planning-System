---
name: shared_constraints
version: "1"
temperature: 0.0
max_tokens: 0
---

- Return ONLY structured output as specified in each agent's OUTPUT FORMAT section unless the user message is raw data for context.
- No markdown fences around JSON unless the OUTPUT FORMAT explicitly allows commentary.
- Prefer concrete, testable statements over vague aspirations; flag assumptions explicitly.
