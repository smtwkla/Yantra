# Roadmaps — big features cut into steps

A **roadmap** turns one big feature (a module of `docs/Plan.MD`, e.g. preventive maintenance) into
an ordered list of items, each the seed of one step. The **roadmapper** (`.claude/agents/roadmapper.md`,
Opus) writes it; KLA, the product owner, approves it at **gate R**; each item becomes a step only
when KLA takes it up (25-10-2026, by KLA).

## Numbers

- A roadmap is `R01`, `R02`, …, in `docs/roadmap/R0N-<slug>.md`.
- Its items are `R0N.1`, `R0N.2`, …, never reused; a dropped item stays, marked `dropped`.
- **A roadmap item has no step number.** When KLA takes one up (`/step plan R0N.n`), the
  orchestrator gives it the next free `S0NN`, records "→ S0NN, DD-MM-YYYY" on the item, and writes
  `From: R0N.n` in the step brief's header. The roadmapper never allocates step numbers.

## Gates

- **Gate R**: KLA approves the roadmap — its items, their order and his answers to its decisions.
  The orchestrator records the answers in the roadmap and the lasting decisions in `Plan.MD`.
- Each step then runs its usual gates (A and B, `docs/steps/README.md`).
- **Re-planning** (`/step roadmap R0N`): the roadmapper revises the roadmap in place with a dated
  `## Log` entry; a changed order or a new decision comes back to gate R.

## Index

| Roadmap | Feature | Items (open / taken up / done) | Status | Date |
|---|---|---|---|---|
