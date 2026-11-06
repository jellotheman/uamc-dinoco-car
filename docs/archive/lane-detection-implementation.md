# Lane detection implementation: 2026-11-06

Archived completed implementation record on 2026-11-06; commands and new validation belong in the current guide and module documentation. Historical results below retain their original scope.

The lane detector now uses adaptive mean thresholding and histogram-seeded
sliding windows inspired by Simon Li AD's camera-node detector. See the
[pinned source comparison](lane-detection-comparison.md) for upstream references;
that comparison preserves the earlier UAMC implementation as a historical snapshot.
This implementation adapts the method to the existing calibrated ROS 2 pipeline.

## Scope and architecture

The scoped change is based on `d6b59069d0a9eb099f591ffeadc226c8de40a5c9` on `v1`.
Image undistortion and timestamped camera-to-base TF remain in use. A Gaussian
blur precedes adaptive mean thresholding; the resulting binary mask is sampled
on the metric ground grid. Near-field column histograms seed two lateral windows.
Window tracking follows narrow bright runs, then normalized least-squares cubic
fits describe the two boundaries. Both markings must be observed on enough
common rows with sufficient forward coverage, acceptable residuals and consistent
lane separation. Twenty center points are returned only over the observed range.

The algorithm stays a pure `detect_lane` function with private projection and
tracking helpers. The ROS node owns calibration, TF, parameters and message
conversion. No alternate backend, stateful tracker or framework was introduced.
A rejected image produces an empty path; no previous path is retained. Single-side inference and stop-line detection are outside this scope.

The ROS graph stays the same: `lane_detector` receives `/camera/image_raw` and
`/camera/camera_info`, uses TF and publishes `/perception/lane` (`nav_msgs/Path`,
`base_link`, source image timestamp). Planner, controller, safety gate, services
and actions keep their existing interfaces. Four tunables replace the fixed
brightness threshold; see the [module guide](../../ros2_ws/src/perception/README.md)
for defaults and migration from `threshold`. Existing named-node `params_file`
launch support can supply tuning; new launch files and dependencies are unnecessary.

## Verification

The perception package builds with `colcon build --symlink-install --packages-select
uamc_perception`. `colcon test --packages-select uamc_perception uamc_control`
passes 35 perception and 26 control tests; their scoped test-result reports have
zero errors and failures. New cases exercise dim markings, smooth illumination
changes, curved centerlines, both current narrow and wider lane spacing, missing
boundaries, noise, uniform bright images, transverse bands, invalid tuning and the
actual ROS callback's valid-to-empty transition. Dim-paint and uneven-illumination
cases failed against the original fixed-threshold detector before implementation.

Independent architecture/standards and spec/correctness reviews found no blocking
issues. A non-blocking observation is that fits can bridge missing intervals
between observed rows. There is no explicit maximum interruption length; this
behavior also existed in the earlier detector. Prolonged occlusion reliability
has not been demonstrated. Cubic fitting is not evidence of better real-world
accuracy without a recorded-image benchmark.

## Live simulator trials

Fresh headless practice and hairpin runs both completed the existing obstacle-stop
action successfully and reached measured standstill. Both retained 20-point
paths in every recorded sample. The defaults were used without scenario retuning.

| Course | Final Gazebo x, y (m) | Final reported clearance | Maximum sampled center error | Maximum sampled envelope-corner distance | Samples |
| --- | --- | --- | --- | --- | ---: |
| Practice | 3.440, 0.349 | 0.96 m | 0.0241 m | 0.1726 m | 78 |
| Hairpin | 4.448, 14.164 | 0.92 m | 0.0349 m | 0.1798 m | 868 |

The nominal inner lane edge is 0.225 m from center. Sampled conservative
0.40 x 0.26 m envelope corners stayed inside it in both runs. The hairpin
probe took about 179 wall-clock seconds, including both U-turns and the S-bend.
Its odometry drifted substantially from truth, so clearance analysis used Gazebo
poses rather than odometry. Neither timing nor these single runs establish a
performance improvement over the earlier detector. The supervised launch and
its simulator processes exited after each trial.
The probes use live camera/lane/obstacle data and drive the existing arm service
and run action. Gazebo ground-truth poses are sampled against course geometry;
sampled envelope checks are not continuous clearance proofs. Probe logs and CSVs
are local temporary artifacts under `/tmp/uamc-lane-*`, not committed recordings.
Physical-car performance, calibration and safety are not established by these checks.
