# M4 vision replay foundation

This is the first executable slice of the existing V12–V25 vision roadmap, not a finished player recognizer. It adds a recorded-video adapter with timestamps and a deterministic camera-cut gate. A hard cut should reset future ByteTrack tracklets; canonical player identities should be reacquired using team + jersey evidence, not propagated by bounding-box association.

## macOS setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy opencv-python
python -m unittest discover -s services/vision -p 'test_*.py'
python -m services.vision.replay --input /path/to/authorized-game.mp4 --output artifacts/vision/cuts.jsonl
```

The output is JSON Lines containing source frame index, timestamp, shot ID, candidate camera-cut flag, and histogram distance. Tune the threshold on labeled camera cuts. Fast pans, graphic wipes, replays, and lighting changes can trigger false positives; similar-looking camera views can produce false negatives.

## Next implementation gates

1. Add a YOLO26n detector adapter using PyTorch MPS and benchmark Core ML on the actual M4 variant. Detect players and officials; keep detector/model version in logs.
2. Add a ByteTrack adapter that resets on shot changes. Measure identity switches *within* shots.
3. Add asynchronous jersey crop/number recognition and temporal voting; resolve only against the fantasy roster, with unknown/abstention as the default.
4. Add a bounded latest-frame queue, metrics, and a replay-to-extension marker transport. Use an authorized live capture source; DRM-protected video is not a supported capture path.

Do not label detected people with fantasy player names until identity evidence is calibrated. The current code does not perform inference or live capture.
