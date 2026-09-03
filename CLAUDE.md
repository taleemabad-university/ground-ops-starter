# CLAUDE.md

Context for Claude Code working in this repo.

**The top half is given and correct — leave it alone.** The bottom half is
marked `YOURS` and is empty on purpose: filling it in is part of the build, and
it is worth more than it looks. See the note at the end.

---

## What this is

An airport ground-ops controller. Flights need a **gate** to park at and a
**runway slot** to use. Four services decide which flight gets which, and the
whole thing has to keep working when one flight runs late and everything behind
it has to be re-planned — with nobody watching.

Python 3.10+, **stdlib only. Never add a dependency.** No pip install, no
requirements.txt. If something seems to need a library, it doesn't.

---

## Do not edit

`board/` · `feeds/` · `harness/`

These are given, finished, and correct. They are also **the surface failures are
injected through on day 3** — the board and the feeds are the only things the
four services can see, so changing what comes through them tests the build
without anyone touching its code. Editing them doesn't make the tests pass; it
makes the result meaningless.

If a change seems to require editing the board, the change is wrong.

**The board keeper is a person, not a piece of code.** The board is given and
nobody edits it — including them. What they own is *running* it: the deploy,
`team.env`, `contracts.md`, and the answer to "is the board healthy". They
diagnose from `/log`, `/decisions` and `./inject verdict` — the evidence the board
already keeps — never by reading a teammate's source.

---

## The board contract

Everything talks to the board over HTTP. `board/client.py` wraps it.

```
GET  /board                    gates, slots, flights, clock, write counter
GET  /now                      the BOARD's clock — read time from here, never datetime.now()
GET  /unassigned               flights with no gate yet
GET  /log?n=50                 recent decisions, newest last

POST /claim   {flight, gate}   -> 200 {"ok":true} | 409 {"ok":false,"reason":"gate_occupied","holder":...}
POST /slot    {flight, slot}   same shape
POST /release {gate}
POST /flag    {flight, decision, reason}   decision = "held" | "divert"
```

**The one rule that matters: a 409 is not a log line, it is a fact.** It means
somebody claimed it first and *the board did not change*. Code that ignores the
return value leaves its own state disagreeing with the board, and the flight it
thinks it placed is nowhere, with nothing looking for it. Always:

```python
ok, reason = board.claim(flight, gate)
if not ok:
    ...   # you lost. leave it unassigned and try again — do NOT record it as placed.
```

Two rules the board enforces so you don't have to: one gate holds one flight,
one slot holds one flight. Ever.

---

## Data

The board keeps everything in **SQLite** (`board.db`, stdlib `sqlite3`, no
install). Two consequences worth knowing:

- **State survives a restart.** `./run` restores every flight from disk. If you
  genuinely want an empty board, `./run fresh`.
- **Every decision is kept forever**, not just the last 400 in memory. This is
  the day-3 debugging tool — it answers "what happened to this flight, in order,
  and who did it" without opening anyone's source.

```bash
curl -s "localhost:8080/decisions?flight=PK-304" | python3 -m json.tool
sqlite3 board.db "SELECT actor, COUNT(*) FROM decisions
                  WHERE event='claim_rejected' GROUP BY actor"
```

Your service does not write to `board.db` — it goes through the board's HTTP
API, and the board persists. Never open the database file for writing.

## Conventions

- Every service is reachable on its own port and answers `/health`, `/state`,
  `/log`. `board/client.py:serve_piece` does this for you. The harness reads
  `/state` and `/log` to score — a service nobody can reach scores as absent.
- `/state` must match the board. If they disagree, the board is right.
- Addresses come from `team.env` via `board/config.py`. **Never hardcode a host
  or port** — there is one board for the whole team and it is not on your laptop.
- Read time from `board.now()`. On day 3 the board's clock gets skewed, and
  anything keeping its own clock won't even notice.
- Fail loudly and keep running. Catch, log with enough context to debug later,
  continue. A service that exits has dropped out of the system.
