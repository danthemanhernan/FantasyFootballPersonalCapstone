from pathlib import Path

import pytest

from vision_lab.dataset_preparation import (
    ShotRange,
    build_shot_ranges,
    ffmpeg_clip_command,
)


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
