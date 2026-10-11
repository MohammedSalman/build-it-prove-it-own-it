"""The stale flag `wristband_mode` (Lab 13, part A5).

It has been off since the 2025 festival. v1 and v2 both still read it, and while it is
on, the gate lets every ticket in on every day. v2 is the version that will stay, so its
copy of the dead code has to go. v1 retires with its copy.
"""

import pytest

from ..helpers import SEED, app_client, switch_flag, use_database

MAYA_CODE = SEED["Maya"][1]     # a Friday ticket


def test_photo_v1_with_wristband_mode_on_admits_a_friday_ticket_on_saturday(tmp_path, monkeypatch, clock):
    # A photograph of the dead code path, so nobody has to guess what it did. This is
    # what flipping the flag on would do on every v1 server still running.
    db = use_database(tmp_path, monkeypatch, "expanded")
    switch_flag(db, "wristband_mode", True)
    clock.set("2026-10-10T18:00:00")    # Saturday
    with app_client("v1", clock) as v1:
        assert v1.post("/api/gate/scan", json={"code": MAYA_CODE}).status_code == 200


@pytest.mark.parametrize("shape", ["expanded", "contracted"])
def test_v2_no_longer_reads_wristband_mode(tmp_path, monkeypatch, clock, shape):
    # Target of part A5: fails on the kit, passes once v2's dead code is gone.
    db = use_database(tmp_path, monkeypatch, shape)
    switch_flag(db, "wristband_mode", True)
    clock.set("2026-10-10T18:00:00")    # Saturday
    with app_client("v2", clock) as v2:
        res = v2.post("/api/gate/scan", json={"code": MAYA_CODE})
    assert res.status_code == 409, "v2 still lets a Friday ticket in on Saturday when wristband_mode is on"
