---
name: self-healing-review
description: Audit one ground-ops service against the four healing patterns before the failures get injected. Use on your own piece on day 2 or 3 — checks retry-on-refusal, damping, blast radius and timeout-to-fallback, names which injected scenario each gap will fail, and reports without rewriting the code.
---

# Self-healing review

Audit one piece against the four patterns in [SELF-HEALING.md](../../../SELF-HEALING.md)
*before* day 3 makes the point for you. Each gap maps to a specific injected failure,
so this is a prediction of the scorecard, not a style review.

**Report, don't rewrite.** Name the gap, name the scenario it will fail, and let the
owner decide the fix — working the answer out is their outcome, and a fix you hand
them is one they cannot defend in the demo. Show a snippet only if asked.

## Which patterns apply

| Piece | Audit for |
|---|---|
| assigner A / B | 1 · retry on refusal |
| re-planner | 2 · damping, 3 · blast radius |
| monitor | 4 · timeout → fallback |
| any | the two cross-cutting rules at the bottom |

Only audit the piece you were pointed at. Reporting on all four makes the owner
responsible for other people's gaps.

## 1 · Retry on refusal — the assigners

Find every call to `board.claim()` / `board.slot()` / `board.release()`.

- Is the return value **read**? `claim()` hands back `(ok, reason)`. A bare
  `board.claim(f, g)` with no unpacking is the bug — that is the shipped naive bug.
- On `not ok`, does the piece record the flight as placed anyway? Look at whatever
  dict backs `/state`. Anything written before the board confirmed is a split waiting
  to happen.
- Is there a retry, and is it **next tick** rather than immediately? An immediate
  retry re-enters the same race it just lost.
- Does `/state` stay truthful in between?

**Gap fails:** `no double-book`, `no silent loss` — the `race` scenario.

## 2 · Damping — the re-planner

- Is there **any** rate limit between "something changed" and "re-plan it"? If the
  re-plan is triggered by board state and writes board state with no brake, that is
  an unbounded loop.
- Is the limit **per flight** (right) or global (leaky — one busy flight starves the
  rest)?
- Is the interval measured in **board-minutes** off `board.now()`, or wall-clock? A
  skewed clock is exactly what day 3 hands it.
- Is the number written in `contracts.md`? If not, nobody can tell a runaway from
  agreed behaviour.

**Gap fails:** `board converges` — the `bad-clock` / runaway scenario.

## 3 · Blast radius — the re-planner

- When one flight slips, how many flights does it touch? Look for a loop over *every*
  flight on the board — the shipped naive version re-issues a slot for all twelve.
- Can the selection rule be stated in one sentence? ("The flights behind it on the
  same gate, and the ones whose slot now overlaps.") If not, it is re-planning
  everything.
- Does it write when nothing changed? Every needless write is another race against
  the assigners.

**Gap fails:** `board converges`, and it makes the `race` worse for everyone.

## 4 · Timeout → fallback — the monitor

- Is a clock **started** per flight the moment it has nowhere to go? Counting
  unplaced flights is not a timer — that is the shipped naive bug.
- Does anything ever call `board.flag(flight, "held" | "divert", reason)`? If that
  call appears nowhere, the piece can only ever hang.
- Is the timeout in **board-minutes**? Board time runs one minute per six real
  seconds, so a wall-clock timeout never fires inside the harness window. **Check
  this first — it catches every cohort.**
- Is a `reason` passed? A decision with no reason cannot be told apart from luck
  afterwards.

**Gap fails:** `decision made` — the `no-gate` / dead-end scenario.

## Cross-cutting, every piece

- **Fails loudly and keeps running?** Look for a bare `except: pass`, or anything that
  can exit the main loop. A piece that dies has dropped out — `pieces alive`.
- **Reads time from `board.now()`**, never `datetime.now()` or `time.time()`.
- **No hardcoded host or port** — addresses come from `team.env` via
  `board/config.py`.
- **Answers `/health`, `/state`, `/log`**, and `/state` matches the board.
- **`/log` says what it decided and why**, not just that something happened.

## Report like this

Ordered by which scenario it fails, worst first:

```
self-healing review · replanner/naive.py

  GAP  damping           no rate limit between board change and re-plan
                         replanner/naive.py:41 re-plans on every tick
                         → will FAIL 'board converges' on ./inject bad-clock
                         → decide N, in board-minutes, and put it in contracts.md

  GAP  blast radius      re-issues a slot for every flight on the board
                         replanner/naive.py:47
                         → makes the race worse for both assigners

  OK   board clock       reads board.now() at :33
  GAP  board clock       ...except :52, which uses time.time()
```

Then stop. Do not apply the fixes unless asked.

## Rules

- **Never edit `board/`, `feeds/` or `harness/`.**
- Standard library only — never suggest a dependency.
- Cite file and line for every gap. An audit without a location is an opinion.
- If a pattern genuinely does not apply to the piece, say so rather than inventing a
  finding.
