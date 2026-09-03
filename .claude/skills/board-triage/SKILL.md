---
name: board-triage
description: Work out which piece of the ground-ops system broke, and whose it is, from the board's own evidence. Use when the board misbehaves and it is not obvious who caused it — reads /log, /decisions, /board and each piece's /state and /log, then names the owner and hands over. Never reads a teammate's source. The board keeper's core loop.
---

# Board triage — whose piece is it?

The board keeps every decision it has ever made, indexed by flight and by actor. That
is enough to name the culprit without opening anyone's code — which matters, because
reading a teammate's source to diagnose them is both slow and the wrong dynamic.

**Diagnose from evidence everyone can see.** Then it is a finding, not an opinion.

**The board is always right.** If a piece's `/state` disagrees with `/board`, the
piece is wrong. That is the definition, not a judgement call.

## The loop

### 1 · Get the symptom in one sentence

Run the scorecard and read what it says:

```bash
./inject verdict
```

Each failing check already names the piece and the flight:

```
FAIL  no double-book   assigner-B thinks PA-450 is on G4, board says TK-709
FAIL  board converges  board still taking 31 writes/sec (was 0.8/s before) — spinning
FAIL  decision made    AI-201 still 'waiting' with nowhere to go — it just hung
```

If nothing is failing but something feels wrong, go to step 2 anyway — the checks
sample a window and can miss a transient.

### 2 · Follow the flight, in order

One flight's whole life, oldest first. This is the highest-value command in the repo:

```bash
curl -s "localhost:8080/decisions?flight=PK-304" | python3 -m json.tool
```

Read it as a story. Who claimed it, who was refused, who released it, who flagged it,
and in what order. The moment the story stops making sense is the moment to look at.

Then the board's recent history across all flights:

```bash
curl -s localhost:8080/log
```

### 3 · Ask each piece what it believes

```bash
curl -s localhost:8101/state     # assigner A
curl -s localhost:8101/log       # and why it did that
```

Compare against `curl -s localhost:8080/board`. You are looking for a **split**: the
piece holding a flight the board says belongs to somebody else, or nobody.

A piece that does not answer at all is also a result — it died instead of degrading,
and that is the `pieces alive` check.

### 4 · Who loses races, in aggregate

When it is intermittent, count instead of guessing:

```bash
sqlite3 board.db "SELECT actor, COUNT(*) FROM decisions
                  WHERE event='claim_rejected' GROUP BY actor ORDER BY 2 DESC"
```

An actor with many rejections is not necessarily broken — losing a race is legal. An
actor with many rejections **whose `/state` still lists those flights as placed** is
broken, and that is the race bug.

## Symptom → owner

| What you see | Whose it is | What to tell them |
|---|---|---|
| A piece's `/state` lists a flight the board gives to someone else | That piece | "You recorded a claim the board refused. Read what `claim()` returns." |
| Board write rate takes off and stays up | Re-planner | "No damping — every re-plan is triggering the next one. What's your N?" |
| Many gates churning after one flight slipped | Re-planner | "Blast radius. One flight moved; you re-planned twelve." |
| A flight sits `waiting` forever, never held or diverted | Monitor | "No timer, or a timeout in wall-clock seconds that never fires." |
| A flight was placed, came off the board, no decision recorded | Whoever released it — check `/decisions` | "This flight is lost. Your release has no follow-up." |
| A piece stops answering `/health` | That piece | "You exited instead of degrading. Catch, log, continue." |

## How to hand it over

Name the evidence, not the person's code. Early and plainly — this is scored (SLO 11),
and it is the difference between a ten-minute fix and losing an afternoon.

> "AI-201 has been `waiting` since board-minute 34 with no gate and no decision —
> `/decisions?flight=AI-201` shows nothing after the arrival. Monitor's timer looks
> like it isn't firing. Can you check the timeout is in board-minutes?"

Not: *"your monitor is broken"*. Not: *"I read your code and you forgot the timer."*

## Rules

- **Never edit `board/`, `feeds/` or `harness/`.** You are reading them, not changing
  them.
- **Do not fix a teammate's piece for them.** Find it, name it, hand it over. Their
  fix is their outcome.
- **Never hardcode a host or port** in anything you write — addresses come from
  `team.env` via `board/config.py`. On day 2+ the board is not on your laptop.
- After a fix lands, re-run the scenario and check `./inject history` — the score
  should actually move. If it didn't, the diagnosis was wrong.
