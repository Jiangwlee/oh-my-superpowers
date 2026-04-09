# Debugging Guideline

Log-driven debugging methodology for sub agents. Read this when tests fail
or unexpected behavior is observed during task execution.

**Core principle: observe first, then act. Never guess.**

---

## Philosophy

**You are the investigator, not the guesser.** The error message tells you
what happened. The logs tell you where. The code tells you why. Follow the
evidence — don't hypothesize without data.

### Meta-Debugging: Your Own Code

When debugging code you just wrote, you're fighting your own mental model.

- **Treat your code as foreign** — read it as if someone else wrote it
- **Question your design decisions** — your implementation decisions are hypotheses, not facts
- **Admit your mental model might be wrong** — the code's behavior is truth; your model is a guess
- **Prioritize code you touched** — if you modified 100 lines and something breaks, those are prime suspects

The hardest admission: "I implemented this wrong."

### Cognitive Biases to Watch

| Bias | Trap | Antidote |
|------|------|----------|
| **Confirmation** | Only looking for evidence supporting your theory | "What would prove me wrong?" |
| **Anchoring** | First explanation becomes your anchor | Generate 3+ hypotheses before investigating |
| **Sunk Cost** | Spent an hour on one path, keep going | "If I started fresh, is this still the path?" |

## The 6-Step Method

### Step 1: List Possible Causes

**Before writing any code or making changes:**

List 3-7 possible causes with their diagnostic method. Be specific and falsifiable.

```
Possible causes:
1. Database query returns empty — check: add log before/after query
2. Auth token expired — check: log token expiry time
3. Response serialization strips field — check: log raw response before serialize
4. Cache returns stale data — check: log cache hit/miss
5. Middleware modifies request body — check: log request at each middleware
```

**Bad hypotheses (unfalsifiable):**
- "Something is wrong with the state"
- "The timing is off"

**Good hypotheses (falsifiable):**
- "User state resets because component remounts on route change"
- "API call completes after unmount, causing state update on unmounted component"

### Step 2: Add Diagnostic Logs

**Insert targeted logs at key points in the execution path.**

```python
# Strategic — logs at decision points
logger.debug(f"[auth] token check: user={user_id}, expires={token.exp}, now={time.time()}")
logger.debug(f"[auth] validation result: valid={is_valid}, reason={reason}")

# NOT strategic — logging everything
logger.debug(f"entering function")  # Useless without context
```

Rules:
- Log at decision points (before/after conditionals, at function boundaries)
- Include actual values, not just "entering function"
- Log to file, not stdout (avoid polluting test output)
- Tag logs with component name: `[auth]`, `[db]`, `[api]`

### Step 3: Run and Read Logs

Execute the failing operation and read the log output.

**Look for:**
- Last successful log before failure (narrows the location)
- Unexpected values (narrows the cause)
- Missing logs (code path not reached — the bug is earlier)

### Step 4: Narrow Scope, Then Read Code

Now that logs have narrowed the problem to a specific file/function:

1. Read the code in that area COMPLETELY (not just "relevant" lines)
2. Read imports, configuration, related tests
3. Trace the actual data flow through the code
4. Identify the root cause — not just "what fails" but "WHY it fails"

### Step 5: Fix and Verify

1. Make the SMALLEST change that addresses the root cause
2. Run the original failing test — it should pass now
3. Run related tests — no regressions
4. If fix doesn't work, go back to Step 1 with new information

### Step 6: Clean Up

**Remove ALL diagnostic logs you added.** Every single one.

- Remove temporary logging statements
- Remove debug print statements
- Revert any temporary configuration changes
- The codebase should look like you were never debugging

---

## Investigation Techniques

### Binary Search

**When:** Large codebase, many possible failure points.

Cut the problem space in half repeatedly:
1. Add log at midpoint of execution path
2. Is data correct at midpoint? YES → bug is after. NO → bug is before
3. Repeat until isolated

**Example:** API returns wrong data
- Data leaves database correctly? YES
- Data reaches frontend correctly? NO
- Data leaves API route correctly? YES
- Data survives serialization? NO → Bug in serialization

### Working Backwards

**When:** You know the correct output but aren't getting it.

1. What function produces the output?
2. Test that function with expected input — correct output?
   - YES → bug is earlier (wrong input)
   - NO → bug is here
3. Repeat backwards through call stack

### Differential Debugging

**When:** Something used to work and now doesn't.

- What changed in code? (`git diff`, `git log`)
- What changed in environment? (versions, config)
- What changed in data?
- Test each difference in isolation

### Minimal Reproduction

**When:** Complex system, unclear which part fails.

1. Copy failing code to isolated context
2. Remove one piece at a time
3. Still fails? Keep removing. Stops failing? Put that piece back
4. Repeat until bare minimum that reproduces the bug

---

## Chrome DevTools Rules

**Only for frontend/browser issues.** Use in this order:

1. **Observe** — take screenshot, check console, inspect network
2. **Log** — add diagnostic logs in the relevant components
3. **Narrow** — use logs to find the specific component/function
4. **Fix** — apply the fix
5. **Verify** — take screenshot again, confirm visual fix

**Do NOT** use DevTools to trial-and-error CSS changes. That's YOLO fixing.

---

## Prohibited Behaviors

- **YOLO fixing**: changing code based on guesses without diagnostic evidence
- **Shotgun debugging**: changing multiple things at once hoping one works
- **Trial-and-error loops**: repeatedly tweaking values without understanding why
- **Leaving debug artifacts**: forgetting to remove diagnostic logs after fixing
- **Skipping reproduction**: fixing without first confirming you can trigger the bug
- **Fixing unrelated issues**: scope creep during debugging (note them, don't fix them)

---

## Decision Tree

```
Test fails or unexpected behavior observed
│
├─ Can you reproduce it?
│  ├─ NO → Make it reproducible first (check environment, data, timing)
│  └─ YES ↓
│
├─ Step 1: List 3-7 possible causes
├─ Step 2: Add diagnostic logs at key points
├─ Step 3: Run and read logs
│  ├─ Logs show the problem clearly → Step 4: Read code at that location
│  └─ Logs insufficient → Add more logs at narrower scope, repeat Step 3
│
├─ Step 4: Read code, identify root cause
│  ├─ Root cause found → Step 5: Fix and verify
│  └─ Still unclear → Go back to Step 1 with new information
│
├─ Step 5: Fix (smallest change) and verify
│  ├─ Tests pass → Step 6: Clean up diagnostic logs
│  └─ Tests still fail → Back to Step 1 (attempt += 1)
│
└─ 3 attempts exhausted → Escalate to orchestrator
```
