# OpenClaw Trading Agent Runtime Templates

This folder contains runnable configuration templates for the A-share trend trading agent workflow.

## Files
1. `agent.runtime.yaml`: top-level runtime settings, skills, paths, and guardrails.
2. `schedules.yaml`: daily cron-style workflow schedule.
3. `event-routing.yaml`: event-to-skill pipeline and retry policy.
4. `env.example`: required environment variables.

## Required Skills
1. `.agents/skills/a-share-trend-scanner`
2. `.agents/skills/a-share-trade-plan-compiler`
3. `.agents/skills/a-share-trade-event-executor`
4. `.agents/skills/a-share-trade-risk-gate`
5. `.agents/skills/a-share-trade-broker-jvquant`
6. `.agents/skills/a-share-trade-reflection-evolver`
7. `.agents/skills/a-share-trade-orchestrator`

## Required Contracts
1. `docs/contracts/trade_plan.schema.json`
2. `docs/contracts/order_intent.schema.json`
3. `docs/contracts/risk_decision.schema.json`
4. `docs/contracts/execution_report.schema.json`
5. `docs/contracts/event_log.schema.json`

## Runtime Rules
1. All broker execution must pass risk gate.
2. Daily fill count limit is 10.
3. Max concurrent symbols is 5.
4. Repost open per symbol per day is capped at 5.
5. Add action only at next +2% level from most recent buy.
6. Stop loss uses 80% of most recent buy.
7. Single order target amount is <= 5000 CNY, with one-lot exception if previous close * 100 > 5000.
