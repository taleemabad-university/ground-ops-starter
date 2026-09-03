# Ground Ops — the graduation build

An airport's gates and runways, run by software, that has to survive a bad day
on its own.

Flights land and take off. Every flight needs a gate to park at and a runway slot
to use, and something has to decide which flight gets which. That something is
what you build. The hard part is not the deciding — it is that the moment one
flight is late, the whole plan has to be redone, **by itself**, while flights keep
arriving.

One late flight holds its gate. So the next arrival can't park. So it misses its
runway slot. So the flight after that gets bumped. One delay can move the whole
board.

**Three days.** Day 1 you understand it, day 2 you build it, day 3 we break it.
**Start at [DAY-1.md](DAY-1.md)** — and don't write a service before you've been
through it.

---

## Get it running

Python 3.10+. **No dependencies — stdlib only.** Nothing to install, nothing to
go wrong on the day.

**mac / linux**

```bash
git clone <this repo>
cd ground-ops-starter
./run
```

**windows** — `./run` is a mac/linux script and PowerShell will not run it. Use
the Windows one, or just call Python directly:

```powershell
git clone <this repo>
cd ground-ops-starter
.\run.cmd
```

```powershell
python run.py        # works everywhere, in any shell. use this if anything else misbehaves
```

Everywhere in this README, `./run x` on Windows means `.\run.cmd x` (or
`python run.py x`), and `./inject x` means `.\inject.cmd x` (or
`python -m harness.inject x`).

If `python` is not found on Windows, install it from python.org and tick **"Add
Python to PATH"** in the installer.

```
board       :8080   /board /now /unassigned /log
assigner A  :8101   /health /state /log
assigner B  :8102
replanner   :8103
monitor     :8104
```

**Watch it move — open <http://localhost:8080/>.** The live board draws itself:
gates, runway slots, every flight, whether each of your pieces is answering, and
the board log as it happens. On day 3 you can watch a failure land in real time
instead of reading it out of a log afterwards.

Or read it raw:

```bash
curl -s localhost:8080/board | python3 -m json.tool
curl -s localhost:8080/log
```

Break it:

```bash
./inject late          # or close-runway | race | bad-clock | no-gate | all
```

Run the tests:

```bash
python -m unittest discover -v
```

---

## Five roles, one board

You each work on your own machine — that part is normal. What is shared is the
**board**: there is exactly one for the whole team, hosted in one place, and all
four of the pieces you build point at it.

The trap is `./run`, because it starts a board of its own. If everyone runs it you
get five separate airports that never meet, and every failure we inject on day 3
politely does nothing. The **board keeper** hosts the one board; everyone else runs
`./run mine <role>`.

Everyone clones the same repo. Then each person owns exactly one role:

| Role | Runs | Owns |
|---|---|---|
| **board keeper** | `./run board` | The deploy, `team.env`, `contracts.md`, and the answer to "is the board healthy". **Team lead.** |
| **assigner A** | `./run mine assigner-A` | `assigners/` — competes with B for gates |
| **assigner B** | `./run mine assigner-B` | `assigners/` — the same code, second instance |
| **re-planner** | `./run mine replanner` | `replanner/` — blast radius + damping |
| **monitor** | `./run mine monitor` | `monitor/` — timer, fallback, logs, tests |

*Four people instead of five? The board keeper doubles as the monitor — both are
observability roles.*

### The board keeper

The board is **given code that nobody edits**, including the board keeper. What the
board keeper owns is *running* it, and leading the team while it runs:

- **Deploys the board** off a laptop, so it doesn't sleep and take the team's day
  with it. `Procfile` and `railway.toml` ship in the repo and the board respects
  `$PORT`. This is SLO 4 done more concretely than anyone else on the team does it.
- **Owns `team.env`** and every address in it.
- **Owns `contracts.md`** and its change log — SLO 11.
- **Answers "is the board healthy", for every piece.** Not by reading a teammate's
  source — by reading the evidence the board already keeps:

  ```bash
  ./inject verdict                              # the five checks, right now
  curl -s localhost:8080/log                    # what the board saw
  curl -s "localhost:8080/decisions?flight=PK-304"   # one flight's whole life
  ```

  "The board isn't settling" goes to the re-planner. "Assigner B's state has split
  from the board" goes to assigner B. "AI-201 hung and nobody decided" goes to the
  monitor. Same evidence everybody else can see, so it is a diagnosis and not an
  opinion.
