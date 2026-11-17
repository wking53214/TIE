"""Replay protection: one atomic claim, safe under contention, honest about durability."""

import json
import os
import threading
import warnings
from pathlib import Path

import pytest

from tie.evidence.herald_intake import (
    HandoffLedger,
    HeraldIntakeRefused,
    SeenHandoffs,
    record_handoff_once,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "herald_export_v4.json"
EXPORT = json.loads(_FIXTURE.read_text())["export"]
HID = EXPORT["identity"]["handoff_id"]


class FileLedger:
    """A durable ledger as a deployer might write one: an exclusive file create is the atomic step."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory

    def claim_once(self, handoff_id: str) -> bool:
        try:
            fd = os.open(self._dir / handoff_id, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        os.close(fd)
        return True


def _race(ledger, workers: int = 64) -> int:
    """How many of `workers` simultaneous attempts to take in the same export succeeded."""
    gate = threading.Barrier(workers)
    wins = []

    def attempt() -> None:
        gate.wait()
        try:
            record_handoff_once(EXPORT, ledger)
            wins.append(1)
        except HeraldIntakeRefused:
            pass

    threads = [threading.Thread(target=attempt) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return len(wins)


def test_in_memory_ledger_satisfies_the_protocol():
    assert isinstance(SeenHandoffs(), HandoffLedger)


def test_first_claim_wins_and_repeats_lose():
    ledger = SeenHandoffs()
    assert ledger.claim_once("hid-a") is True
    assert ledger.claim_once("hid-a") is False
    assert ledger.claim_once("hid-b") is True


def test_simultaneous_claims_cannot_both_succeed_in_memory():
    assert _race(SeenHandoffs()) == 1


def test_simultaneous_claims_cannot_both_succeed_on_a_durable_ledger(tmp_path):
    assert _race(FileLedger(tmp_path)) == 1


def test_a_durable_ledger_remembers_across_a_restart(tmp_path):
    record_handoff_once(EXPORT, FileLedger(tmp_path))
    restarted = FileLedger(tmp_path)  # a new object over the same storage
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        record_handoff_once(EXPORT, restarted)


def test_the_in_memory_ledger_forgets_across_a_restart():
    """Stated plainly because it is the durability boundary: this is why it is for tests and single-process tools."""
    record_handoff_once(EXPORT, SeenHandoffs())
    record_handoff_once(EXPORT, SeenHandoffs())  # a fresh ledger knows nothing


def test_a_ledger_that_fails_refuses_the_export():
    class Broken:
        def claim_once(self, handoff_id):
            raise OSError("disk full")

    with pytest.raises(HeraldIntakeRefused, match="replay ledger failed"):
        record_handoff_once(EXPORT, Broken())


@pytest.mark.parametrize("answer", [None, 1, "yes", 0])
def test_a_ledger_that_does_not_answer_true_or_false_refuses_the_export(answer):
    class Vague:
        def claim_once(self, handoff_id):
            return answer

    with pytest.raises(HeraldIntakeRefused, match="other than True or False"):
        record_handoff_once(EXPORT, Vague())


def test_failure_to_record_is_not_a_claim():
    """A ledger that failed must not have counted the ID, so a retry on a healthy ledger is not a replay."""
    calls = []

    class Flaky:
        def claim_once(self, handoff_id):
            calls.append(handoff_id)
            if len(calls) == 1:
                raise OSError("transient")
            return True

    flaky = Flaky()
    with pytest.raises(HeraldIntakeRefused):
        record_handoff_once(EXPORT, flaky)
    record_handoff_once(EXPORT, flaky)
    assert calls == [HID, HID]


def test_a_legacy_two_method_ledger_still_works_but_warns():
    class Legacy:
        def __init__(self):
            self.ids = set()

        def has_seen(self, handoff_id):
            return handoff_id in self.ids

        def record(self, handoff_id):
            self.ids.add(handoff_id)

    legacy = Legacy()
    with pytest.warns(DeprecationWarning, match="not atomic"):
        record_handoff_once(EXPORT, legacy)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(HeraldIntakeRefused, match="already taken in"):
            record_handoff_once(EXPORT, legacy)