- **Never hold a lock across a network call.** `/state` is served from the same
  process as your main loop. If you guard your state with a lock and hold it across
  a `board.claim()` — which gets 4 seconds — `/state` cannot answer, and the harness
  scores your piece as absent while it is running perfectly.

### Timing — the budgets that decide whether you are "alive"

**Two different things here are called a "timeout".** Do not confuse them:
the harness's HTTP budget is in **real seconds** and is about being reachable (SLO 4);
the monitor's fallback timer is in **board-minutes** and is about deciding instead of
hanging (SLO 6).

| What | Budget | Where |
|---|---|---|
| harness → your `/state` | **automatic**: `max(2s, /health × 8)`, capped at 10s | `harness/verdict.py` |
| harness → the board | 3s | `harness/verdict.py` |
| your piece → the board | 4s | `board/client.py` |
| the board's clock | 1 board-minute per **6 real seconds** | `board/state.py` |

The harness times `/health` first — a constant dict that never touches your code — so
it measures the network alone, then derives the `/state` budget from it. On localhost
that is 2.0s. If `/health` is fast and `/state` is slow, the network is fine and your
`state_fn` is the problem.

## Commands

```bash
./run                     everything on this machine (solo, for trying things out)
./run board               host the board for the team   (the board keeper)
./run me                  print YOUR address, the one a teammate can reach
./run mine assigner-A     just your service, against the team's board
./inject late             break it (also: close-runway race bad-clock no-gate all)
./inject verdict          score the board as it stands right now (the board keeper
                          runs this constantly and routes what it finds)
./inject history          every run so far — did that fix actually move the number?
python -m unittest discover -v
```

On Windows those are `.\run.cmd` and `.\inject.cmd` — same arguments. `python
run.py` and `python -m harness.inject` work in any shell on any OS, and are the
fallback if a wrapper misbehaves. Never assume a POSIX shell in code you write
here: five people on five different laptops have to run the same repo.

Watch it: <http://localhost:8080/> — the live board, updating as it moves.

## Skills

Three ship in `.claude/skills/` and you should reach for them rather than
re-deriving the procedure each time:

- **`failure-to-test`** — after `./inject` breaks something: reproduce it, pin it with
  a test that fails first, fix, confirm.
- **`board-triage`** — the board is misbehaving and it is not obvious whose fault it
  is. Reads the board's evidence and names the owner. Never reads a teammate's source.
- **`self-healing-review`** — audit one piece against the four patterns in
  `SELF-HEALING.md` before day 3 makes the point for you.

`SELF-HEALING.md` is the four patterns themselves — retry on refusal, damping, blast
radius, timeout → fallback — written as questions, because working out the answer for
your own piece is the build.

---

# YOURS — fill this in

*Everything above describes what you were given. This part describes what you
build, and nobody can write it for you. Keep it current: when it goes stale, so
does every answer you get.*

## Our service

- **Role:** <board keeper | assigner A | assigner B | re-planner | monitor>
- **Runs at:** <the address a teammate can actually reach>
- **What it does:**
- **What it deliberately does NOT do:**

## Our contract with the services either side

<Exactly what comes in, exactly what goes out, and what happens when the board
refuses a write. Same as `contracts.md` — if the two disagree, fix both.>

## Decisions we made and don't want re-litigated

<e.g. "we retry a refused claim next tick rather than immediately, because
immediate retry just loses the race again". Write down the reasoning, not only
the rule — otherwise the next change quietly undoes it.>

## Things that are true but not obvious from the code

<This section is the point of the exercise. Every one of these is something the
code is relying on a human to remember — and the moment you all go home, an
agent working in here has no way to know it. That is Part A, SLO 3.>

## Skills we've built

<Three skills already ship in `.claude/skills/` — read them; they are the worked
example. SLO 7 is not "invent one from nothing", it is *notice a procedure you keep
repeating and write it down so it can be handed over*.

So: what did YOUR team keep re-deriving that the three don't cover? The deploy dance,
the way you read your own logs, the sequence for bringing your piece back after it
drops out. Write that one, put it in `.claude/skills/`, and name it here.>