- **Chairs** the day-1 contract session and the day-3 demo.

### Getting off your laptop

A laptop that sleeps takes the whole team's board with it, so the board wants a
real home. **This is the board keeper's job, on day 1.** `Procfile` and
`railway.toml` are in the repo and the board respects `$PORT`, so it deploys
as-is. Point `BOARD_URL` at the deployed address and nothing else changes. Same
trick works for your own piece.

---

## What the repo does for you — skills and the healing patterns

### The four healing patterns

A self-healing system is not one that never gets hit. It is one that takes the hit,
says so, and keeps going. There are exactly four patterns you have to get right, and
each one maps to a failure we inject on day 3:

| Pattern | Whose | Fails without it |
|---|---|---|
| Retry on refusal | assigners | the race |
| Damping | re-planner | the runaway |
| Blast radius | re-planner | the runaway, and it worsens the race |
| Timeout → fallback | monitor | the dead end |

**[SELF-HEALING.md](SELF-HEALING.md) is the four questions**, plus the three things
the repo already heals for you — so you can tell what you are standing on from what
you still have to build. Read it on day 1.

### Three skills ship with the repo

In [.claude/skills/](.claude/skills/). Clone the repo and Claude Code can use them:

| Skill | What it does |
|---|---|
| `failure-to-test` | Turn an injected failure into a regression test that fails before the fix and passes after |
| `board-triage` | Work out whose piece broke, from the board's evidence — never from a teammate's source |
| `self-healing-review` | Audit your piece against the four patterns before day 3 does it for you |

**SLO 7 is still yours.** You are not scored on having invented the first example —
you are scored on **recognising a procedure you keep repeating and writing it down**.
So: use these, and then write the one they don't cover. Every team hits something
specific to how they built it; that is your skill, and it goes in
`.claude/skills/` alongside these.

### Are you actually getting better?

Every scorecard is recorded. Nothing to set up:

```bash
./inject verdict     # score the board now — and see what moved since last time
./inject history     # every run so far
```

```
2026-09-03 09:14:02  2/4  .+.+    04 · the runaway
2026-09-03 11:40:55  4/4  ++++    04 · the runaway
```

After a fix, the scenario's score should move. **If it didn't, you fixed something
else** — that is the honest check, and it is the whole reason the loop is written
down instead of remembered.

---

## What `contracts.md` is, and who fills it in

> A contract is the promise your service makes to the one next to it: exactly what
> you take in, exactly what you hand back, and what you do when the board says no.
> Written down before any code — so that when two pieces disagree at 4pm, you can
> tell whose fault it is in a minute instead of an hour.

That is SLO 1, and it is the first thing we check. `contracts.md` is filled in on
**day 1, before any code**. Nobody fills it in alone, and no row is left to "the
team" — every row has a name against it:

| Section of `contracts.md` | Who writes it | What specifically |
|---|---|---|
| Who this is for | Everyone, board keeper chairs | One sentence. One person, one job, one shift — not "airports". |
| Who owns what | Board keeper | Names, ports, health-check URLs, the deployed board address |
| `assigner → board` | Assigner A + B **together** | `POST /claim {flight,gate,actor}` — and what they do on a 409 |
| `re-planner → board` | Re-planner | Which writes it makes, its **blast-radius rule** and its **damping rule** |
| `monitor → board` | Monitor | `POST /flag {flight,decision,reason}` — the allowed decision values, and its **timeout in board-minutes** |
| `board → everyone` | Board keeper | The 200 / 409 shapes every writer has to handle |
| What we are NOT building | Everyone | Three lines, decided out loud before you are tired |
| MVP / roadmap | Everyone; board keeper holds the line | The v1 that must work by end of day 2 |
| Changes to this file | Board keeper owns it | Every contract change once building has started — SLO 11 |

`contracts.md` ships with the first row of the contracts table **filled in as a
worked example**. That level of detail — the exact shape, and a real answer in the
refusal column — is the standard for every other row.

Two things people treat as implementation detail that are actually contracts, and
both need a number in them: **the re-planner's damping rule** (it decides how hard
the board gets written to, and the board settling is one of the five things we
score) and **the monitor's timeout in board-minutes** (the board's clock runs one
minute per six real seconds, so a timeout in wall-clock seconds never fires).

