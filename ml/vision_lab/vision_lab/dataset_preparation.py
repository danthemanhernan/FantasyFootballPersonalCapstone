from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .pipeline import inspect_video
from .shot_detection import load_shot_start_frames


@dataclass(frozen=True)
class ShotRange:
    shot_id: int
    start_frame: int
    end_frame: int

    @property
    def frame_count(self) -> int:
        return self.end_frame - self.start_frame + 1


@dataclass(frozen=True)
class PreparedClip:
    shot_id: int
    start_frame: int
    end_frame: int
    frame_count: int
    start_time_seconds: float
    end_time_seconds: float
    path: str
    sha256: str


@dataclass(frozen=True)
class PreparationSummary:
    source: str
    source_sha256: str
    source_fps: float
    source_frame_count: int
    shot_manifest: str
    shot_manifest_sha256: str
    output_directory: str
    clips: tuple[PreparedClip, ...]
    manifest: str


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_shot_ranges(
    frame_count: int, cut_start_frames: tuple[int, ...]
) -> tuple[ShotRange, ...]:
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if cut_start_frames != tuple(sorted(set(cut_start_frames))):
        raise ValueError("cut frames must be unique and strictly increasing")
    if any(frame <= 0 or frame >= frame_count for frame in cut_start_frames):
        raise ValueError("cut frames must fall inside the source after frame zero")

    starts = (0, *cut_start_frames)
    ends = (*cut_start_frames, frame_count)
    return tuple(
        ShotRange(shot_id, start, end - 1)
        for shot_id, (start, end) in enumerate(zip(starts, ends))
    )


def ffmpeg_clip_command(
    source: Path,
    destination: Path,
    shot: ShotRange,
    *,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    frame_filter = (
        f"trim=start_frame={shot.start_frame}:end_frame={shot.end_frame + 1},"
        "setpts=PTS-STARTPTS"
    )
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        frame_filter,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        str(destination),
    ]


def _encode_clip(
    source: Path, destination: Path, shot: ShotRange, *, ffmpeg: str
) -> None:
    subprocess.run(
        ffmpeg_clip_command(source, destination, shot, ffmpeg=ffmpeg), check=True
    )
    encoded = inspect_video(destination)
    if encoded.frame_count != shot.frame_count:
        raise RuntimeError(
            f"Encoded {destination.name} has {encoded.frame_count} frames; "
            f"expected {shot.frame_count}"
        )


def prepare_shot_clips(
    source: str | Path,
    shots_path: str | Path,
    output_dir: str | Path,
    *,
    ffmpeg: str = "ffmpeg",
) -> PreparationSummary:
    source_path = Path(source).resolve()
    shots_file = Path(shots_path).resolve()
    destination = Path(output_dir).resolve()
    ffmpeg_path = shutil.which(ffmpeg)
    if ffmpeg_path is None:
        raise RuntimeError(f"Could not find FFmpeg executable: {ffmpeg}")

    metadata = inspect_video(source_path)
    ranges = build_shot_ranges(
        metadata.frame_count, load_shot_start_frames(shots_file)
    )
    clips_dir = destination / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[PreparedClip] = []
    for shot in ranges:
        clip_name = (
            f"shot_{shot.shot_id:04d}_"
            f"f{shot.start_frame:06d}-f{shot.end_frame:06d}.mp4"
        )
        clip_path = clips_dir / clip_name
        _encode_clip(source_path, clip_path, shot, ffmpeg=ffmpeg_path)
        prepared.append(
            PreparedClip(
                shot_id=shot.shot_id,
                start_frame=shot.start_frame,
                end_frame=shot.end_frame,
                frame_count=shot.frame_count,
                start_time_seconds=round(shot.start_frame / metadata.fps, 6),
                end_time_seconds=round((shot.end_frame + 1) / metadata.fps, 6),
                path=str(clip_path.relative_to(destination)),
                sha256=file_sha256(clip_path),
            )
        )

    manifest_path = destination / "manifest.json"
    summary = PreparationSummary(
        source=metadata.path,
        source_sha256=file_sha256(source_path),
        source_fps=metadata.fps,
        source_frame_count=metadata.frame_count,
        shot_manifest=str(shots_file),
        shot_manifest_sha256=file_sha256(shots_file),
        output_directory=str(destination),
        clips=tuple(prepared),
        manifest=str(manifest_path),
    )
    manifest_path.write_text(json.dumps(asdict(summary), indent=2) + "\n")
    return summary
