// Regression tests for the pi-event -> SSE mapper.
//
// The behavior these lock down once broke during the TS migration: a generated
// UI rendered but its buttons were dead because the definitive run=true paint
// (the `gen_ui` event, which makes the frontend run scripts and attach
// listeners) was never emitted. Root cause: pi carries the full render_ui html
// on tool_execution_START, NOT on END — so emitting the final gen_ui only from
// tool_execution_end (whose args.html is absent) produced nothing.
//
// Run: node --test --experimental-strip-types server/pi/events.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { createPiLineMapper, type SseEvent } from "./events.ts";

function run(lines: unknown[]): SseEvent[] {
  const mapper = createPiLineMapper();
  const out: SseEvent[] = [];
  for (const line of lines) {
    const { events } = mapper.mapPiLine(JSON.stringify(line));
    out.push(...events);
  }
  return out;
}

const FULL_HTML =
  '<!doctype html><html><body><button id="b">+1</button>' +
  '<script>document.getElementById("b").addEventListener("click",function(){});</script></body></html>';

// The exact regression: materialized-arguments streaming. The html arrives via
// toolcall_delta (partial.content[i].arguments.html) and on tool_execution_start
// args.html, but tool_execution_end carries NO html.
test("materialized-args stream emits exactly one final gen_ui with the full html", () => {
  const events = run([
    {
      type: "message_update",
      assistantMessageEvent: {
        type: "toolcall_delta",
        toolCallId: "tc1",
        partial: { content: [{ type: "toolCall", arguments: { html: "<!doctype html><html><body><butt" } }] },
      },
    },
    {
      type: "message_update",
      assistantMessageEvent: {
        type: "toolcall_delta",
        toolCallId: "tc1",
        partial: { content: [{ type: "toolCall", arguments: { html: FULL_HTML } }] },
      },
    },
    { type: "tool_execution_start", toolName: "render_ui", toolCallId: "tc1", args: { html: FULL_HTML, title: "Demo" } },
    // tool_execution_end has NO html — this is what broke it.
    { type: "tool_execution_end", toolName: "render_ui", toolCallId: "tc1", args: {} },
    { type: "agent_end" },
  ]);

  const genUi = events.filter((e) => e.type === "gen_ui");
  // Exactly one: not zero (the regression), not two (the double-render a prior
  // review pass worried about — scripts must not run twice).
  assert.equal(genUi.length, 1, "exactly one final gen_ui (run=true paint) must be emitted");
  const final = genUi[0] as Extract<SseEvent, { type: "gen_ui" }>;
  assert.ok(final.html.length > 0, "final gen_ui html must be non-empty so scripts run and listeners attach");
  assert.equal(final.html, FULL_HTML);
  assert.equal(final.title, "Demo");
  // Partial deltas should have streamed for the live-paint experience.
  assert.ok(events.some((e) => e.type === "gen_ui_delta"), "partial gen_ui_delta frames should stream");
});

// Fast path: no toolcall_delta at all; html materializes only on start.
test("html only on tool_execution_start (no delta) still emits the final gen_ui", () => {
  const events = run([
    { type: "tool_execution_start", toolName: "render_ui", toolCallId: "tc1", args: { html: FULL_HTML, title: "T" } },
    { type: "tool_execution_end", toolName: "render_ui", toolCallId: "tc1", args: {} },
    { type: "agent_end" },
  ]);
  const genUi = events.filter((e) => e.type === "gen_ui");
  assert.equal(genUi.length, 1);
  assert.equal((genUi[0] as Extract<SseEvent, { type: "gen_ui" }>).html, FULL_HTML);
});

// Per-turn isolation: a new stream must not leak the previous turn's html.
test("a fresh mapper does not leak html across turns", () => {
  // First turn renders something.
  run([
    { type: "tool_execution_start", toolName: "render_ui", toolCallId: "a", args: { html: FULL_HTML, title: "A" } },
    { type: "tool_execution_end", toolName: "render_ui", toolCallId: "a", args: {} },
    { type: "agent_end" },
  ]);
  // A brand-new mapper (new stream) with a render_ui that never carried html
  // anywhere must NOT emit a stale gen_ui.
  const events = run([
    { type: "tool_execution_start", toolName: "render_ui", toolCallId: "b", args: {} },
    { type: "tool_execution_end", toolName: "render_ui", toolCallId: "b", args: {} },
    { type: "agent_end" },
  ]);
  assert.equal(events.filter((e) => e.type === "gen_ui").length, 0);
});

// Text + done plumbing stays intact.
test("text deltas map to assistant_delta and agent_end maps to done", () => {
  const events = run([
    { type: "message_update", assistantMessageEvent: { type: "text_delta", delta: "hi" } },
    { type: "agent_end" },
  ]);
  assert.deepEqual(
    events.find((e) => e.type === "assistant_delta"),
    { type: "assistant_delta", delta: "hi" },
  );
  assert.ok(events.some((e) => e.type === "done"));
});
