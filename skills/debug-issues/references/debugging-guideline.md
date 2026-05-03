# Debugging Guideline

Evidence-driven debugging methodology for failing tests, runtime errors, and
unexpected behavior.

**Core principle: observe first, then act. Never guess.**

## Philosophy

You are the investigator, not the guesser.

- The error message tells you what happened.
- The logs tell you where.
- The code tells you why.

Follow the evidence. Do not change code just because a theory sounds plausible.

### Meta-Debugging: Your Own Code

When debugging code you recently wrote, your mental model is a risk factor.

- Treat your code as foreign code.
- Assume your implementation choices may be wrong.
- Prioritize the code you touched most recently.
- Ask: "What evidence would prove my current theory wrong?"

### Biases To Watch

- **Confirmation bias**: only noticing facts that support your first theory
- **Anchoring**: refusing to leave the first explanation
- **Sunk cost**: continuing an unproductive path because you already spent time on it

## The 6-Step Method

### Step 1: List Possible Causes

Before changing code, write 3-7 specific and falsifiable causes.

Good:

1. Cache returns stale data after invalidation failure.
2. Component remount resets local state on route change.
3. Serializer drops the field before the API response is returned.

Bad:

- "Something is wrong with state"
- "Timing seems off"

### Step 2: Choose Your Observation Method

Three ways to gather evidence. Pick by **environment** + **suspect range**.

| Method | Use when | Avoid when |
|---|---|---|
| **chrome-devtools** | Browser: console, network, DOM / CSS, SPA, performance, runtime values | Non-browser scenarios |
| **curl direct probe** | Verify upstream HTTP service; isolate frontend / proxy / SDK layers | Pure compute; stateful pipelines |
| **Add logs** | Backend / CLI / long pipeline; async, concurrent, cross-process; rerunnable but not steppable | Browser UI; range already tiny; throwaway script |
| **Read code** | Range already narrow (1-2 files, gate-locked); pure logic; config / type / typo; small recent change | Runtime-value dependent; concurrency; spread across many modules |

Decision order:

```text
browser?               -> chrome-devtools
upstream HTTP suspect? -> curl direct probe (mind proxy env)
narrow + pure logic?   -> read code
otherwise              -> add diagnostic logs
```

#### Reading Code

When the suspect range is small enough to read end-to-end:

- Read the file or function completely, not just the line that crashes.
- Read related tests, imports, and configuration.
- Trace the real data flow and check actual call sites.
- Check recent diffs (`git log -p <file>`) before assuming the code is correct.

#### Adding Logs

Log at decision points and data boundaries.

Good:

```python
logger.debug(
    "[auth] validation result user=%s valid=%s reason=%s",
    user_id,
    is_valid,
    reason,
)
```

Bad:

```python
logger.debug("entering function")
```

Rules:

- Log actual values.
- Log before and after important branches.
- Tag logs with a component marker such as `[auth]` or `[db]`.
- Prefer logs that can be removed cleanly after the fix.

#### Using chrome-devtools

For anything happening inside a browser page, prefer the chrome-devtools MCP
over guessing or reloading blindly:

- `list_console_messages` — JS errors, warnings, your own logs.
- `list_network_requests` / `get_network_request` — failed XHR / fetch, status, payloads.
- `evaluate_script` — read runtime values, call functions, inspect state stores.
- `take_snapshot` — DOM tree with selectors for the next action.
- `take_screenshot` — visual confirmation.
- `performance_start_trace` / `performance_stop_trace` — slowness and jank.

#### Using curl direct probe

When the suspect is the boundary between the app and an upstream HTTP service,
hit the upstream directly with `curl` to isolate which layer breaks:

- Run the same request the app sends; compare status, headers, body, latency.
- Strip auth / proxy / SDK abstractions one at a time to find the failing layer.
- For local / LAN endpoints, confirm proxy env is bypassed:
  `curl --noproxy '*' ...` or `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY curl ...`.
- For streaming endpoints, add `--no-buffer` and watch chunks arrive in real time.
- For TLS / certificate issues, add `-v` and inspect the handshake.

### Step 3: Run And Read Logs

Execute the failing path and inspect the output.

Look for:

- the last successful log before failure
- unexpected values
- missing logs that prove a branch never ran

### Step 4: Narrow Scope, Then Read Code

<HARD-GATE>
Do NOT read code until the suspect range is narrowed to 1-2 files or a single
function. Wide-scope code reading is the most common failure mode in
LLM-driven debugging.
</HARD-GATE>

Once the evidence points to a specific area:

1. Read that file or function completely.
2. Read related tests, imports, and configuration.
3. Trace the real data flow.
4. Identify the root cause, not just the line that crashes.

If the range is still wide, return to Step 2 and pick a different observation
method. Do not "read everything to get a feel" — that is shotgun reading.

### Step 5: Fix And Verify

1. Apply the smallest change that matches the root cause.
2. Rerun the original failing test or reproduction.
3. Run related checks to catch regressions.
4. If the evidence no longer matches your theory, go back to Step 1.

### Step 6: Clean Up

Remove every temporary debugging artifact.

- Remove diagnostic logs you added for the investigation.
- Remove debug prints and temporary config changes.
- Leave the codebase as if the debugging session never happened.

## Investigation Techniques

### Binary Search

Use when the failure could be in many places.

1. Pick a midpoint of the execution path and observe the data there
   (log, `evaluate_script`, breakpoint, or direct read — whichever your
   chosen method allows).
2. If the data is correct there, the bug is later.
3. If the data is wrong there, the bug is earlier.
4. Repeat until the suspect area is small.

### Working Backwards

Use when you know the correct output.

1. Start from the function that produces the wrong output.
2. Check whether it behaves correctly for the expected input.
3. If yes, move earlier.
4. If no, the bug is here.

### Differential Debugging

Use when something used to work.

- Check what changed in code.
- Check what changed in environment.
- Check what changed in data.
- Test one difference at a time.

### Minimal Reproduction

Use when the full system is too noisy.

1. Isolate the failing behavior.
2. Remove unrelated pieces.
3. Keep shrinking until the failure becomes obvious.

## Frontend Rule

For frontend issues, observe with chrome-devtools before editing.

1. `list_console_messages` and `list_network_requests` — find what failed and where.
2. `take_snapshot` / `take_screenshot` — confirm visible state and get selectors.
3. `evaluate_script` — read the actual runtime value at the suspect point.
4. Narrow to the exact decision point.
5. Fix.
6. Verify the visual or behavioral result.

Do not trial-and-error CSS or UI values without evidence. Do not fall back to
adding `console.log` when chrome-devtools can read the value directly.

## Prohibited Behaviors

- YOLO fixing
- Shotgun debugging
- Trial-and-error loops without diagnosis
- Leaving debug artifacts behind
- Fixing unrelated issues during a debug pass
- Claiming success without rerunning the failing path

## Decision Tree

```text
Failure reproduced
    -> list possible causes
    -> add targeted diagnostics
    -> run and read evidence
    -> narrow scope
    -> fix the root cause
    -> verify
    -> clean up

Cannot reproduce
    -> make the failure reproducible first
```
