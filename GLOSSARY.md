# Running Analyzer

Analyzes a person's running technique from treadmill videos, measures kinematic metrics and gives evidence-based technique advice.

## Language

### People

**Account**:
The login identity that owns one or more Runners. In the first version every Account owns exactly one Runner.
_Avoid_: User, profile

**Active Account**:
An Account that was used while signed in at least once in the last 30 days.
_Avoid_: Active user, engaged user

**Runner**:
The person whose running technique is analyzed. In the first version the Runner is also the person who owns the Account.
_Avoid_: Athlete, user, client

**Admin**:
A member of the project team who manages Invite Codes and monitors the service. An Admin is not an Operator and does not analyze Runners.
_Avoid_: Superuser, moderator

**Invite Code**:
A single-use code that lets a new person create an Account during the closed beta.
_Avoid_: Referral, token

**Operator**:
A professional (coach, physiotherapist, running store) who analyzes the technique of several Runners. Not part of the first version.
_Avoid_: Trainer, admin

### Input

**Session**:
A set of Videos of one Runner recorded on the same occasion under the same Treadmill Settings and with the same shoes. Changing speed, incline or shoes means a new Session.
_Avoid_: Analysis, test, run, workout

**Recording Guide**:
The instructions shown to the Runner on how to film a Video (camera placement, framing, frame rate).
_Avoid_: Tutorial, setup instructions

**View**:
The camera angle of a Video, named after the side of the Runner the camera sees: Left Side, Right Side or Rear. A Session has at least one Side View and at most one Video per View.
_Avoid_: Angle, perspective, "right of the room"

**Near Leg**:
The leg on the side of the Runner facing the camera in a Side View. Leg Metrics from a Side View come only from its Near Leg; the other leg needs the opposite Side View.
_Avoid_: Visible leg, front leg

**Video**:
One uploaded video file of a Session, filmed from one View. The Videos of a Session are not synchronized: they may be filmed one after the other.
_Avoid_: Recording, clip

**Analysis Window**:
The 20 seconds of steady running inside a Video that the Analysis measures. Everything outside it is discarded once the Analysis succeeds.
_Avoid_: Section, segment, interval, excerpt

**Playback Video**:
The video the Runner watches with the skeleton on top: the frames of the Analysis Window, one per keypoint row, at a regular pace. It replaces the uploaded Video once the Analysis succeeds.
_Avoid_: Clip, normalized video, preview

**Recording Check**:
The automatic inspection of a Video right after upload, which recognizes its View and judges the camera placement. Its outcome is Rejected, Warning or OK; a Video with a Warning can still be submitted.
_Avoid_: Validation, quality gate

**Improvement Consent**:
The Runner's optional, per-Session permission for Admins to view its Videos in order to improve the analysis.
_Avoid_: Research consent, data sharing

**Failure Report**:
A failed Session whose Videos the Runner, through Improvement Consent, left to the team to investigate. It stays open until an Admin resolves it.
_Avoid_: Bug report, ticket, flag

**Treadmill Settings**:
The speed and incline of the treadmill during a Session.

### Output

**Analysis**:
The result the system produces from a Session: skeleton, Metrics and Advice. A Session has at most one Analysis.
_Avoid_: Report, result, assessment

**Metric**:
A kinematic quantity measured in an Analysis, such as cadence or knee flexion at initial contact. Each Metric comes from exactly one View and is either measured or Unmeasurable.
_Avoid_: Parameter, score

**Typical Range**:
The range of values of a Metric reported in a cited study for a reference group of runners. It is a group average, not a validated cut-off for an individual.
_Avoid_: Normal range, target, threshold

**Descriptor**:
A Metric reported without a Typical Range, because the literature does not link it to injury or economy (e.g. foot strike pattern, ground contact time). A Descriptor never produces Advice.
_Avoid_: Info metric

**Unmeasurable**:
The state of a Metric whose underlying pose data is too unreliable to report a value. An Unmeasurable Metric never produces Advice.
_Avoid_: Missing, invalid, error

**Unreliable**:
The state of a Metric that has a value but may be biased by a Recording Check Warning, such as a camera placed too low. The value is shown, marked as not reliable.
_Avoid_: Approximate, low quality

**Advice**:
A technique suggestion derived from a Metric that falls outside the typical range reported in the literature, always citing its source. It is never a diagnosis.
_Avoid_: Diagnosis, prescription, recommendation
