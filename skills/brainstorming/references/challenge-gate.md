# Challenge Gate

Run this step before proposing any solution. Its purpose is to surface the strongest objection to the user's premise, not to be contrarian, but to catch wrong-direction decisions before implementation begins.

## Normal mode checks

1. **Root cause test** — Is the user solving the actual problem, or patching a symptom? State clearly if the proposal treats the wrong layer, for example: "this is a workaround for a prompt constraint issue, not a real architectural need."

2. **Project standards test** — Apply the project's own evaluation criteria to the proposal. For agents, use Role × Agency × Ownership. For skills, check CLI-ability and autonomy rules. Cite the specific standard and explain why the proposal may fail it.

3. **Fragile assumptions test** — List the 2-3 assumptions the idea depends on that are most likely to be wrong. Make each assumption explicit and falsifiable.

## Rules

- Present the challenge in its own message before moving to mode judgment.
- Do NOT walk back the challenge when the user defends their idea. Either accept the defense if it addresses the challenge substantively, or maintain the challenge and note it as unresolved: *"挑战未解决，但你选择继续。"*
- Generic objections ("this might not work") are forbidden. Every challenge must cite a specific reason, principle, or project constraint.

## Fast mode

Run the root cause test only (1-2 points). Skip the project standards and fragile assumptions tests.
