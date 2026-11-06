# Lane detection: UAMC and Simon Li's AD

Research snapshot: 2026-11-05. This compares the current UAMC source with the `main` branch of [simonli357/AD](https://github.com/simonli357/AD) at commit [`cb73d5ad6a407273e125e53a8b559687431cc6f0`](https://github.com/simonli357/AD/tree/cb73d5ad6a407273e125e53a8b559687431cc6f0). These are code observations, not a benchmark or evidence of real-car performance.

> Historical comparison: the UAMC algorithm below describes the pre-upgrade
> implementation. See [the implementation record](../development/lane-detection-implementation.md)
> for the current adaptive-threshold and sliding-window detector.

## Simon Li AD

The [camera launch](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/launch/cameraNode.launch) enables lane detection by default. Its [camera processing class](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/include/Perception.hpp) calls `LaneDetector::publish_lane`; the [detector](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/include/LaneDetector.hpp) uses classical OpenCV image processing, inverse perspective mapping and sliding-window polynomial fitting, not a learned lane detector:

1. Convert the image to grayscale, apply a 5 x 5 Gaussian blur and use adaptive mean thresholding to identify bright pixels.
2. Build a ground-plane homography using camera intrinsics and a configured real-camera pose; remap the binary image to a bird's-eye image (inverse perspective mapping, IPM).
3. In a near-field region, sum binary pixels by column, identify and cluster peaks as candidate markings, and select lane seeds. It also derives a separate near-field center offset when two peaks have approximately the expected separation.
4. Starting from the seeds, use sliding windows to collect marking pixels along each side and fit third-degree polynomials by least squares if sufficient windows contain pixels. If initially only one side is selected and successfully fitted, the other can be inferred by shifting the fit by an assumed lane width. It generates center and boundary waypoints from the fits.
5. It also performs separate stop-line detection and puts stop-line distance, offset and waypoint information in a `utils/Lane3` message on `/lane` when publishing is enabled.

The repository also contains an [older standalone histogram implementation](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/src/lane.cpp), which uses a lower image strip and returns an image-space center and stop-line flag. It should not be confused with the detector used through the camera-node path described above.

The [configuration file](https://github.com/simonli357/AD/blob/cb73d5ad6a407273e125e53a8b559687431cc6f0/src/perception/config/lane_params.yaml) specifies IPM and window parameters. Caution: in the inspected detector `preprocess` initializes `static bool first` without a true initializer, so the conditional parameter reads for the adaptive threshold are not reached as written; its local defaults are used. Some fit-consistency checks are commented out, so their comments do not establish active validation.

## UAMC

The [lane detector implementation](../../ros2_ws/src/perception/uamc_perception/lane.py) also uses classical image processing and a ground-plane view, but it does not use AD's sliding windows. The [ROS 2 node](../../ros2_ws/src/perception/uamc_perception/lane_node.py) obtains camera calibration and a timestamped camera-to-vehicle TF transform, then:

1. Converts to grayscale, undistorts using camera intrinsics and distortion coefficients, and projects a grid of ground points into the image. It samples brightness into that vehicle-frame grid.
2. Applies a fixed brightness threshold. For each forward-distance row, it identifies narrow bright runs, pairs runs within the allowed lane-width range and chooses the pair with midpoint nearest the vehicle center.
3. Requires enough paired rows and sufficient forward coverage, fits a quadratic to each boundary, and rejects results with excessive residual or fitted widths outside the permitted range. It returns 20 points halfway between the two fitted curves.
4. Publishes those points as a `nav_msgs/Path` on `/perception/lane` in `base_link`. Missing or invalid calibration, transform or image data and rejected fits produce an empty path.

In the ROS node defaults the fixed brightness threshold is 190, near and far distances are 0.25 m and 1.5 m, and the acceptable width is 0.35-0.95 m. Simulation overrides the ground height; geometry and camera pose are provisional.

## Practical differences

| | Simon Li AD camera-node detector | UAMC |
| --- | --- | --- |
| Extraction | Adaptive threshold, near-field histogram seeds and sliding windows | Fixed brightness threshold and independently paired runs on sampled ground rows |
| Curve fit | Cubic, using collected window pixels | Quadratic, using selected row centers |
| One visible side | Can synthesize the other when the initial selection is a single side and that fit succeeds | Requires paired boundaries in enough rows |
| Outputs | Offset, waypoints and stop-line data in ROS 1 custom message | ROS 2 path; obstacle detection is separate and lane detector does not detect stop lines |
| Calibration | Intrinsics and configured pose feed IPM; preprocessing does not explicitly undistort in this path | CameraInfo distortion/intrinsics plus timestamped TF |

Both assume a usable approximately planar road and appropriate camera calibration. AD's adaptive threshold and single-side reconstruction could help in some situations; UAMC's required pairs and width/residual checks reject some ambiguous observations. These are design tradeoffs, not proven comparative performance claims. Test on representative recorded images and physical track conditions before adopting either approach.
