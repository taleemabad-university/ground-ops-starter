"""The five injected failures. GIVEN — this is exactly what we run on day 2.

    ./inject late            one flight runs 90 minutes late
    ./inject close-runway    a runway shuts and its slots disappear
    ./inject race            two claims land on the last free gate at once
    ./inject bad-clock       the board's clock jumps 47 minutes forward
    ./inject no-gate         a flight arrives and nothing ever opens up
    ./inject all             all five, in order, with a scorecard

READ THIS BIT — it is the whole design.

  We never touch your code. Not one line, not on day 2, not in the demo.

  Every injection goes through the two things WE gave you: the board and the
  feeds. Your pieces only ever see the world through those two doors, so we can
  change what comes through the doors and watch what your build does about it.
  That is why the board and the feeds are handed to you finished — they are not
  a favour, they are the injection surface.

  Which means: anything your piece assumes about the world, we can make untrue
  from the outside, without warning, in front of an audience. Handle the answers
  you get back from the board and none of this can hurt you.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request

from . import verdict

from board.config import BOARD_URL as BOARD


def post(path, payload):
    req = urllib.request.Request(f"{BOARD}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get(path):
    with urllib.request.urlopen(f"{BOARD}{path}", timeout=4) as r:
        return json.loads(r.read())


def say(msg):
    print(f"  ▸ {msg}", flush=True)


# ── 01 · the cascade ─────────────────────────────────────────────────────────
def inject_late():
    """One flight runs 90 minutes late — and it does not give its gate back."""
    snap = get("/board")
    gated = [f for f, v in snap["flights"].items() if v["gate"]]
    if not gated:
        say("nothing is on a gate yet — let it run a few seconds and try again")
        return None
    # prefer a flight that is holding a runway slot — losing it is what cascades
    with_slot = [f for f in gated if snap["flights"][f]["slot"]]
    victim = sorted(with_slot or gated)[0]
    _, body = post("/admin/delay", {"flight": victim, "minutes": 90})
    say(f"{victim} is now 90 min late and still sitting on {body.get('gate')}")
    if body.get("missed_slot"):
        say(f"it was too late for {body['missed_slot']} — that slot is now free, "
            f"and whoever was queued behind it has to be re-planned")
    say("the re-plan has to stay clean: touch what moved, and nothing else")
    return None


# ── 02 · the runway close ────────────────────────────────────────────────────
def inject_close_runway():
    """A runway shuts. Its slots are gone, and whoever held them is homeless."""
    # make sure the runway we are about to close is actually carrying flights,
    # otherwise closing it tests nothing at all
    snap = get("/board")
    for s in ("R3", "R4"):
        if snap["slots"].get(s):
            continue
        for fid, v in sorted(snap["flights"].items()):
            if v["gate"] and not v["slot"]:
                post("/slot", {"flight": fid, "slot": s, "actor": "HARNESS-setup"})
                snap = get("/board")
                break
    _, body = post("/admin/close-runway", {"slots": ["R3", "R4"]})
    evicted = body.get("evicted") or []
    say("R3 and R4 are closed and will refuse every claim from now on")
    say(f"evicted: {', '.join(evicted) if evicted else 'nobody was holding them'}")
    say("those flights must be MOVED, not quietly forgotten")
    return None


# ── 03 · the race ────────────────────────────────────────────────────────────
def inject_race():
    """Two claims on the last free gate, fired in the same instant.

    The harness plays the part of a competing assigner here. The board will hold
    the line — it always does. The question is whether YOUR assigner noticed
    that it was the one who lost.
    """
    snap = get("/board")
    free = [g for g, holder in sorted(snap["gates"].items()) if holder is None]
    waiting = [f for f, v in snap["flights"].items() if v["gate"] is None]
    if not free:
        # the assigners have filled the board — open exactly one gate so there is
        # something worth fighting over, which is the situation we care about
        gate = sorted(snap["gates"])[-1]
        post("/release", {"gate": gate, "actor": "HARNESS"})
        say(f"board was full — freed {gate} so there is one gate left to fight over")
        snap = get("/board")
        waiting = [f for f, v in snap["flights"].items() if v["gate"] is None]
    else:
        gate = free[-1]
    if len(waiting) < 2:
        say("need two waiting flights — let it run a few more seconds and try again")
        return None
    a, b = sorted(waiting)[:2]
    say(f"firing two claims at {gate} on the same tick: {a} and {b}")

    barrier = threading.Barrier(2)
    out = {}

    def fire(flight):
        barrier.wait()
        out[flight] = post("/claim", {"flight": flight, "gate": gate,
                                      "actor": "HARNESS-rogue-assigner"})

    ts = [threading.Thread(target=fire, args=(f,)) for f in (a, b)]
    [t.start() for t in ts]
    [t.join() for t in ts]

    winners = [f for f, (code, _) in out.items() if code == 200]
    losers = [f for f, (code, _) in out.items() if code != 200]
    say(f"board accepted {len(winners)} and refused {len(losers)} — as it should")
    say("now: does the losing side know it lost, or has its state quietly split?")
    return None


# ── 04 · the runaway ─────────────────────────────────────────────────────────
def inject_bad_clock():
    """The board's clock jumps forward. Suddenly every flight looks late."""
    post("/admin/skew", {"minutes": 47})
    say("board clock is now 47 minutes fast — every flight reads as overdue")
    say("an undamped re-planner will now re-plan, forever, as fast as it can")
    return None


