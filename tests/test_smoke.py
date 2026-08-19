"""One example test, so you have something to copy. The rest are YOURS.

    python -m unittest discover -v

This one needs no server — it drives the board object directly, which is the
fastest way to test a rule. Your pieces will need the other kind too: stand the
board up, point your piece at it, and assert on what it did.

SLO 5 — write a test for your piece and use it to catch a problem BEFORE
        everything is joined up.
SLO 7 — every failure you hit on day 2 becomes a test here, so it cannot
        come back the same way.
"""
import unittest

from board.state import Board, Rejected


class TestTheTwoHardRules(unittest.TestCase):
    def setUp(self):
        self.b = Board()
        for f in ("PK-304", "EK-621"):
            self.b.upsert(f, "arrival", 10)

    def test_one_gate_holds_one_flight(self):
        self.assertTrue(self.b.claim_gate("PK-304", "G1", "test"))
        with self.assertRaises(Rejected) as caught:
            self.b.claim_gate("EK-621", "G1", "test")
        self.assertEqual(caught.exception.reason, "gate_occupied")
        self.assertEqual(caught.exception.holder, "PK-304")
        self.assertEqual(self.b.gates["G1"], "PK-304")      # board did not move

    def test_a_flight_holds_at_most_one_gate(self):
        self.b.claim_gate("PK-304", "G1", "test")
        self.b.claim_gate("PK-304", "G2", "test")           # moving is allowed
        self.assertIsNone(self.b.gates["G1"])               # and G1 is freed
        self.assertEqual(self.b.gates["G2"], "PK-304")

    def test_a_closed_slot_refuses_everything(self):
        self.b.close_runway(["R3"])
        with self.assertRaises(Rejected) as caught:
            self.b.claim_slot("PK-304", "R3", "test")
        self.assertEqual(caught.exception.reason, "slot_closed")

    def test_duplicates_from_the_feed_collapse(self):
        self.assertFalse(self.b.upsert("PK-304", "arrival", 10))   # already known
        self.assertEqual(len([f for f in self.b.flights if f == "PK-304"]), 1)


class TestTheFallback(unittest.TestCase):
    """The monitor's job: a decision, not a hang."""

    def setUp(self):
        self.b = Board()
        self.b.upsert("ZZ-999", "arrival", 5)

    def test_a_stuck_flight_can_be_held(self):
        self.b.flag("ZZ-999", "held", "no gate for 12 min")
        self.assertEqual(self.b.flights["ZZ-999"].status, "held")
        self.assertEqual(self.b.flights["ZZ-999"].reason, "no gate for 12 min")

    def test_the_fallback_must_be_a_real_decision(self):
        with self.assertRaises(Rejected):
            self.b.flag("ZZ-999", "maybe_later", "hmm")


if __name__ == "__main__":
    unittest.main()