---

## What you get, and what you build

| | | |
|---|---|---|
| `board/` | **given** | The shared state, both hard rules under one lock, and `db.py` — SQLite persistence plus the full decision history. Plus `client.py`, the client and "be reachable" helper. |
| `feeds/` | **given** | Arrivals and departures, live, with duplicates in them. |
| `harness/` | **given** | The failure injector and the verdict checks we run on day 3. Run them yourself as often as you like — every run is recorded, so you can see the number move. |
| `SELF-HEALING.md` | **given** | The four healing patterns, as questions. Read on day 1. |
| `.claude/skills/` | **half each** | Three skills ship. The one for whatever *you* keep repeating is yours to add. |
| `assigners/` | **yours** | Two or more, running at once. They compete. |
| `replanner/` | **yours** | Redo the flights a delay actually touched — and damp it. |
| `monitor/` | **yours** | Timer, safe fallback, logs, and the tests. |
| `contracts.md` | **yours** | Written before any code. Day 1, and every row has an owner. |
| `tests/` | **yours** | One per service, plus one per failure you hit. |
| `CLAUDE.md` | **half each** | The given half is written. The `YOURS` half is empty on purpose — see below. |

**What's in `assigners/`, `replanner/` and `monitor/` right now runs, and is
wrong.** Each file opens with exactly what is wrong with it and which outcome it
maps to. That is your starting point, not your answer — read the header of each
before you touch it.

### CLAUDE.md and skills — who writes what

`CLAUDE.md` ships with the top half filled in: the board contract, the do-not-edit
list, the conventions, the commands. That is the same deal as the board itself —
it's setup, and setup is not what we're testing.

**The `YOURS` half is empty and stays that way until you write it.** What your
service does and doesn't do, the contract with the services either side, the
decisions you don't want quietly undone, and — the one that counts — the things
that are true but not obvious from reading the code.

That last section is the whole point. Every line in it is something your build
is relying on a human to remember. Right now that human is you, sitting next to
it. On Monday it isn't, and an agent working in this repo has no way to know any
of it. Writing those down *is* Part A SLO 3 — hidden dependencies — done for
real rather than described.

**Skills — three ship, the next one is yours.** A skill is a procedure you would
otherwise repeat by hand, written down so nobody re-derives it. The repo ships
`failure-to-test`, `board-triage` and `self-healing-review` in
[.claude/skills/](.claude/skills/) — use them from day 1, and read them, because they
are also the worked example of what a skill looks like.

**SLO 7 is not "did you invent one from nothing".** It is *did you notice a procedure
you keep repeating, and write it down so it can be handed over*. So the outcome is:
use the three, then add the one they don't cover. Every team hits something specific
to how they built it — a deploy dance, a way of reading their own logs, the sequence
for bringing a piece back after it drops out. **That** is your skill, and by day 3 you
will know exactly what it is.

### Where the data lives

The board stores everything in **SQLite** — `board.db`, standard library, nothing
to install. It buys two things:

**The board survives a restart.** Whoever hosts it can reboot without wiping the
team's afternoon; `./run` restores every flight from disk. `./run fresh` if you
want to start genuinely empty.

**Every decision is kept.** The in-memory log holds the last 400 events; the
`decisions` table holds all of them, indexed by flight and by actor. On day 3
that is how you answer *"is this my fault or upstream?"* — SLO 2, fault
isolation — without reading anybody's code:

```bash
# everything that ever happened to one flight, in order
curl -s "localhost:8080/decisions?flight=PK-304" | python3 -m json.tool

# who keeps losing races?
sqlite3 board.db "SELECT actor, COUNT(*) FROM decisions
                  WHERE event='claim_rejected' GROUP BY actor ORDER BY 2 DESC"
```

You never write to `board.db` yourself — you go through the board's API and it
persists for you.

---

## The two hard rules

Enforced by the board, not by you:

```
one gate holds one flight, ever
one slot holds one flight, ever
```

So the board will never double-book. **That is not the same as your build being
correct.** When the board refuses a claim it answers `409` and *does not change*.
If your piece carries on as though it won, its picture of the world and the
board's have just split — and the flight you think you placed is sitting
nowhere, with nobody looking for it.

Every write can be refused. Read what comes back.

