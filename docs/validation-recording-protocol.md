# Recording protocol for the camera-placement validation

Goal: measure how much camera height changes each Metric, by filming the same runner at the same speed
from a good position and from a bad one. Secondary goals: near-leg vs far-leg difference, and a clean
reference recording at hip height for the first round of threshold tuning.

With **one phone** the two positions cannot be filmed at the same time, so they are filmed one after the
other in an A-B-A-B sequence. Repeating each position measures how much a Metric changes between two
clips filmed the same way (clip-to-clip variation); a difference between positions larger than that is
an effect of the camera. Steady-state repeatability measured on 10-03 was cadence ±2–4 steps/min and
contact time ±8 ms, so effects of a few degrees or centimetres will be visible.

## Equipment

- One phone in slow-motion mode applied to the whole clip (240 fps if available, else 120).
  Main camera only: no ultra-wide / 0.5x.
- Something to hold the phone at hip height: tripod, a bench, a box on the neighbouring treadmill, a bag.
- Tape (or anything) to mark each phone position on the floor, and a tape measure if available.
- Treadmill speed 14 km/h, 0 % incline (same as the first session, so the two days can be compared).
- Same shoes for every clip.

## Positions

```
                 side wall
   B (floor, 1.5 m)        A (hip height, 3-4 m)
        \                  /
         \                /
      ====================   <- belt, runner facing left
```

- **A — reference**: hip height (~90-100 cm), 3-4 m from the belt, perpendicular to it, pointing at the hip.
  Whole body in frame with margin above the head and below the feet.
  Nothing between the camera and the legs: no handrail or frame of the neighbouring treadmill (the
  arches in yesterday's clip hid the feet in swing). As much light as possible: the feet are
  motion-blurred in swing even at 240 fps, and blur is the main residual error on foot keypoints.
- **B — bad**: on the floor, 1.5 m from the belt, tilted up, like yesterday's clip. Same side as A.
- **C — optional**: on the floor like B, but 3-4 m away like A. Separates the effect of height from the
  effect of distance.
- **R — rear**: directly behind the belt, hip height, ~2 m.

Mark A and B on the floor before the first clip, and note the phone height and distance from the belt.
A2 and B2 must be filmed from exactly the same spots as A1 and B1. A photo of each setup helps.

## Measurements and markers

The app turns pixels into centimetres by assuming thigh + shank = 49 % of body height. Known distances
in the video check that assumption (it drives ankle-ahead-of-hip and vertical oscillation) and the real
belt speed (it drives step length). Use brightly coloured tape that stands out against the black frame.

**Markers on the treadmill**, on the side facing the camera:

- **Two fixed marks on the side rail or deck edge, exactly 100 cm apart**, at belt height, roughly
  centred in the frame. They give the pixel-to-cm scale, show whether the camera is tilted, and act as
  the start and finish line for the speed check.
- **One mark on the belt itself, at its edge** (where the feet never land). Its passage between the two
  fixed marks, filmed at 240 fps, gives the real belt speed to about 1–2 %. Ask the gym first if needed;
  remove it afterwards.
- **Rear view**: two marks at the back of the deck on the two belt edges, so the belt width is visible.
  They show whether the rear camera is tilted.

**Distances to write down** (tape measure, in cm):

| What | Why |
|------|-----|
| Belt width, and distance from the side marks to the belt centre line | The runner moves in the centre plane, further from the camera than the marks: this corrects the scale for depth |
| For each position (A, B, C, R): height of the phone lens from the floor | Camera height and tilt, for the perspective error |
| For each position: horizontal distance from the lens to the belt centre line | Same |
| Your leg: floor to the bony bump on the side of the hip (greater trochanter), standing, shoes on | Checks the 49 % leg-length assumption for you |
| Your leg: that bump to the knee joint line, and knee joint line to the ankle bone (outer side) | Thigh and shank separately, as the pose model sees them |

A photo of the tape measure next to each mark, and of each phone position, avoids doubts later.

## Recordings (in this order)

| # | Position | What | Running at speed |
|---|----------|------|------------------|
| 1 | A | side view, runner's **left** side | 40 s |
| 2 | B | side view, left side | 40 s |
| 3 | A | side view, left side (repeat of #1) | 40 s |
| 4 | B | side view, left side (repeat of #2) | 40 s |
| 5 | A, other side | side view, runner's **right** side | 40 s |
| 6 | R | rear view | 30 s |
| 7 | C (optional) | side view, left side | 40 s |

**If someone can help:** run continuously at 14 km/h and let them move the phone between clips; start
each clip once the phone is placed. Only the change of camera differs between clips.

**If you are alone:** for each clip, place the phone, start recording, get on the treadmill, bring it to
14 km/h and run 40 s at speed, then stop. Recording the ramp-up does not matter: the analysis finds the
steady part by itself. Rest the same short time between clips (about 1 minute), so fatigue builds up
evenly; the A-B-A-B order spreads it across both positions anyway.

If a bystander walks behind the treadmill it does not matter; if someone stands between camera and belt
for more than a second, redo the clip.

## After recording

- Do not trim or export from the gallery with "save as" (that may re-encode and drop the capture-fps tag);
  copy the original files.
- Note the exact speed shown by the treadmill.
- Copy to `videos/` with the pattern `YYYYMMDD_<n>_<A|B|C|R>_<left|right|rear>.mp4`, where `<n>` is the
  clip number in the table.
- Each clip can also be uploaded as its own session in the app.

## What will be compared

- **Camera effect**: mean of #1 and #3 (A) against mean of #2 and #4 (B), for every side-view Metric.
- **Clip-to-clip variation**: #1 vs #3 and #2 vs #4. A camera effect counts only if it is clearly larger
  than this variation.
- **Near leg vs far leg**: #1 and #3 (left leg near the camera) vs #5 (right leg near the camera).
- **Rear view**: #6, pelvic drop and hip adduction with a closer camera (hip width in pixels should
  roughly double compared with 10-03).
- **Height vs distance**: #7 vs #2 (same height, different distance) and #7 vs #1/#3 (same distance,
  different height).
- **Scale**: the 100 cm marks, corrected for depth, against the scale from body height. The gap is the
  error of every centimetre Metric; your measured leg length says how much of it is the 49 % assumption.
- **Belt speed**: the belt mark's passages between the fixed marks against the 14 km/h on the display.

## If a second phone is available

Borrowing any phone that films at 60 fps or more adds the strongest comparison: A and B filmed at the
same time see the same strides, so differences can be compared step by step instead of as averages.
In that case record #1 and #2 together, one phone at A and one at B, and skip #3 and #4.
