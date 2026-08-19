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

```bash
git clone <this repo>
cd ground-ops-starter
./run
```

Python 3.10+. **No dependencies — stdlib only.** Nothing to install, nothing to
go wrong on the day.

```
board       :8080   /board /now /unassigned /log
assigner A  :8101   /health /state /log
assigner B  :8102
replanner   :8103
monitor     :8104
```

Watch it move:

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

## What you get, and what you build

| | | |
|---|---|---|
| `board/` | **given** | The shared state. Both hard rules enforced, in one place, under one lock. Plus `client.py` — the client and the "be reachable" helper, so you don't write HTTP boilerplate three times. |
| `feeds/` | **given** | Arrivals and departures, live, with duplicates in them. |
| `harness/` | **given** | The failure injector and the verdict checks we run on day 2. Run them yourself as often as you like. |
| `assigners/` | **yours** | Two or more, running at once. They compete. |
| `replanner/` | **yours** | Redo the flights a delay actually touched — and damp it. |
| `monitor/` | **yours** | Timer, safe fallback, logs, and the tests. |
| `contracts.md` | **yours** | Written before any code. Day 1, first thing. |
| `tests/` | **yours** | One per piece, plus one per failure you hit. |

**What's in `assigners/`, `replanner/` and `monitor/` right now runs, and is
wrong.** Each file opens with exactly what is wrong with it and which outcome it
maps to. That is your starting point, not your answer — read the header of each
before you touch it.

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

- **8** — name the real user and decide what your piece does and doesn't do, before writing code
- **1** — agree what your piece takes in and hands out, and don't change it without telling anyone
- **4** — get it running somewhere a teammate can reach
- **6** — fail loudly and keep going instead of dying quietly

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
