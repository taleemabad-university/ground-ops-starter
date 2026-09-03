---
name: failure-to-test
description: Turn an injected ground-ops failure into a regression test. Use after ./inject breaks something — reproduces the failure, writes the minimal test in tests/, proves it fails before the fix and passes after. Covers the race, the runaway, the dead end, the cascade and the runway close.
---

# Failure → regression test

A failure you fixed without a test is a failure that comes back. This is the loop:
reproduce it, pin it with a test that fails, fix it, watch the test pass.

**Run the test before the fix.** A test written after the fix proves nothing — it has
never seen the bug. If it passes on the broken code, it is testing the wrong thing.

## The loop

### 1 · Name what actually broke

Read the scorecard, not your intuition. `./inject <scenario>` prints which of the
five checks failed and why:

```
FAIL  no double-book   assigner-B thinks PA-450 is on G4, board says TK-709
```

That sentence is the test. "Assigner B records a flight as placed after the board
refused the claim."

If you are not sure the failure is yours, stop and use the `board-triage` skill
first. Do not write a test for someone else's bug.

### 2 · Find the smallest thing that reproduces it

Two kinds of test, and the cheap one is usually enough:

**Drive the board object directly** — no server, milliseconds, no flakiness. This is
how `tests/test_smoke.py` works and it is the right default:

```python
from board.state import Board, Rejected

b = Board()
b.upsert("PK-304", "arrival", 10)
b.claim_gate("PK-304", "G1", "test")
# now assert what your piece should do when this raises Rejected
```

**Stand the board up and point your piece at it** — only when the bug is in *how
your piece reacts over time* (a timer firing, a retry on the next tick, a rate
limit). Slower and can flake; use it when you must.

Prefer to test **your piece's decision function** over its loop. If the decision
lives inside a `while True:`, that is a hint to pull it into a function you can call
with a board state and assert on the result. That refactor is usually the real fix.

### 3 · Write it so it fails

Put it in `tests/`, named for the failure, with a docstring saying which injected
scenario it came from:

```python
class TestRefusedClaimIsNotRecorded(unittest.TestCase):
    """From ./inject race — assigner recorded a flight the board refused.

    Board said 409. The piece marked it placed anyway, so its /state split from
    the board and the flight was lost with nobody looking for it.
    """
```

Run it against the **unfixed** code and confirm it fails:

```
python -m unittest tests.test_race -v
```

If it passes, the test does not reproduce the bug. Go back to step 2.

### 4 · Fix, then confirm

Fix the piece. Run the test — it should pass. Then run the whole suite so you did not
trade one bug for another, and re-run the scenario end to end:

```
python -m unittest discover
./inject race
./inject history          # did the number actually move?
```

`./inject history` is the honest check. If the scenario's score did not improve, you
fixed something else.

## Rules for this repo

- **Never edit `board/`, `feeds/` or `harness/`** to make a test pass. They are given
  and they are the injection surface. If a test seems to need a change in there, the
  test is wrong.
- **Standard library only.** `unittest`, not pytest. No dependency, ever.
- **Timeouts in board-minutes**, never wall-clock seconds. Board time runs one minute
  per six real seconds, so `time.sleep(90)` in a test is both wrong and slow. Read
  the clock from the board.
- **Never hardcode a host or port.** Addresses come from `team.env` via
  `board/config.py`.
- One test per failure. Do not fold three scenarios into one test method — when it
  goes red you want to know which failure came back.

## The five, and what each one is really testing

| Scenario | The check it fails | What the test should pin |
|---|---|---|
| `race` | `no double-book`, `no silent loss` | A refused claim is not recorded as placed |
| `runaway` (`bad-clock`) | `board converges` | One flight cannot be re-planned more than N board-minutes apart |
| `dead end` (`no-gate`) | `decision made` | A flight with nowhere to go gets held or diverted, not left hanging |
| `cascade` (`late`) | `no silent loss` | A flight that loses its gate ends up somewhere or gets a decision |
| `close-runway` | `no silent loss` | Flights evicted from a closed slot are moved, not dropped |
