from pathlib import Path

from vision_lab.cvat_annotations import load_cvat_ground_truth, validate_cvat


def _write_xml(path: Path) -> None:
    path.write_text(
        """<annotations>
<meta><job><size>4</size></job><original_size><width>100</width><height>80</height></original_size></meta>
<track id="7" label="player" source="manual">
  <box frame="0" outside="0" xtl="1" ytl="2" xbr="11" ybr="22"><attribute name="team">home</attribute><attribute name="jersey_visible">true</attribute></box>
  <box frame="1" outside="1" xtl="1" ytl="2" xbr="11" ybr="22" />
  <box frame="2" outside="0" xtl="2" ytl="3" xbr="12" ybr="23"><attribute name="team">home</attribute><attribute name="jersey_visible">false</attribute></box>
</track>
</annotations>\n"""
    )


def test_load_cvat_uses_one_based_frames_and_ignores_outside(tmp_path: Path):
    path = tmp_path / "annotations.xml"
    _write_xml(path)
    records = load_cvat_ground_truth(path)
    assert [record.frame for record in records] == [1, 3]
    assert records[0].identity == 7
    assert records[0].category == "player"


def test_validate_cvat_reports_gaps_and_empty_frames(tmp_path: Path):
    path = tmp_path / "annotations.xml"
    _write_xml(path)
    report = validate_cvat(path)
    assert report.track_count == 1
    assert report.visible_box_count == 2
    assert report.empty_frames == [1, 3]
    assert report.tracks_with_internal_visibility_gaps == 1
    assert report.player_team_values == {"home": 2}
