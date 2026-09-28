# Vision model and runtime candidates

This is a practical comparison of the vision candidates considered for the
Fantasy Football HUD as of September 2026. A “public example” below means an
officially documented project, benchmark, or demo—not proof that a commercial
product uses the model internally.

Benchmark numbers across repositories are not directly comparable. Input
resolution, hardware, numerical precision, preprocessing, and datasets differ.
Benchmark finalists on the same NFL broadcast corpus and target hardware.

## Detection and model-assisted labeling

| Candidate | What it is good for | When it is used | Main drawbacks | Public application or example | Documentation |
|---|---|---|---|---|---|
| **YOLO26** | Fast closed-set player, official, ball, helmet, and jersey-region detection. Also supports segmentation, pose, depth, classification, and oriented boxes. | The live inference hot path when classes are known and a practical accuracy/latency balance is required. | Must be fine-tuned for broadcast football. Small and occluded players remain difficult. AGPL-3.0 may require an enterprise license for a closed-source product. | Ultralytics custom real-time detection and export pipeline; exports to ONNX, TensorRT, CoreML, OpenVINO, and other targets. | [YOLO26 docs](https://docs.ultralytics.com/models/yolo26), [paper](https://arxiv.org/abs/2606.03748) |
| **YOLOE-26** | Open-vocabulary detection and segmentation using text or visual prompts—for example, “football player,” “referee,” “helmet,” or “scoreboard.” | Dataset exploration, annotation bootstrapping, new-class discovery, and prototypes where categories change dynamically. | Prompt sensitivity and weaker predictability than a fine-tuned closed-set detector. Usually not the final production model. Same Ultralytics licensing consideration. | Interactive text-prompted object discovery through the Ultralytics model pipeline. | [YOLOE documentation](https://docs.ultralytics.com/models/yoloe), [YOLO26 overview](https://docs.ultralytics.com/models/yolo26) |
| **RT-DETRv3** | End-to-end, NMS-free transformer detection with strong real-time performance. A useful alternative to YOLO-style detectors. | When cleaner end-to-end detection semantics are desired and transformer inference can be benchmarked on the target GPU. | Training and customization are less turnkey than Ultralytics. Deployment support is less polished in the official repository. | Official COCO and LVIS real-time detection models; the repository reports TensorRT FP16 results for its ResNet variants. | [RT-DETRv3 repository](https://github.com/clxia12/RT-DETRv3), [paper](https://arxiv.org/abs/2409.08475) |
| **D-FINE** | Precise box localization, especially in crowded scenes, small objects, blurred boundaries, and difficult lighting. | A strong accuracy-oriented benchmark for players packed around the line of scrimmage. | Larger variants may be too heavy for live edge inference. Its ecosystem is smaller than YOLO's. | Official dense street-scene demo covers crowds, motion blur, backlighting, and small objects. Supports ONNX and TensorRT export. | [D-FINE repository](https://github.com/Peterande/D-FINE), [paper](https://arxiv.org/abs/2410.13842) |
| **Grounding DINO 1.5** | Powerful open-world detection and phrase grounding. Good at locating objects described in natural language. Pro and Edge variants target capability and efficiency respectively. | Offline annotation, class discovery, hard-example mining, and quickly testing whether a visual concept can be detected. | The official 1.5 implementation is API-oriented. It introduces network latency, cost, and external-service dependence. Too unpredictable for the primary frame-by-frame loop. | IDEA Research's DeepDataSpace API and official Gradio application for text-grounded detection. | [Grounding DINO 1.5 API](https://github.com/IDEA-Research/Grounding-DINO-1.5-API) |

### Detection recommendation

Start with **YOLO26n or YOLO26s** as the baseline and train it for:

```text
player
official
football
helmet
jersey-number-region
```

Then benchmark **RT-DETRv3-R18** and a small **D-FINE** variant against the same
game-level test split. Do not select a model from COCO scores alone. Measure
small-player recall, crowded-player recall, latency, and false detections on NFL
broadcast shots.

Use YOLOE-26 or Grounding DINO for annotation and discovery, not as the first
production detector.

## Segmentation, tracking, and identity evidence

| Candidate | What it is good for | When it is used | Main drawbacks | Public application or example | Documentation |
|---|---|---|---|---|---|
| **SAM 2** | Promptable image and video segmentation. Propagates object masks through video using temporal memory. | Annotation tools, player-mask generation, occlusion analysis, and creating better training data. Potentially useful for selected high-value tracks. | Usually too expensive to segment every player on every live frame. Masks do not provide player identity. | Meta's official multi-object video predictor propagates prompted masks through a video. | [SAM 2 repository](https://github.com/facebookresearch/sam2), [paper](https://arxiv.org/abs/2408.00714) |
| **CoTracker3** | Dense point tracking, including visibility and occlusion behavior. Supports online and offline modes. | Field-line tracking, camera-motion estimation, marker stabilization, and difficult-occlusion research. | Tracks points, not semantic player identities. GPU use is strongly recommended, and dense tracking can be costly. | Meta's official online tracking demo and public Hugging Face Space. | [CoTracker repository](https://github.com/facebookresearch/co-tracker), [paper](https://arxiv.org/abs/2410.11831) |
| **ByteTrack** | Fast, simple multi-object tracking that associates high- and lower-confidence detections. Often preserves tracks through partial occlusion better than discarding weak boxes. | The best initial box tracker after player detection. A good baseline for stable real-time track IDs. | No native appearance-based re-identification; similar-looking players can swap IDs after longer occlusions. | Official YOLOX + ByteTrack MOT demo, with ONNX Runtime, TensorRT, NCNN, and DeepStream deployment examples. | [ByteTrack repository](https://github.com/FoundationVision/ByteTrack), [paper](https://arxiv.org/abs/2110.06864) |
| **BoT-SORT** | Combines motion, appearance re-identification, and camera-motion compensation. | Broadcast footage with frequent panning, zooming, occlusion, and players crossing each other. | More components and tuning than ByteTrack. ReID adds compute, while similar football uniforms weaken appearance evidence. | Official MOT17 and MOT20 multi-pedestrian tracking implementation and demonstrations. | [BoT-SORT repository](https://github.com/NirAharon/BoT-SORT), [paper](https://arxiv.org/abs/2206.14651) |
| **OC-SORT** | Observation-centric online tracking robust to non-linear motion and temporary occlusion. | When acceleration, abrupt direction changes, or poor motion prediction fragments a basic tracker. | Does not solve long-term identity or visually identical uniforms. Detection and identity evidence are still required. | Official DanceTrack and MOTChallenge demos; DanceTrack is relevant because subjects have similar appearance and complex motion. | [OC-SORT repository](https://github.com/noahcao/OC_SORT), [paper](https://arxiv.org/abs/2203.14360) |
| **SoccerNet jersey-recognition pipeline** | Jersey-number recognition from player tracklets, using evidence across many frames rather than one OCR crop. | After tracking has produced stable player tracklets. Used to infer number probabilities and an explicit “not visible” state. | Soccer footage differs from NFL footage. NFL-specific data, shoulder/front/back crops, and separate one- and two-digit handling will be needed. | SoccerNet Jersey Number Recognition Challenge; explicitly targets player labels, statistics, tracking, analysis, and broadcast overlays. | [SoccerNet JNR repository](https://github.com/SoccerNet/sn-jersey), [dataset](https://www.soccer-net.org/data) |

### Tracking recommendation

Use the following progression:

1. **ByteTrack** as the baseline.
2. Test **BoT-SORT** if camera pans and occlusions create ID switches.
3. Test **OC-SORT** if abrupt player motion breaks the motion model.
4. Use **CoTracker3** experimentally for field geometry and marker stabilization.
5. Use **SAM 2** primarily for annotation and debugging.

For identity, aggregate evidence over an entire track:

```text
team probability
+ jersey-number probability over multiple frames
+ roster eligibility
+ on-field lineup
+ field position
+ play-by-play participation
+ previous track identity
= identity belief
```

The output must include `unknown`. Hiding a marker is preferable to labeling the
wrong player.

## Deployment runtimes and video infrastructure

These are execution and orchestration technologies, not competing recognition
models.

| Candidate | What it is good for | When it is used | Main drawbacks | Public application or example | Documentation |
|---|---|---|---|---|---|
| **ONNX Runtime** | Portable inference across CPU, NVIDIA, AMD, DirectML, CoreML, mobile, WebGPU, and other execution providers. | The first deployment target when the same exported model should run on a laptop, server, browser experiment, or different accelerator. | Peak NVIDIA performance may require TensorRT. Unsupported or custom operators can complicate export. | Microsoft documents ONNX Runtime use across Office, Azure, and Bing, plus mobile and browser object-detection examples. | [ONNX Runtime docs](https://onnxruntime.ai/docs/) |
| **TensorRT** | Maximum optimized inference performance on supported NVIDIA GPUs, including mixed precision and INT8 quantization. | After the model is correct and profiling shows inference is a bottleneck. Appropriate for an NVIDIA workstation or server. | NVIDIA-only, greater deployment complexity, engine compatibility concerns, and possible quantization accuracy loss. Jetson compatibility depends on JetPack and TensorRT versions. | Common optimization backend for YOLO, D-FINE, ByteTrack detector pipelines, and DeepStream applications. | [TensorRT documentation](https://docs.nvidia.com/deeplearning/tensorrt/latest/index.html) |
| **NVIDIA DeepStream** | Complete streaming-video pipelines: decoding, batching, inference, tracking, metadata, message brokers, and multi-stream operation. | When moving from a notebook into a continuously running NVIDIA video-analytics service, especially with multiple feeds. | Platform coupling, GStreamer complexity, and a steeper debugging curve. Excessive for the first prototype. | NVIDIA's configurable `deepstream-app` combines video sources, object detection, classification, and tracking. | [DeepStream 8 overview](https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Overview.html) |

## Recommended project stack by phase

| Phase | Recommended stack | Goal |
|---|---|---|
| Annotation | Grounding DINO or YOLOE-26 + SAM 2 | Rapidly create and correct player, official, and jersey-region labels. |
| First live baseline | YOLO26n/s + ByteTrack + ONNX Runtime | Get a measurable detector and tracker running quickly. |
| Tracking upgrade | YOLO26 or D-FINE + BoT-SORT | Reduce identity switches during camera movement and occlusion. |
| Jersey identity | Dedicated jersey cropper + temporal sequence recognizer | Produce number probabilities from entire tracklets. |
| Geometry | Field keypoints and lines + CoTracker3 experiments | Estimate camera motion, homography, and stable marker positions. |
| NVIDIA optimization | TensorRT FP16, followed by carefully calibrated INT8 | Reduce inference latency after correctness is established. |
| Production video service | DeepStream if multiple authorized streams justify it | Operate decoding, inference, tracking, and telemetry continuously. |

## First recommended experiment

```text
authorized 1080p game clip
  -> YOLO26s player detector at 10-15 detections/sec
  -> ByteTrack at frame rate
  -> synthetic identity assigned to one chosen track
  -> browser overlay
  -> record ID switches, marker jitter, and end-to-end latency
```

This experiment teaches more about a real-time vision system than immediately
combining several foundation models. Once the pipeline is measurable, substitute
and compare one component at a time.
