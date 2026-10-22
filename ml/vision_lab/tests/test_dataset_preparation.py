import json
from pathlib import Path

import pytest

import vision_lab.dataset_preparation as preparation
from vision_lab.dataset_preparation import (
    ShotRange,
    build_shot_ranges,
    ffmpeg_clip_command,
)
from vision_lab.smoke import make_smoke_video


def test_builds_contiguous_inclusive_shot_ranges() -> None:
    assert build_shot_ranges(10, (3, 7)) == (
        ShotRange(0, 0, 2),
        ShotRange(1, 3, 6),
        ShotRange(2, 7, 9),
    )
    assert [shot.frame_count for shot in build_shot_ranges(10, (3, 7))] == [3, 4, 3]


@pytest.mark.parametrize("cuts", [(0,), (10,), (7, 3), (3, 3)])
def test_rejects_invalid_cut_boundaries(cuts: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        build_shot_ranges(10, cuts)


def test_ffmpeg_uses_frame_exact_trim_without_a_shell() -> None:
    command = ffmpeg_clip_command(
        Path("source.mp4"), Path("clip.mp4"), ShotRange(1, 9, 123)
    )
    assert command[0] == "ffmpeg"
    assert "trim=start_frame=9:end_frame=124,setpts=PTS-STARTPTS" in command
    assert command[-1] == "clip.mp4"


def test_preparation_manifest_preserves_every_source_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_smoke_video(tmp_path / "source.mp4", frame_count=10)
    shots = tmp_path / "shots.jsonl"
    shots.write_text(
        "\n".join(
            json.dumps({"frame_index": frame, "camera_cut": frame in {3, 7}})
            for frame in range(10)
        )
        + "\n"
    )

    def fake_encode(source_path, destination, shot, *, ffmpeg):
        destination.write_bytes(f"shot-{shot.shot_id}".encode())

    monkeypatch.setattr(preparation.shutil, "which", lambda _: "/test/ffmpeg")
    monkeypatch.setattr(preparation, "_encode_clip", fake_encode)
    summary = preparation.prepare_shot_clips(source, shots, tmp_path / "prepared")

    assert [clip.frame_count for clip in summary.clips] == [3, 4, 3]
    assert sum(clip.frame_count for clip in summary.clips) == 10
    assert all(len(clip.sha256) == 64 for clip in summary.clips)
    assert Path(summary.manifest).exists()
