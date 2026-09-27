from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    width: float
    height: float
    confidence: float
    team: str | None = None
    jersey_number: int | None = None


@dataclass(frozen=True)
class RosterCandidate:
    player_id: str
    name: str
    pro_team: str
    jersey_number: int | None = None


@dataclass(frozen=True)
class Marker:
    player_id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    confidence: float
    evidence: tuple[str, ...]


def resolve_detection(
    detection: Detection,
    roster: list[RosterCandidate],
    minimum_confidence: float = 0.65,
) -> Marker | None:
    """Resolve detector evidence to one roster identity or remain unknown."""
    if detection.confidence < minimum_confidence:
        return None

    candidates = roster
    evidence = [f"detector={detection.confidence:.2f}"]
    identity_confidence = detection.confidence

    if detection.team:
        candidates = [player for player in candidates if player.pro_team == detection.team]
        evidence.append(f"team={detection.team}")
        identity_confidence *= 0.9

    if detection.jersey_number is not None:
        candidates = [
            player for player in candidates if player.jersey_number == detection.jersey_number
        ]
        evidence.append(f"jersey={detection.jersey_number}")
        identity_confidence = min(0.99, identity_confidence + 0.15)

    if len(candidates) != 1:
        return None
    player = candidates[0]
    return Marker(
        player_id=player.player_id,
        label=player.name,
        x=detection.x,
        y=detection.y,
        width=detection.width,
        height=detection.height,
        confidence=identity_confidence,
        evidence=tuple(evidence),
    )
