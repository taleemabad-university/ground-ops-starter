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
the board log as it happens. On day 2 you can watch a failure land in real time
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

## Four people, four laptops, one board

You each work on your own machine — that part is normal. What is shared is the
**board**: there is exactly one for the whole team, hosted in one place, and all
four of your pieces point at it.

The trap is `./run`, because it starts a board of its own. If all four of you
run it you get four separate airports that never meet, and every failure we
inject on day 2 politely does nothing. **One** person runs `./run board`;
everyone else runs `./run mine <role>`.

Everyone clones the same repo. Then each person owns exactly one role:

| Role | Runs | Owns |
|---|---|---|
| **assigner A** | `./run mine assigner-A` | `assigners/` — competes with B for gates |
| **assigner B** | `./run mine assigner-B` | `assigners/` — the same code, second instance |
| **re-planner** | `./run mine replanner` | `replanner/` — blast radius + damping |
| **monitor** | `./run mine monitor` | `monitor/` — timer, fallback, logs, tests |

### Day 1, in order

1. **Together, before any code** — fill in `contracts.md`, and decide who hosts
   the board.
2. **The host runs `./run board`.** It prints the address to give everyone.
3. **Everyone copies `team.env.example` to `team.env`** and puts that address in
   `BOARD_URL`, plus their own reachable address in their `*_URL` line. Commit
   it — `team.env` is the machine-readable half of your contract.
4. **Each person runs `./run mine <their-role>`** and builds their piece.
5. Open the board's address in a browser. All four pieces should show
   **answering**. If one says *no answer*, that piece is not reachable yet — and
   that is SLO 4, not a detail.

Your address is not `localhost` — that only means "this machine". On mac,
`ipconfig getifaddr en0` gives you the one a teammate can actually reach.

### Getting off your laptop

A laptop that sleeps takes the whole team's board with it, so the board wants a
real home. `Procfile` and `railway.toml` are in the repo and the board respects
`$PORT`, so it deploys as-is. Point `BOARD_URL` at the deployed address and
nothing else changes. Same trick works for your own piece.

---

## What you get, and what you build

| | | |
|---|---|---|
| `board/` | **given** | The shared state, both hard rules under one lock, and `db.py` — SQLite persistence plus the full decision history. Plus `client.py`, the client and "be reachable" helper. |
| `feeds/` | **given** | Arrivals and departures, live, with duplicates in them. |
| `harness/` | **given** | The failure injector and the verdict checks we run on day 2. Run them yourself as often as you like. |
| `assigners/` | **yours** | Two or more, running at once. They compete. |
| `replanner/` | **yours** | Redo the flights a delay actually touched — and damp it. |
| `monitor/` | **yours** | Timer, safe fallback, logs, and the tests. |
| `contracts.md` | **yours** | Written before any code. Day 1, first thing. |
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

**Skills** are yours entirely. A skill is a procedure you would otherwise repeat
by hand. Don't invent one on day 1; you'll know when you need it. The obvious
candidate turns up on day 2, the second time you turn a failure into a
regression test — write the steps down once instead of re-deriving them. That's
SLO 7 as something you can hand to someone else.

### Where the data lives

The board stores everything in **SQLite** — `board.db`, standard library, nothing
to install. It buys two things:

**The board survives a restart.** Whoever hosts it can reboot without wiping the
team's afternoon; `./run` restores every flight from disk. `./run fresh` if you
want to start genuinely empty.

**Every decision is kept.** The in-memory log holds the last 400 events; the
`decisions` table holds all of them, indexed by flight and by actor. On day 2
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

## How we break it on day 2

**We never touch your code.** Not one line, not on day 2, not during the demo.

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

## The two days

**Day 1 — design it, build it, connect it.**
Fill in `contracts.md` *before any code*. Then build your piece to what was
agreed, and get it running somewhere a teammate can reach — not just on your
laptop. Connect it end to end.
*Done when: every piece is reachable, and the board runs start to finish — even
if it's rough.*

**Day 2 — break it, fix it, show it.**
Write a test for your piece. We inject the failures. Work out which piece broke
and whose it is, then handle it so one broken piece doesn't quietly take the rest
down. **Every failure becomes a test.** Then a live demo — with a failure
injected during it.
*Done when: no double-books, survives the injected failures, and bends instead of
breaking.*

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
