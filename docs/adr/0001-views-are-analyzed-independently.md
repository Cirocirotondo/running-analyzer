# Side and Rear Views are analyzed independently

Most Runners film with a single phone, so the Side and Rear Videos of a Session are filmed one after the other, not at the same time. We therefore analyze each View on its own and never combine them frame by frame: no synchronization, no multi-camera 3D reconstruction. Each Metric comes from exactly one View, and the Side View is mandatory because the most reliable Metrics (sagittal angles, cadence) come from it.

## Consequences

- Strides in the Side Video and the Rear Video are different strides; Metrics from the two Views can be compared only as averages over many gait cycles.
- Multi-camera approaches (Pose2Sim, OpenCap) are out of scope unless this decision is revisited.
