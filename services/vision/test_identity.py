import pytest

from identity import Detection, RosterCandidate, resolve_detection


ROSTER = [
    RosterCandidate("1", "Example Receiver", "SF", 11),
    RosterCandidate("2", "Example Quarterback", "SF", 13),
    RosterCandidate("3", "Other Receiver", "SEA", 11),
]


def test_team_and_jersey_resolve_one_player():
    marker = resolve_detection(
        Detection(10, 20, 30, 80, 0.8, team="SF", jersey_number=11), ROSTER
    )

    assert marker is not None
    assert marker.player_id == "1"
    assert marker.confidence == pytest.approx(0.87)
    assert marker.evidence == ("detector=0.80", "team=SF", "jersey=11")


def test_ambiguous_detection_stays_unidentified():
    assert resolve_detection(Detection(10, 20, 30, 80, 0.9), ROSTER) is None


def test_low_confidence_detection_is_suppressed():
    assert resolve_detection(
        Detection(10, 20, 30, 80, 0.4, team="SF", jersey_number=11), ROSTER
    ) is None
