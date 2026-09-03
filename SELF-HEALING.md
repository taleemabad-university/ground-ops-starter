# The four healing patterns

Read this on day 1, before you build anything. It is four questions, not four
snippets. **Nobody is going to hand you the code for these** — working out the
answer for your own piece *is* the build.

A self-healing system is not one that never gets hit. It is one that takes the hit,
says so, and keeps going. Every one of the failures we inject on day 3 is survivable
by a piece that has answered its question below, and fatal to a piece that hasn't.

---

## 1 · Retry on refusal — the assigners

**The question:** a 409 means somebody claimed it first and *the board did not
change*. What happens to the flight you did not place?

Every write to the board can be refused. `board.claim()` hands back `(ok, reason)`.
If you take the refusal as a log line and carry on, your piece now believes it owns
a gate it does not own — and the flight it "placed" is sitting nowhere, with nobody
looking for it. The board is fine. Your picture of it is not.

Decide, and write it in `contracts.md`:

- Do you retry immediately, or next tick? (Immediately just loses the same race
  again — think about why.)
- How many times before you stop and say something?
- Between losing and retrying, what does your `/state` say about that flight?

**Fails without it:** `no double-book`, `no silent loss`. This is the race.

## 2 · Damping — the re-planner

**The question:** how often may one flight be re-planned? Give a number, in
board-minutes.

Your changes go onto the board. The board changing looks like something happened.
Something happening is what makes you re-plan. That is a loop with no brake, and on
day 3 we hand you a clock that is 47 minutes fast so *every* flight looks late at
once. The piece whose whole job is to fix the board is the piece most likely to melt
it.

Damping is the brake: at most one re-plan per flight per N board-minutes. **Pick N
and write it in `contracts.md`** — the board settling is one of the five things we
score, so if N isn't written down nobody can tell whether a runaway is a bug or the
behaviour you agreed on.

**Fails without it:** `board converges`. This is the runaway.

## 3 · Blast radius — the re-planner

**The question:** one flight slipped. Which flights did that *actually* touch?

The lazy answer is "all of them", and it works right up until it doesn't: every
unnecessary write is another chance to fight an assigner for a gate nobody asked you
to move. The useful answer is a rule you can state — the flights behind it on the
same gate, the ones whose slot it now overlaps, and stop there.

Write the rule down. If you can't state it in one sentence, you are re-planning the
whole board and calling it a strategy.

**Fails without it:** `board converges`, and it makes the race worse for everyone.

## 4 · Timeout → fallback — the monitor

**The question:** nothing has opened up. When do you stop waiting, and what do you
choose?

Waiting forever is the same as crashing, except harder to notice. On day 3 a flight
arrives and **no gate ever opens** — there is no right answer available, so the
right behaviour is to make a call anyway: `board.flag(flight, "held", reason)` or
`"divert"`. A safe backup beats hanging, every time.

**Say the timeout in board-minutes.** The board's clock runs one minute per six real
seconds, so a timeout you wrote in wall-clock seconds will never fire inside the
window we test in. This has caught every cohort so far.

> **Two different timeouts, don't mix them up.** *This* one — the monitor's fallback
> timer — is in **board-minutes** and is about deciding instead of hanging. The
> *harness* also has a timeout: a **real-seconds** budget for your `/state` to answer,
> which is about being reachable. See "Timing" in the README.

**Fails without it:** `decision made`. This is the dead end.

---

## What already heals, before you write anything

Three things you were given. Know them, so you can tell what you're standing on from
what you still have to build:

| | What it does | See it |
|---|---|---|
| **The board restores itself** | Every flight and decision is in SQLite. Restart the board and it comes back — the host can reboot without wiping the team's afternoon. | `./run` prints `restored N flights from board.db` |
| **The lock refuses double-books** | One gate holds one flight, one slot holds one flight. Ever. Enforced under one lock, so two assigners cannot both win. | `curl -s localhost:8080/log` — the `claim_rejected` lines |
| **The board restarts on failure** | `railway.toml` sets `restartPolicyType = "ON_FAILURE"`, 3 retries. Process-level only. | Deployed board only |

Notice what is *not* in that list: nothing that handles a refusal for you, nothing
that damps anything, nothing that decides about a stuck flight. **That is your
four.**

---

## Checking yourself

`./inject verdict` scores the board as it stands. `./inject history` shows every run
so far, so you can see whether a change actually helped or just moved the problem:

```
2026-09-03 09:14:02  2/4  .+.+    04 · the runaway
2026-09-03 11:40:55  4/4  ++++    04 · the runaway
```

Ask Claude to audit one piece against these four with the `self-healing-review`
skill — see [.claude/skills/](.claude/skills/).
