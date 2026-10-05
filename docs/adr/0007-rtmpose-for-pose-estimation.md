# RTMPose (via rtmlib) for pose estimation

Pose estimation uses RTMPose with the Halpe26 keypoint set (body plus heel and toes), run through the `rtmlib` ONNX wrapper, rather than MediaPipe Pose. MediaPipe is simpler to deploy and runs on CPU, but on the four treadmill videos tried during the prototype (two stock clips at 24–25 fps and the owner's own 240 fps clip) it lost the feet and produced unusable gait events: cadence 158 ± 43 steps/min against 157 ± 7 for RTMPose on the same clip, with the far leg's keypoint score at 0.54 against 0.86. RTMPose's values were consistent across cycles on every video, matching the published comparison (arXiv 2505.04713, ~5.6° joint-angle error). The cost is a heavier model: about 80–120 ms per frame on an RTX 4060, more on CPU, which the asynchronous worker absorbs.

## Consequences

- Keypoints are stored in the Halpe26 layout; the common 13-point subset used by the metrics (shoulder, hip, knee, ankle, heel, toe per side, plus nose) is the contract the rest of the pipeline depends on.
- A different model can be swapped in by mapping its keypoints to that subset, as the prototype already does for MediaPipe.
- Processing a 30 s clip at 240 fps means ~7 200 frames, i.e. 10–15 minutes of GPU time with detection on every frame; tracking the runner's bounding box between frames instead of re-detecting is the obvious optimization.
