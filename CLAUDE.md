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
injected through on day 2** — the board and the feeds are the only things the
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
  the day-2 debugging tool — it answers "what happened to this flight, in order,
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
- Read time from `board.now()`. On day 2 the board's clock gets skewed, and
  anything keeping its own clock won't even notice.
- Fail loudly and keep running. Catch, log with enough context to debug later,
  continue. A service that exits has dropped out of the system.

## Commands

```bash
./run                     everything on this machine (solo, for trying things out)
./run board               host the board for the team   (the board keeper)
./run me                  print YOUR address, the one a teammate can reach
./run mine assigner-A     just your service, against the team's board
./inject late             break it (also: close-runway race bad-clock no-gate all)
./inject verdict          score the board as it stands right now (the board keeper
                          runs this constantly and routes what it finds)
python -m unittest discover -v
```

On Windows those are `.\run.cmd` and `.\inject.cmd` — same arguments. `python
run.py` and `python -m harness.inject` work in any shell on any OS, and are the
fallback if a wrapper misbehaves. Never assume a POSIX shell in code you write
here: five people on five different laptops have to run the same repo.

Watch it: <http://localhost:8080/> — the live board, updating as it moves.

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

<A skill is a procedure you'd otherwise repeat by hand. The obvious one comes up
on day 2, the second time you turn a failure into a regression test — write the
steps down once and stop re-deriving them. That's SLO 7.>
