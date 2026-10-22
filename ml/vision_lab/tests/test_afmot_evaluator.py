from pathlib import Path

from vision_lab.afmot_evaluator import (
    GroundTruth,
    Prediction,
    category_for_label,
    evaluate,
    intersection_over_union,
    load_afmot_ground_truth,
    load_predictions,
)


def truth(frame: int, identity: int, box, label="k1"):
    return GroundTruth(frame, identity, label, category_for_label(label), box)


def prediction(frame: int, track_id: int, box):
    return Prediction(frame, track_id, 0.9, box)


def test_loads_afmot_identity_from_eighth_column(tmp_path: Path):
    labels = tmp_path / "labels.txt"
    labels.write_text("k1\nref_1\n")
    gt = tmp_path / "gt.txt"
    gt.write_text("1,-1,10,20,30,40,1,2,1.0\n")
    records = load_afmot_ground_truth(gt, labels)
    assert records[0].identity == 2
    assert records[0].label == "ref_1"
    assert records[0].category == "official"
    assert records[0].box_xyxy == (10.0, 20.0, 40.0, 60.0)


def test_iou():
    assert intersection_over_union((0, 0, 10, 10), (5, 5, 15, 15)) == 25 / 175


def test_evaluation_counts_detection_and_fragmentation():
    ground_truth = [
        truth(1, 1, (0, 0, 10, 10)),
        truth(2, 1, (0, 0, 10, 10)),
        truth(1, 2, (20, 20, 30, 30), "ref_1"),
    ]
    predictions = [
        prediction(1, 10, (0, 0, 10, 10)),
        prediction(2, 11, (0, 0, 10, 10)),
        prediction(1, 99, (40, 40, 50, 50)),
    ]
    report = evaluate(ground_truth, predictions)
    assert report.true_positives == 2
    assert report.false_positives == 1
    assert report.false_negatives == 1
    assert report.recall_by_category == {"official": 0.0, "player": 1.0}
    assert report.ambiguous_ground_truth_identities == 0
    assert report.trackable_ground_truth_identities == 2
    assert report.approximate_id_switches == 1
    assert report.identities_with_fragmented_tracks == 1


def test_ambiguous_identity_labels_are_excluded_from_track_diagnostics():
    ground_truth = [
        truth(1, 1, (0, 0, 10, 10)),
        truth(1, 1, (20, 20, 30, 30)),
    ]
    predictions = [
        prediction(1, 10, (0, 0, 10, 10)),
        prediction(1, 11, (20, 20, 30, 30)),
    ]
    report = evaluate(ground_truth, predictions)
    assert report.ambiguous_ground_truth_identities == 1
    assert report.trackable_ground_truth_identities == 0
    assert report.mean_predicted_tracks_per_identity == 0.0


def test_predictions_are_sampled_onto_annotation_timebase(tmp_path: Path):
    predictions = tmp_path / "frames.jsonl"
    predictions.write_text(
        "\n".join(
            [
                '{"frame_index":0,"detections":[]}',
                '{"frame_index":1,"detections":[]}',
                '{"frame_index":2,"detections":[{"track_id":7,"confidence":0.9,"box_xyxy":[1,2,3,4]}]}',
            ]
        )
        + "\n"
    )
    records = load_predictions(
        predictions, max_frame=3, source_fps=30.0, annotation_fps=15.0
    )
    assert len(records) == 1
    assert records[0].frame == 2
