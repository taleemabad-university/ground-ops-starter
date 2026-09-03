# Day 1 — understand it before you build it

**Nobody writes a service today.**

That is deliberate. Last time round, teams who were good at this went straight to
building and spent the back half discovering they had been solving the wrong
problem. Today
you run the thing we gave you, watch it break, and agree what you are each
promising the others. Tomorrow you build.

Every command below works on any machine:

```
python run.py <args>
```

If your team is on mac or linux you can use `./run <args>` instead; on Windows
`.\run.cmd <args>`. When in doubt use `python run.py` — it works in every shell.

**Done when:** every person can explain the problem in their own words,
`contracts.md` is filled in, and the deployed board is reachable by all five of you.

---

## 1 · Run it and watch it

Everyone, on their own laptop:

```
python run.py
```

Then open <http://localhost:8080/> and **watch it for two minutes without touching
anything.** Flights arrive. Gates fill. The pieces report themselves as answering.

> **Answer as a team:** what is the board actually deciding, and what happens to a
> flight between arriving and being parked?

Right now you are each running your own private airport. That is fine today. From
tomorrow there is one board for the team — see step 6.

## 2 · Follow one flight all the way through

The board keeps every decision it has ever made. Pick one flight and read its life:

```
curl -s "localhost:8080/decisions?flight=PK-304"
curl -s localhost:8080/log
```

> **Answer as a team:** who decided PK-304's gate — and how would you find out, from
> the board alone, if two pieces disagreed about it?

This is the tool you use on day 3 to work out whether a failure is yours or
upstream. Learn it now, while nothing is on fire.

## 3 · Read what is wrong with your piece

Open the file for the role you are taking and **read the header comment**:

| Role | File |
|---|---|
| assigner A / assigner B | `assigners/naive.py` |
| re-planner | `replanner/naive.py` |
| monitor | `monitor/naive.py` |
| board keeper | `board/api.py` and `harness/verdict.py` — what you will be holding people to |

Each header says exactly what is wrong with the version that ships, and which
outcome it costs you. **What is in there runs, and it is wrong.** That is your
starting point, not your answer.

> **Say out loud, each person in turn:** what my piece does, what is wrong with it,
> and what that will cost us when it gets broken.

If you cannot say it in your own words, do not move on. This is the step that was
missing last time.

## 3b · Read the four healing patterns

Everyone reads [SELF-HEALING.md](SELF-HEALING.md). It is four questions, one per
pattern, and each maps to a failure that gets injected on day 3:

| Pattern | Whose | Fails without it |
|---|---|---|
| Retry on refusal | assigners | the race |
| Damping | re-planner | the runaway |
| Blast radius | re-planner | the runaway |
| Timeout → fallback | monitor | the dead end |

It also names the three things the repo **already** heals for you, so you can tell
what you're standing on from what you have to build.

> **Answer, each person:** which of the four is mine, and what is my answer to its
> question? You don't need the code today — you need the answer, because it goes in
> `contracts.md` in step 5.

## 4 · Break it, and do not fix it

```
python -m harness.inject late
```

A flight runs ninety minutes late and keeps its gate. Watch the board page while it
lands.

> **Answer as a team:** which pieces had to do something about that, in what order?
> Which one would you blame first, and how would you check?

Then run one more:

```
python -m harness.inject race
```

Two claims hit the last free gate at the same instant. The board refuses one. Watch
what the losing assigner does about it — the answer is *nothing*, and that is the
bug you will fix tomorrow.

**Do not fix anything today.** You are here to recognise these when they come back
on day 3.

Both runs were recorded. Have a look:

```
python -m harness.inject history
```

Every scorecard from now until the demo lands in that list. It is how you tell a fix
that worked from a fix that moved the problem somewhere else.

## 5 · Write the contracts

Open [contracts.md](contracts.md) and fill it in **together**. It tells you which
rows belong to which person — nobody fills it in alone, and no row is left to "the
team".

Budget a real hour. The three things people skip and regret:

- **The refusal column.** What each writer actually does when the board says no.
- **The re-planner's damping rule**, with a number in it.
- **The monitor's timeout, in board-minutes** — not seconds.

> **You do not leave day 1 until every row has something in it.**

## 6 · Board keeper: put the board somewhere real

One board for the whole team, and it must not live on a laptop that sleeps.

The board keeper deploys it — `Procfile` and `railway.toml` are already in the repo
and the board respects `$PORT`, so it goes up as-is. Then:

1. Board keeper gives everyone the deployed address.
2. **Everyone** copies `team.env.example` to `team.env`, puts that address in
   `BOARD_URL`, and puts their own reachable address in their own line. Commit it.
3. Find your own address with:
   ```
   python run.py me
   ```
   `localhost` is not an address — it means "this machine", and a piece nobody can
   reach scores as absent.
4. Open the deployed board in a browser. Everyone's laptop should reach it.

> **Done when:** all five of you can load the same board page and see the same
> flights.

---

## End of day 1

- Every person can explain the problem, their piece, and what is wrong with it
- `contracts.md` is filled in, every row owned
- The board is deployed and everyone's `team.env` points at it

Not one line of your service is written. That is the correct state.

**Tomorrow:** build your piece to what you agreed. See the README.

Three skills ship in `.claude/skills/` and are worth knowing about before you start:
`failure-to-test`, `board-triage` and `self-healing-review`. Read them — they are
also the worked example for the skill you will write yourself by day 3.