```python
ok, reason = board.claim("PK-304", "G3")
if not ok:
    ...   # somebody beat you to it. the board did NOT move. now what?
```

---

## How we break it on day 3

**We never touch your code.** Not one line, not on day 3, not during the demo.

Every injection goes through the two things we gave you — the **board** and the
**feeds**. Your pieces only ever see the world through those two doors, so we
change what comes through the doors and watch what your build does about it.
That is why the board and the feeds arrive finished: they are not a favour, they
are the injection surface.

| | What we do | Where it enters | The question |
|---|---|---|---|
| `late` | A flight runs 90 min late and keeps its gate | board | Does the re-plan stay clean, or does one delay wreck the whole board? |
| `close-runway` | R3 and R4 shut; anyone holding them is evicted | board | Does it move those flights, or lose them without saying anything? |
| `race` | Two claims hit the last free gate in the same instant | board | Does the board double-book — and does the loser *know* it lost? |
| `bad-clock` | The board clock jumps 47 min forward | board | Does the re-planner spin out, or does the damping hold? |
| `no-gate` | A flight arrives, every gate is full, nothing opens | feeds + board | Does the backup kick in, or does it hang forever? |

Because it all comes in from outside, anything your piece *assumes* about the
world we can make untrue without warning, in front of an audience. Handle the
answers the board gives you and none of it can hurt you.

### What counts as surviving

`harness/verdict.py` reads the board, and reads the `/state` and `/log` your own
pieces expose. It never opens your source.

| Check | Fails when |
|---|---|
| no double-book | A piece's state disagrees with the board about who holds what |
| no silent loss | A flight ends up nowhere with no decision recorded |
| board converges | The board is still being hammered at the end of the window — it's spinning, not settling |
| pieces alive | Something stopped answering instead of degrading |
| decision made | A stuck flight was never held or diverted — it just hung |

```bash
./inject all       # all five, in order, with a scorecard
./inject verdict   # just check the board as it stands
```

Almost nobody passes all five cold. **That is the point** — it shows exactly
which skills to work on.

---

## The three days

**Day 1 — understand it.** *Nobody writes a service.*
Run what we gave you and watch it. Follow one flight through the board's decision
log. Read what is wrong with the piece you are taking. Watch two failures land
without fixing them. Then fill in `contracts.md` together, and the board keeper
deploys the board. **Step by step: [DAY-1.md](DAY-1.md).**
*Done when: every person can explain the problem in their own words,
`contracts.md` is filled in with every row owned, and the deployed board is
reachable by all five.*

**Day 2 — build it and connect it.**
Build your piece to what was agreed on day 1 — the contract already exists, so you
start writing code, not arguing about field names. Get it running somewhere a
teammate can reach, not just on your laptop.
*Done when: every piece is reachable, and the board runs start to finish — even
if it's rough.*

**Day 3 — break it, fix it, show it.**
Write a test for your piece. We inject the failures. Work out which piece broke
and whose it is, then handle it so one broken piece doesn't quietly take the rest
down. **Every failure becomes a test.** Then a live demo — with a failure
injected during it.
*Done when: no double-books, survives the injected failures, and bends instead of
breaking.*

Day 1 is new, and it is there because it was the missing piece last time: teams
who were good at this went straight to building and spent the back half
discovering they had solved the wrong problem.

---

## What you're scored on

Not on how good the demo looked. On whether you did the work **on your own** or
**after being told** — and the line between those two is what decides
graduation.

The four that matter most:

| | Skill | What it means here |
|---|---|---|
| **8** | scoping | name the real user, decide what's in and out, before writing code |
| **1** | interface contract | agree your service's inputs and outputs, never change them silently |
| **4** | deployment | running on an endpoint a teammate can reach — not localhost |
| **6** | graceful degradation | fail loudly and keep running instead of dying silently |

---

## When something breaks and it isn't obvious whose fault it is

That is the job. Start here:

```bash
curl -s localhost:8080/log            # what the board saw, newest last
curl -s localhost:8101/state          # what assigner A believes
curl -s localhost:8101/log            # what it decided, and why
```

If the board's log and your piece's log disagree, **the board is right.** Work
backwards from there — and tell whoever owns the piece feeding into yours, plainly
and early. That's SLO 11, and it is the difference between a ten-minute fix and
losing an afternoon.
