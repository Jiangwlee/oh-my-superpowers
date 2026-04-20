# Scenario S1: Open Discussion

> You have completed the common skeleton (Explore → Clarifying → Challenge Gate → Propose approaches). This file is the S1 SOP.

S1 is the **fallback** scenario: the user wants to think out loud, explore a question, or align understanding — with no immediate implementation intent.

## When S1 applies

- Non-routable by S2 / S3 (no "design skill/agent" and no "develop/fix/refactor X" trigger)
- Or the user explicitly asks to just talk / think / explore
- Or S2/S3 gate fails and falls back

If the user's intent turns actionable mid-discussion, **re-run scenario routing** (re-enter the common skeleton from step 0); do not silently convert to S2/S3.

## SOP

1. Continue the dialogue until the user is satisfied (they say so, or they switch topic).
2. **No mandatory artifacts**: no design doc, no spec review loop.
3. **Optional lightweight discussion note** — only if the user explicitly asks to preserve the conclusion, or the conversation reaches a reusable insight worth capturing:
   - Path: `docs/brainstorming/discussions/YYYY-MM-DD-<topic>.md`
   - Format: free-form markdown; include date, participants (if meaningful), the question, the conclusion. Not a design doc.
   - **NOT** `docs/brainstorming/specs/` — specs/ is reserved for S3 implementation designs.

## Gotchas

- **Do not upgrade S1 silently into S3**. If the user says "let's actually build this", acknowledge, return to scenario routing, and proceed through S3's skeleton afresh.
- **Do not produce a design doc by default**. S1's product is conversation clarity, not a file.
- **Challenge Gate still applies** when the user asks for recommendations — the point of S1 isn't to bypass rigor, it's to bypass **mandatory artifacts**.
