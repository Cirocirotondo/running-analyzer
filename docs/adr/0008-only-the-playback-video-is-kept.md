# Only the Playback Video is kept

The skeleton drifted out of sync with the original phone footage whenever the file had a quirk (frames hidden by an edit list, the slow-motion start gap, dropped frames, HEVC decoded differently by each browser), and the originals took 300 MB–1 GB each while the Analysis uses 20 seconds. After a successful Analysis the worker therefore writes a Playback Video, the frames of the Analysis Window one per keypoint row at a regular pace in H.264, and deletes the uploaded Video; a failed Analysis deletes it too, unless the Runner sends it to the team in a Failure Report. The overlay is aligned by construction and storage drops to about 19 MB per Video, at the price of never re-analyzing anything outside the Analysis Window with a better pipeline. Supersedes [0002](0002-videos-kept-until-runner-deletes-them.md).

## Considered Options

- Keep the original and map times to rows more carefully in the browser: each fix covered one quirk; the next file brought another, and browser decoders cannot be tested for every platform.
- Let the Runner cut 20 seconds in the browser before upload: a cut without re-encoding creates exactly the edit-list quirk, re-encoding 240 fps HEVC in the browser is slow or unsupported, and choosing the best stretch needs the pose model on the server. Kept as a later upload-size optimisation, with the server still choosing inside the uploaded stretch.
