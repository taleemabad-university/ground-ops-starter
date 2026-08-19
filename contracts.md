# Contracts

**Fill this in before you write any code. No contract, no build.**

This is the first thing we check on day 1, and it is SLO 1: *agree on exactly
what your piece takes in and hands out to the piece next to it, and don't change
it without telling anyone.*

It takes twenty minutes. Skipping it costs you the afternoon, because the first
time two pieces disagree about a field name you will not be able to tell whose
fault it is — which is SLO 2, and it is much harder when nothing was written
down.

---

## Who this is for

> One sentence. Who is on the other end of this system, and what goes wrong in
> their day if it stops working? Not "airports". One person, one job, one shift.

**Our user:**

---

## Who owns what

| Piece | Owner | Runs on | Health check |
|---|---|---|---|
| assigner A | | `:8101` | `curl localhost:8101/health` |
| assigner B | | `:8102` | |
| re-planner | | `:8103` | |
| monitor | | `:8104` | |

The board (`:8080`) and the feeds are given. Nobody owns them and nobody edits
them — that is what makes them safe to build against.

---

## The contracts

One row per pair of pieces that touch. Be specific enough that someone could
build the other side from this table alone.

| From → To | What passes | Exact shape | What happens when it's refused |
|---|---|---|---|
| assigner → board | a gate claim | `POST /claim {"flight","gate","actor"}` | 409 `{"ok":false,"reason":"gate_occupied","holder":"PK-304"}` — **and then we…** |
| re-planner → board | | | |
| monitor → board | | | |
| board → everyone | | | |

**The one everybody gets wrong:** the last column. A 409 is not an error to log
and move past — it means the board did not change and your piece is now wrong
about the world. Write down here what you actually do about it.

---

## What we are NOT building

> Scope, decided out loud, before you are tired. Two days, one component. SLO 9
> says stick to this when time runs short — so make it something you can stick to.

-
-
-

---

## In the first version / left for later

**First version (must work by end of day 1):**

-

**Left for later:**

-

---

## Changes to this file

Every change to a contract, once building has started, goes here with a name and
a time. This is SLO 11 — if you change a shape someone else is coding against
and don't say so, their piece breaks and they will spend an hour blaming
themselves.

| When | Who | What changed | Who it affects |
|---|---|---|---|
| | | | |
