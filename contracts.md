# Contracts

**Fill this in on day 1, before you write any code. No contract, no build.**

## What a contract is

> A contract is the promise your service makes to the one next to it: exactly what
> you take in, exactly what you hand back, and what you do when the board says no.
> Written down before any code — so that when two pieces disagree at 4pm, you can
> tell whose fault it is in a minute instead of an hour.

That is SLO 1, and it is the first thing we check. It takes twenty minutes.
Skipping it costs you a day, because the first time two pieces disagree about a
field name you will not be able to tell whose fault it is — which is SLO 2, and it
is much harder when nothing was written down.

## Who fills in what

Nobody fills this in alone, and no row belongs to "the team" — every row has a
name against it. The board keeper chairs the session and owns the file.

| Section | Who writes it | What specifically |
|---|---|---|
| Who this is for | Everyone, board keeper chairs | One sentence. One person, one job, one shift — not "airports". |
| Who owns what | Board keeper | Names, ports, health-check URLs, and the deployed board address |
| `assigner → board` | Assigner A + B **together** | `POST /claim {flight,gate,actor}` — and what they do on a 409 |
| `re-planner → board` | Re-planner | Which writes it makes, its **blast-radius rule** and its **damping rule** |
| `monitor → board` | Monitor | `POST /flag {flight,decision,reason}` — the exact allowed decision values, and its **timeout in board-minutes** |
| `board → everyone` | Board keeper | The 200 / 409 shapes every writer has to handle |
| What we are NOT building | Everyone | Three lines, decided out loud before you are tired |
| MVP / roadmap | Everyone; board keeper holds the line | The v1 that must work by end of day 2 |
| Changes to this file | Board keeper owns it | Every contract change once building has started — SLO 11 |

**You do not leave day 1 until every row has something in it**, and until the
refusal column is answered for all three writers.

---

## Who this is for

> One sentence. Who is on the other end of this system, and what goes wrong in
> their day if it stops working? Not "airports". One person, one job, one shift.

**Our user:**

---

## Who owns what

| Piece | Owner | Runs on | Health check |
|---|---|---|---|
| **board keeper** | | the deployed board | `curl <BOARD_URL>/health` |
| assigner A | | `:8101` | `curl localhost:8101/health` |
| assigner B | | `:8102` | |
| re-planner | | `:8103` | |
| monitor | | `:8104` | |

The board (`:8080`), the feeds and the harness are **given**. Nobody edits them —
that is what makes them safe to build against, and it is why we can break your
system on day 3 without touching your code.

The **board keeper** owns *running* the board, not its source: the deploy, the
addresses in `team.env`, this file, and the answer to "is the board healthy".

---

## The contracts

One row per pair of pieces that touch. Be specific enough that someone could build
the other side from this table alone.

**The first row is filled in as the worked example.** That level of detail — the
exact shape, and a real answer in the last column — is the standard for every other
row.

| From → To | What passes | Exact shape | What happens when it's refused |
|---|---|---|---|
| assigner → board | a gate claim | `POST /claim {"flight","gate","actor"}` | 409 `{"ok":false,"reason":"gate_occupied","holder":"PK-304"}` — we leave the flight unassigned and retry it next tick. We do **not** record it as placed. |
| re-planner → board | | | |
| monitor → board | | | |
| board → everyone | | | |

**The one everybody gets wrong:** the last column. A 409 is not an error to log and
move past — it means the board did not change and your piece is now wrong about the
world. Write down here what you actually do about it.

### Two things that are contracts, not implementation details

Write these down here, in this file, with a number in them:

- **The re-planner's damping rule** — "at most one re-plan per flight per N
  board-minutes". This sets how hard the board gets written to, and *the board
  settling is one of the five things we score*. If the number is not written down,
  nobody can tell on day 3 whether a runaway is a bug or the behaviour you agreed on.
- **The monitor's timeout, in board-minutes.** The board's clock runs one minute per
  six real seconds. A timeout written in wall-clock seconds silently never fires
  inside the window we test in. Say it in board-minutes.

---

## What we are NOT building

> Scope, decided out loud, before you are tired. Three days, one service. SLO 9 is
> MVP and roadmap — hold this line when time runs short, so make it a line you can
> actually hold.

-
-
-

---

## MVP / roadmap

**v1 — must work by end of day 2:**

-

**Roadmap — everything after that:**

-

---

## Changes to this file

Every change to a contract, once building has started, goes here with a name and a
time. **The board keeper owns this table.** This is SLO 11 — if you change a shape
someone else is coding against and don't say so, their piece breaks and they will
spend an hour blaming themselves.

| When | Who | What changed | Who it affects |
|---|---|---|---|
| | | | |