# ── 05 · the dead end ────────────────────────────────────────────────────────
def inject_no_gate():
    """A flight arrives when there is nowhere to put it, and nowhere opens up."""
    snap = get("/board")
    free = [g for g, holder in snap["gates"].items() if holder is None]
    parked = [f"PARK-{i}" for i in range(len(free))]
    for name, gate in zip(parked, free):
        post("/admin/flight", {"flight": name, "kind": "arrival", "eta_min": 0})
        post("/claim", {"flight": name, "gate": gate, "actor": "HARNESS"})
    stuck = "ZZ-999"
    post("/admin/flight", {"flight": stuck, "kind": "arrival", "eta_min": 0})
    say(f"every gate is now full ({len(free)} parked by the harness)")
    say(f"{stuck} has arrived and there is nowhere for it to go")
    say("nothing will open up. something has to make a call instead of waiting")
    return stuck


SCENARIOS = {
    "late":          (inject_late,          "01 · the cascade",     14),
    "close-runway":  (inject_close_runway,  "02 · the runway close", 12),
    "race":          (inject_race,          "03 · the race",         10),
    "bad-clock":     (inject_bad_clock,     "04 · the runaway",      14),
    "no-gate":       (inject_no_gate,       "05 · the dead end",     22),
}


def run_one(key):
    fn, title, window = SCENARIOS[key]
    print(f"\n╭─ INJECTING {title}")
    try:
        get("/board")
    except Exception:
        print("╰─ the board is not up. start it with  ./run\n")
        sys.exit(1)
    baseline = verdict.rate(verdict.watch(3))          # how busy is it normally?
    print(f"│  baseline {baseline:.1f} board-writes/sec")
    flight = fn()
    print(f"╰─ watching for {window}s …")
    samples = verdict.watch(window)
    want = list(verdict.CHECKS) if flight else [k for k in verdict.CHECKS if k != "decision made"]
    return verdict.report(title, verdict.run(samples, want, flight, baseline))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("  scenarios:", ", ".join(SCENARIOS), "| all | verdict")
        return 0
    cmd = argv[0]
    if cmd == "verdict":
        return 0 if verdict.report("board right now", verdict.run(verdict.watch(4))) else 1
    if cmd == "all":
        results = {k: run_one(k) for k in SCENARIOS}
        survived = sum(results.values())
        print("═" * 70)
        for k, ok in results.items():
            print(f"  {'SURVIVED' if ok else 'BROKE   '}  {SCENARIOS[k][1]}")
        print(f"\n  survived {survived}/5 injected failures")
        print("  almost nobody passes all five cold. that is the point.\n")
        return 0 if survived == 5 else 1
    if cmd not in SCENARIOS:
        print(f"unknown scenario: {cmd}\ntry: {', '.join(SCENARIOS)}, all, verdict")
        return 2
    return 0 if run_one(cmd) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
