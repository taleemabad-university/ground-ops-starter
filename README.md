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

**Not sure what `held` or `divert` mean?** Every word this repo uses — the flight
statuses, the log events, the exact string the board sends back when it refuses you —
is defined in **[The words we use](#the-words-we-use)** at the end. Start there, not
in the source.

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

Below, every role in the same shape: what you own, what you decide, which healing
pattern is yours, which failure is aimed at you, and which verdict will say your name
out loud on day 3. Read your own block, then read the one either side of you — those
are the people you have a contract with.

### assigner A · assigner B

Two people, the same file, two instances running at the same time. **They compete for
gates on purpose.**

- **Owns** — `assigners/`. Read the header of `assigners/naive.py` first: it says
  exactly what is wrong with the version that ships.
- **Decides** — which flight parks at which gate. `POST /claim {flight, gate, actor}`.
- **Runs** — `./run mine assigner-A` on `:8101`, `./run mine assigner-B` on `:8102`.
- **Your healing pattern** — **retry on refusal** (pattern 1). A `409` means the other
  assigner got there first and *the board did not change*. The question is what happens
  to the flight you did not place.
- **The failure aimed at you** — `race`: two claims hit the last free gate in the same
  instant.
- **The verdict that names you** — `no double-book`, and `no silent loss` for the
  flight you dropped. It says your name:

  > `assigner-B thinks PA-450 is on G4, board says TK-709 — its state has split from the board's`

- **Your row in `contracts.md`** — `assigner → board`, written by **A and B
  together**: the claim shape, what each of you does on a 409, and how you divide the
  work so you are not both grabbing G1 every tick.
- **Done when** — a refused claim leaves the flight back in play, and your `/state`
  never claims a gate the board didn't give you.

### the re-planner

One flight slipped, so the flights behind it have to be redone. The hard part is
stopping.

- **Owns** — `replanner/`. The header of `replanner/naive.py` lists three things wrong
  with it.
- **Decides** — which flights a delay *actually* touched, and re-issues their runway
  slots. `POST /slot {flight, slot, actor}`.
- **Runs** — `./run mine replanner` on `:8103`.
- **Your healing patterns** — **damping** (pattern 2) *and* **blast radius**
  (pattern 3). You are the only role with two, because you are the only piece whose
  own writes can set off its own next run.
- **The failure aimed at you** — `bad-clock`: the board clock jumps 47 minutes forward,
  so every flight looks late at once. The piece whose whole job is fixing the board is
  the piece most likely to melt it.
- **The verdict that names you** — `board converges`:

  > `board still taking 31 writes/sec at the end of the window (was 0.8/s before the injection) — it is not settling, it is spinning`

- **Your row in `contracts.md`** — `re-planner → board`: which writes you make, your
  **blast-radius rule in one sentence**, and your **damping rule with a number in
  it** — at most one re-plan per flight per N board-minutes. Both are contracts, not
  implementation details.
- **Done when** — a delay moves the flights it touched and nothing else, and the board
  goes quiet again afterwards.

### the monitor

The piece that notices nothing is happening, and makes a call anyway.

- **Owns** — `monitor/`, and `tests/`. The header of `monitor/naive.py` lists four
  things wrong with it, and one of them is "no tests".
- **Decides** — when a flight has waited too long, and what to do about it.
  `POST /flag {flight, decision, reason}`, where `decision` is `held` or `divert` and
  nothing else.
- **Runs** — `./run mine monitor` on `:8104`.
- **Your healing pattern** — **timeout → fallback** (pattern 4). Waiting forever is
  the same as crashing, except harder to notice.
- **The failure aimed at you** — `no-gate`: a flight arrives, every gate is full, and
  nothing ever opens up. There is no right answer available — making a call regardless
  *is* the answer.
- **The verdict that names you** — `decision made`, the fifth check, which only runs
  for this scenario:

  > `ZZ-999 is still 'pending' with nowhere to go — nothing timed out, nothing chose a backup, it just hung`

- **Your row in `contracts.md`** — `monitor → board`: the flag shape, the allowed
  decision values, and your **timeout in board-minutes**. Not seconds — the board's
  clock runs one minute per six real seconds, so a wall-clock timeout silently never
  fires inside the window we test in. This has caught every cohort so far.
- **Done when** — no flight can sit undecided, and your log says what you decided and
  why.

### the board keeper — team lead

The board is **given code that nobody edits**, including the board keeper. What the
board keeper owns is *running* it, and leading the team while it runs. **The board
keeper is a person, not a piece of code.**

- **Owns** — the deploy, `team.env` and every address in it, `contracts.md` and its
  change log (SLO 11), and the answer to "is the board healthy". Not `board/` — nobody
  owns that.
- **Decides** — nothing about flights. Whose problem a failure is.
- **Runs** — `./run board`: the **one** board for the whole team, on `:8080`.
- **Your pattern** — none of the four; those belong to the pieces. Yours is the
  **deploy**, which is SLO 4 done more concretely than anyone else on the team does
  it. `Procfile` and `railway.toml` ship in the repo and the board respects `$PORT`,
  so it goes up as-is. **Day 1 job** — see "Getting off your laptop" below.
- **The failure aimed at you** — all five, indirectly. Every injection enters through
  the board or the feeds, so you see it land first and route it.
- **The verdict that names you** — `pieces alive`, when an address in `team.env` is
  wrong; and `no silent loss` when it abstains with *"window too short to judge"* —
  that one means **the board** was unreachable, so fix the board before you read
  anything into the rest of the score.
- **Your rows in `contracts.md`** — "Who owns what" (names, ports, health-check URLs,
  the deployed board address) and `board → everyone` (the 200 / 409 shapes every writer
  has to handle). You also **chair** the day-1 contract session and the day-3 demo.
- **Done when** — all five of you load the same deployed board and see the same
  flights.

**Answering "is the board healthy", for every piece.** Not by reading a teammate's
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

## Scope — what we model, and what we don't

**The whole system in one sentence:** flights arrive on a feed, something has to give
each one a gate to park at and a runway slot to use, and that plan has to redo itself
when a flight runs late.

**What we model.** Six gates, `G1`–`G6`. Four runway slots, `R1`–`R4`. Arrivals and
departures. An ETA in board-minutes. A delay. A re-plan. A safe fallback. A log of
every decision and who made it. **That is the entire world your pieces can see** —
through two doors, the board and the feeds, and nothing else.

**What we deliberately don't model.** None of this is an oversight:

| Not in this build | Which means |
|---|---|
| baggage, crew, fuel, catering, de-icing | there is no resource to contend for except the gate and the slot |
| passengers, boarding, connections, misconnects | a flight is an id, a kind, an ETA and a status |
| pushback, taxi, turnaround time | a gate is held until somebody releases it — there is no "eight minutes to clean the aircraft" |
| weather, real ATC, ground stops | delays and closures arrive from the harness, not from a model of the world |
| aircraft types and sizes | **any flight fits any gate**, and any slot |
| terminals, walking distance, airline preference | all six gates are equally good, so there is no *best* gate — only a free one |
| cost, fairness, on-time percentage | there is nothing to optimise. There are two hard rules not to break, and five verdicts to survive |

Every one of those is a scope decision **already made for you**, so that the only hard
part left is the one you are actually scored on: keeping four services correct while
the world changes underneath them. If your build seems to need one of these, the change
is wrong — the same rule that applies to the board itself.

**What is still yours to scope.** Three lines in `contracts.md` under *What we are NOT
building*, and the v1 under *MVP / roadmap*. Decided out loud on day 1, before anyone
is tired, and held by the board keeper when time runs short. That is SLO 8 and SLO 9,
and scoping is one of the four things that decides graduation — so those three lines
are not a formality.

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

### What counts as surviving — all five verdicts

`harness/verdict.py` reads the board, and reads the `/state` and `/log` your own
pieces expose. It never opens your source.

```bash
./inject all       # all five failures, in order, with a scorecard
./inject verdict   # just check the board as it stands
./inject history   # every run so far — are you actually improving?
```

Most scorecards show **4 checks**. `no-gate` shows **5** — `decision made` only runs
when a scenario has a specific stuck flight to ask about. That is expected, not a bug.

---

#### 1 · `no double-book`

**Checks:** the board never has a gate whose flight disagrees with itself, *and* every
piece's `/state` agrees with the board about what it is holding.

> `assigner-B thinks PA-450 is on G4, board says TK-709 — its state has split from the board's`

**Cause:** the piece wrote down a claim the board refused. `claim()` returns
`(ok, reason)`; the shipped naive assigner throws that away. **Whose:** the named
piece. **Fix:** read the return value and don't record a refused claim as placed —
pattern 1 in [SELF-HEALING.md](SELF-HEALING.md).

> ⚠️ **This check skips pieces it cannot reach.** An absent piece quietly *passes*
> here while failing `pieces alive`. If you see that combination, fix reachability
> first — this check has not actually looked at that piece yet.

#### 2 · `no silent loss`

**Checks:** a flight that *had* a gate or slot and lost it must end up somewhere, or
have a decision recorded. A flight still queued behind full gates has not been lost —
it was never placed.

> `2 flight(s) were placed and then came off the board with no decision: EK-621, QR-118`

**Cause:** something released or evicted a flight and nothing picked it up. **Whose:**
whoever released it — check `/decisions?flight=…`. **Fix:** every release needs a
follow-up.

> `window too short to judge` — the board was unreachable for most of the window, so
> the check abstains rather than fails. **Fix the board first**; this verdict is not
> telling you anything about your piece.

#### 3 · `board converges`

**Checks:** the board settles. Measured **against how busy it was before the
injection**, because a healthy steady rate depends on how you built it — an absolute
ceiling would be unfair across teams.

**Threshold:** `baseline × 2.5` when there is a baseline, otherwise the absolute
`RUNAWAY_WRITES_PER_SEC = 25`.

> `board still taking 31 writes/sec at the end of the window (was 0.8/s before the injection) — it is not settling, it is spinning`

**Cause:** no damping, or too wide a blast radius — a re-plan triggers a board change,
which looks like a change, which triggers a re-plan. **Whose:** the re-planner.
**Fix:** patterns 2 and 3 in [SELF-HEALING.md](SELF-HEALING.md).

#### 4 · `pieces alive`

**Checks:** every piece in `team.env` answers `/state` inside its budget. A piece
nobody can reach is a piece that dropped out — that is SLO 4, not a detail.

It now tells you **which way** it was unreachable:

```
FAIL  pieces alive
      assigner-A [refused] http://127.0.0.1:8101 — nothing is listening there —
                  is it running? is team.env right?
      monitor [too slow] http://10.0.1.9:8104 — /health answered in 4ms so the
                  network is fine, but /state took longer than 2.0s — your
                  state_fn is blocking. holding a lock across a board call?
```

| What you see | What it means |
|---|---|
| `[refused]` | Nothing listening. Not running, or the wrong address in `team.env`. |
| `[too slow]` | It answered `/health` fine, so the network is not the problem — **your `state_fn` is blocking**. |
| `[no answer]` | Address is right, nothing came back. Firewall, or the host is down. |
| `[bad response]` | It replied, but not with JSON the harness could read. |
| `[http 5xx]` | It answered with an error instead of state. |

**See "My piece is running but scores as absent" below.**

#### 5 · `decision made` — `no-gate` only

**Checks:** the stuck flight was actually decided — `held` or `divert` — rather than
left hanging.

> `ZZ-999 is still 'pending' with nowhere to go — nothing timed out, nothing chose a backup, it just hung`

**Cause:** no timer, or a timeout written in wall-clock seconds that never fires.
**Whose:** the monitor. **Fix:** pattern 4 in [SELF-HEALING.md](SELF-HEALING.md), and
**put the timeout in board-minutes**.

#### And one that is not a verdict

> `check blew up: KeyError('gates')`

The check itself raised. Almost always a piece returning a shape the harness could not
read. It counts as a fail — fix the shape.

---

### Timing — every budget in one place

Two different things in this repo are called a "timeout", and confusing them costs
people an afternoon:

- **The harness's HTTP budget** is in **real seconds** and is about *being reachable*
  (SLO 4).
- **The monitor's fallback timer** is in **board-minutes** and is about *deciding
  instead of hanging* (SLO 6).

| What | Budget | Where |
|---|---|---|
| harness → your `/state` | **automatic**: `max(2s, /health × 8)`, capped at 10s | `harness/verdict.py` |
| harness → the board | 3s | `harness/verdict.py` |
| your piece → the board | 4s | `board/client.py` |
| the board's clock | 1 board-minute per **6 real seconds** | `board/state.py` |

**Why the `/state` budget is automatic.** A piece on your laptop and a piece deployed
behind a load balancer don't deserve the same stopwatch, so the harness times
`/health` first — a constant dict that never touches your code, which measures the
*network alone* — and gives `/state` a budget derived from it. On localhost that lands
on the floor: **2.0 seconds**. On a slow link it stretches. The gap between the two is
the diagnosis: if `/health` is fast and `/state` is slow, the network is fine and your
code is the problem.

### My piece is running but scores as absent

The single most common one. Time it yourself:

```bash
time curl -s localhost:8101/health    # the network only
time curl -s localhost:8101/state     # the network AND your state_fn
```

- **Both fast, still failing?** The harness isn't reaching the address in `team.env`.
  `localhost` only means "this machine" — run `./run me` for the one a teammate can
  actually reach.
- **`/health` fast, `/state` slow?** Your `state_fn` is blocking. The usual cause: a
  lock held across a board call. `board.claim()` gets **4 seconds**, and `/state`
  cannot answer while you hold that lock — so a piece that is running perfectly gets
  scored as dead. **Never hold a lock across a network call.**
- **Both slow?** A slow link. The budget stretches automatically, up to 10s.

---

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

---

## The words we use

Every word below appears in the code, on the board page, or in a verdict message.
Where it is a real airport word, the real meaning is here too — because knowing what
a controller means by "hold" is most of knowing why the monitor exists.

### A flight's status

Five values, defined in `board/state.py`. A flight is always in exactly one of them.

| Status | At a real airport | Here | Who sets it |
|---|---|---|---|
| `pending` | in the schedule, nothing arranged for it yet | the board knows the flight; it has no gate | the feeds when it arrives — and the board itself, whenever a flight loses its gate |
| `gated` | parked at a stand | holds a gate, no runway slot yet | an assigner, `POST /claim` |
| `slotted` | parked, and cleared for a runway window | holds a gate **and** a runway slot | the re-planner, `POST /slot` |
| `held` | told to wait — on the tarmac, or in a holding pattern | **decided to wait**: nowhere to go, and the monitor said so out loud | the monitor, `POST /flag` |
| `divert` | sent to a different airport | this airport cannot place it at all | the monitor, `POST /flag` |

`pending` is the one people misread. It does not mean lost and it does not mean
broken — a flight queued behind full gates is `pending`, and that is correct. It
becomes a problem only when nothing ever changes it. Two details worth knowing:
`GET /unassigned` lists exactly these flights (`pending`, no gate), so a flight
drops off that queue the moment the monitor flags it; and a flight can hold a runway
slot while still `pending`, because `slotted` means *both*.

**So what do `held` and `divert` actually mean?**

**`held`** — the plane waits. Real ops hold an aircraft on the tarmac when there is
nowhere to put it yet, or in a holding pattern in the air when the ground is not
ready. A hold solves nothing by itself; it buys time, and — this is the part that
matters here — **somebody has decided that this aircraft is waiting, and written down
why**. In this repo it is the monitor's safe fallback for a flight with nowhere to go:
a recorded decision to wait, which is not the same thing as a hang.

**`divert`** — the flight goes somewhere else. Real ops divert when the destination
genuinely cannot take the aircraft: the runway is shut, the weather is below limits,
no stand will free up in time, the fuel margin is gone. It is expensive, and it is not
a failure — it is the correct answer when the alternative is circling until something
worse happens. Here it is the monitor's other fallback, for a flight this airport
cannot place at all.

The pair matters because they are **the only two values `POST /flag` accepts** — the
board refuses anything else with `bad_decision` — and because the `decision made`
verdict passes only if the stuck flight ended in one of them. **Doing nothing is not a
third option.** A flight left `pending` forever fails that check, and that is the whole
of SLO 6: decide something, say so, keep running.

### Places and things

| Word | What it is |
|---|---|
| **gate** | Where the aircraft parks. `G1`–`G6`. **One gate holds one flight, ever** — the board enforces it, you don't. At a real airport this is a *stand*; "gate" is the door the passengers walk through, and the two get used interchangeably. |
| **runway slot** | Permission to use the runway in a particular window. `R1`–`R4`. **One slot holds one flight, ever.** At a real airport ATC issues these, and missing yours means waiting for another; here it is simply an exclusive reservation. |
| **closed slot** | A runway taken out of service. `./inject close-runway` shuts `R3` and `R4`, evicts whoever held them, and every later claim on them comes back `slot_closed`. The board page shows it as `runway shut`. |
| **the tarmac** | The paved ground outside the gates. In this repo it is where a `held` flight waits — there is no tarmac in the data model, only the status. |
| **the board** | The one shared source of truth: which flight is at which gate, in which slot, and every decision ever made about it. There is exactly **one** for the team, and it is not on your laptop. The real-world equivalent is the ops board the whole ramp works from. **If it and your piece disagree, the board is right.** |
| **the feeds** | Live arrivals and departures. They overlap and repeat the same flight, because real feeds do; de-duplicating them is the board's job — that is `duplicate_merged` in the log, not an error. |
| **piece** · **service** · **role** | Used interchangeably here. A *piece* is one of the four programs; a *role* is the person who owns it. |

### A flight's facts

| Field | What it means |
|---|---|
| `id` | The flight number: airline code plus number. The feed uses real codes — `PK` Pakistan International, `EK` Emirates, `QR` Qatar, `TK` Turkish, `SV` Saudia, `AI` Air India, `BA` British Airways, `LH` Lufthansa, `PA` Pan Am — so the board reads like a real one. Nine flights, and three of them come down the feed twice. |
| `kind` | `arrival` or `departure`. Both need a gate and a slot; the difference is which end of the visit you are looking at. |
| `eta_min` | Minutes past the hour, **on the board's clock**. Not a wall-clock time. |
| `delay_min` | How far the harness has pushed this flight back. A delay of 60 minutes or more makes a flight miss its runway slot — **the slot opens up, the gate does not**, and that is what starts the cascade. |
| `decided_by` | Which piece made the last call on this flight. Your name ends up in here, which is how a verdict can tell whose problem something is. |
| `reason` | The free text the monitor writes with a `held` or a `divert`. The one field that exists purely to be read by a human afterwards — so write it like someone will. |

One id is not in that feed: **`ZZ-999`**. The `no-gate` injection invents it on the day
as the flight with nowhere to go, so it is the flight the `decision made` verdict asks
you about. If you see it on the board, you are being tested.

### Time

The board keeps its own clock, and you read time from there.

| Word | What it means |
|---|---|
| **board-minute** | The board's unit of time. **One board-minute per six real seconds** — so a 20-board-minute timeout fires after two real minutes. |
| **the board clock** | `GET /now`. Read time from here, never from `datetime.now()`. |
| **clock skew** | `./inject bad-clock` jumps the board clock 47 minutes forward. A piece keeping its own clock will not even notice, which is exactly the point. |
| **"timeout"** | **Two different things share this word.** The monitor's fallback timer is in *board-minutes* and is about deciding instead of hanging (SLO 6). The harness's HTTP budget is in *real seconds* and is about being reachable (SLO 4). Every budget is in one table under [Timing](#timing--every-budget-in-one-place). |

### What you'll read in `/log` and `/decisions`

The board writes a line for everything that happens, and on day 3 these lines are all
you get. Learn them on day 1.

| Event | What happened |
|---|---|
| `inbound` | The feed announced a flight the board had not seen before. |
| `duplicate_merged` | The feed announced one it already had. Normal. |
| `claim_ok` | An assigner took a gate. |
| `claim_rejected` | An assigner tried for a gate somebody else holds. **The board did not change.** |
| `slot_ok` · `slot_rejected` | The same two, for a runway slot. |
| `release_gate` | A gate was given back. That flight is `pending` again — somebody has to pick it up. |
| `fallback` | The monitor flagged a flight `held` or `divert`. |
| `delay` | The harness pushed a flight back. |
| `close_runway` | The harness shut runway slots and evicted whoever held them. |
| `clock_skew` | The harness moved the board clock. |

And the `actor` on each line — who did it:

`feed` · `assigner-A` and `assigner-B` · `replanner` · `monitor` · `HARNESS` (us, on
day 3 — sometimes `HARNESS-setup` or `HARNESS-rogue-assigner`) · and `?`, a write that
arrived with no actor at all. The name is whatever your piece passed to
`Board(actor=...)`, so if you ever see `?`, your own code is not sending one.

```bash
curl -s localhost:8080/log                          # the last 50, newest last
curl -s "localhost:8080/decisions?flight=PK-304"    # one flight's whole life, from SQLite
```

### When the board says no

Every write can be refused. A refusal comes back `409` when the write would have
broken a rule, `400` when the request itself was malformed, and `404` for a path that
does not exist — always with a `reason`, and these are the exact strings:

| `reason` | What it means |
|---|---|
| `gate_occupied` | Somebody holds that gate. The response also carries `holder`: the flight that has it. |
| `slot_occupied` | Somebody holds that runway slot. |
| `slot_closed` | That runway is shut. See `close-runway`. |
| `unknown_flight` | No flight with that id — a typo, or one the feed has not announced yet. |
| `unknown_gate` · `unknown_slot` | Not one of `G1`–`G6` · `R1`–`R4`. |
| `bad_decision` | You flagged something that is not `held` or `divert`. |
| `bad_json` | The body would not parse. |
| `missing_<field>` | A required field was absent — e.g. `missing_gate`. |
| `no_such_route` | Wrong path. The board's routes are listed in `CLAUDE.md`. |

**A 409 is not a log line, it is a fact:** somebody got there first and the board did
not move. See [The two hard rules](#the-two-hard-rules).

### The words we use for building it

One line each. The full version is wherever the link goes.

| Word | What we mean by it |
|---|---|
| **self-healing** | Not a system that never gets hit. One that takes the hit, says so, and keeps going. [SELF-HEALING.md](SELF-HEALING.md) |
| **retry on refusal** | What you do with the flight you did not place. Pattern 1 — the assigners'. |
| **damping** | A brake: at most one re-plan per flight per N board-minutes. Pattern 2 — the re-planner's. Needs a number, and the number goes in `contracts.md`. |
| **blast radius** | Which flights a delay *actually* touched. Pattern 3 — the re-planner's. If you cannot state it in one sentence, you are re-planning the whole board and calling it a strategy. |
| **timeout → fallback** | When you stop waiting, and what you choose instead. Pattern 4 — the monitor's. In board-minutes. |
| **split state** | Your piece and the board disagree about the world. Almost always a refused write that got recorded as a success. The verdict phrases it *"its state has split from the board's"*. |
| **injection** | A failure we cause on day 3, always through the board or the feeds, **never** by touching your code. `./inject late`, and four others. |
| **injection surface** | Why the board and the feeds arrive finished: they are the only two things your pieces can see, so changing what comes through them tests your build without editing it. |
| **verdict** | One of the five checks in `harness/verdict.py`. Each one reads the board and your `/state` and `/log` — never your source. |
| **scorecard** | The result of a run: `4/4  ++++`. Every one is recorded; `./inject history` shows them all. |
| **absent** | A piece the harness could not reach inside its budget. A piece running perfectly on your own laptop is absent to everyone else — see [My piece is running but scores as absent](#my-piece-is-running-but-scores-as-absent). |

### Real airport words you'll hear, and what we call them

People say these out loud in the room. Only the rows that map to something are in the
build — don't go looking in the code for the rest.

| You'll hear | In this repo |
|---|---|
| stand | **gate** — `G1`–`G6` |
| ATC slot, departure slot | **runway slot** — `R1`–`R4` |
| holding pattern, holding on the ground | the status **`held`** |
| diversion, divert to an alternate | the status **`divert`** |
| the ops board, the FIDS | **the board**, on `:8080` |
| cascade, knock-on delay | what `./inject late` causes |
| runway closure, ground stop | `./inject close-runway` |
| apron, ramp, taxiway | not modelled — a flight is at a gate or it isn't |
| turnaround, pushback, off-blocks | not modelled — a gate is held until somebody releases it |
| load control, weight and balance | not modelled |
| MCT, misconnect, passenger connections | not modelled — these flights carry no passengers |
| de-icing, catering, fuelling | not modelled |

Everything marked *not modelled* is out on purpose — see
[Scope](#scope--what-we-model-and-what-we-dont).
