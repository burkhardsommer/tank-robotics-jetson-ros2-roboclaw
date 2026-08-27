# Tank Robot Manual

## 1. Overview

This document describes the setup and operation of the Tank Robot software on the NVIDIA Jetson.

The system consists of three primary components:

1. Camera driver
2. YOLO object detector
3. Tracker / joystick / motor controller

The components communicate through ROS 2 topics.

---

# 2. Software Environment

The current system uses:

```text
Ubuntu 22.04
ROS 2 Humble
Python 3.10
```

The YOLO Python environment is:

```text
~/venvs/yoloros2
```

ROS 2 Humble and the Python environment are normally sourced separately.

A convenience script is used to activate both.

### `start_yoloros.sh`

```bash
#!/bin/bash

# Source ROS 2 Humble setup
source /opt/ros/humble/setup.bash

# Activate Python virtual environment
source /home/user/venvs/yoloros2/bin/activate

# Optional: keep the shell open after sourcing
# exec "$SHELL"
```

Run it with:

```bash
source ~/start_yoloros.sh
```

After sourcing the script, the terminal should show:

```text
(yoloros3)
```

and ROS 2 commands such as `ros2 node list` should be available.

The script only modifies the current shell when called with `source`.

---

# 3. Python Dependencies

The main Python dependencies are listed in:

```text
requirements.txt
```

Important packages include:

```text
numpy
opencv-python
pyserial
ultralytics
torch
torchvision
```

## PyTorch on Jetson

PyTorch is currently installed as an NVIDIA/Jetson-specific build.

It should **not** be replaced with a generic desktop PyTorch package.

The installed version is:

```text
torch 2.5.0a0+872d972e41.nv24.8
```

The correct PyTorch build depends on the JetPack/L4T version of the Jetson.

---

# 4. ROS 2 Workspace

The workspace is:

```text
~/tank_ws
```

Source directory:

```text
~/tank_ws/src
```

Build the workspace with:

```bash
cd ~/tank_ws
source /opt/ros/humble/setup.bash
colcon build
```

After building:

```bash
source ~/tank_ws/install/setup.bash
```

---

# 5. Bluetooth Joystick

The Tank Robot uses a Bluetooth game controller for manual driving.

The controller must be paired with the Jetson before starting the joystick node.

## Bluetooth setup

Check the Bluetooth controller using:

```bash
bluetoothctl
```

Inside `bluetoothctl`:

```text
power on
agent on
default-agent
scan on
```

Wait until the controller appears.

Then pair using its Bluetooth MAC address:

```text
pair XX:XX:XX:XX:XX:XX
```

After successful pairing:

```text
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
```

You can stop scanning with:

```text
scan off
```

and exit:

```text
quit
```

Check that the controller is connected before starting the joystick node.

The exact controller name and MAC address depend on the game controller being used.

---

# 6. Joystick Node

## Why we do not use `joy_node`

The standard ROS 2 `joy` package was tested on the Jetson:

```bash
ros2 run joy joy_node
```

However, it did not provide usable joystick messages in the current Jetson configuration.

Although the node started and `/joy` existed as a ROS 2 topic, it did not provide the required controller input reliably.

Therefore, **the Tank Robot does not use the standard ROS 2 `joy_node`.**

Instead, the project uses a self-programmed Python joystick node.

## Starting the joystick node

The node is located at:

```text
~/tank_ws/src/poolbot_tracker/poolbot_tracker/joystick_node.py
```

Start it with:

```bash
python3 ~/tank_ws/src/poolbot_tracker/poolbot_tracker/joystick_node.py
```

This node reads the Bluetooth controller directly and publishes the joystick information required by the Tank Robot.

The joystick node is therefore an application-specific replacement for the standard ROS 2 `joy_node`.

---

# 7. Camera

The Tank Robot uses a Logitech C922 Pro Stream Webcam.

The camera is accessed through the ROS 2 `v4l2_camera` package.

## Install the camera package

If `v4l2_camera` is not installed:

```bash
sudo apt install ros-humble-v4l2-camera
```

Verify that the package is available:

```bash
ros2 pkg list | grep v4l2_camera
```

Expected:

```text
v4l2_camera
```

## Check the camera device

```bash
ls -l /dev/video*
```

Typical output:

```text
/dev/video0
/dev/video1
```

The C922 is normally available as `/dev/video0`.

The device can also be identified with:

```bash
v4l2-ctl --list-devices
```

If `v4l2-ctl` is not installed:

```bash
sudo apt install v4l-utils
```

---

# 8. Starting the Camera Node

The camera node is launched with:

```bash
ros2 run v4l2_camera v4l2_camera_node \
  --ros-args -p video_device:=/dev/video0
```

This starts the camera and publishes the image stream to:

```text
/image_raw
```

The camera currently runs at approximately:

```text
30 Hz
```

Verify the camera topic:

```bash
ros2 topic info /image_raw
```

Expected:

```text
Type: sensor_msgs/msg/Image
Publisher count: 1
```

Check the frame rate:

```bash
ros2 topic hz /image_raw
```

Expected:

```text
average rate: ~30 Hz
```

The camera node reports the C922 as:

```text
Driver: uvcvideo
Device: C922 Pro Stream Webcam
```

---

# 9. Camera Calibration

The `v4l2_camera` node may report that a calibration file is missing:

```text
Camera calibration file ... not found
```

This does **not** prevent the camera from publishing images.

For the current YOLO detection system, camera calibration is not required.

Calibration can be added later if the project requires accurate geometric measurements or 3-D reconstruction.

---

# 10. Starting the Detector

Activate the environment:

```bash
source ~/start_yoloros.sh
```

Go to the detector directory:

```bash
cd ~/tank_ws/src/poolbot_detector/poolbot_detector
```

Start the detector:

```bash
python3 detector_node.py
```

The detector loads:

```text
~/tank_ws/src/poolbot_detector/models/best.pt
```

and subscribes to:

```text
/image_raw
```

It publishes detection information to:

```text
/target_detection
```

A successful startup looks similar to:

```text
Model summary (fused): ...
[INFO] [detector_node]: Detector Node started with trained model.
```

---

# 11. YOLO Detection

The current trained model detects the objects required by the Tank Robot.

Typical YOLO output may look like:

```text
0: 480x640 1 whiteboat
```

or:

```text
0: 480x640 1 whiteboat, 1 redtoy
```

The detector processes the camera stream continuously.

The current inference time on the Jetson is approximately:

```text
~21 ms inference
```

with additional preprocessing and postprocessing time.

---

# 12. Detection Topic

Check the detection topic:

```bash
ros2 topic info /target_detection
```

Monitor the values:

```bash
ros2 topic echo /target_detection
```

The detector publishes:

```text
Float32MultiArray
```

with:

```text
[x_center, y_center, confidence]
```

The coordinates are normalized to the image dimensions:

```text
x_center = 0.0 ... 1.0
y_center = 0.0 ... 1.0
confidence = 0.0 ... 1.0
```

If no valid target is detected:

```text
[0.0, 0.0, 0.0]
```

---

# 13. Tracker

The tracker combines:

* joystick input
* target detection
* autonomous tracking logic
* RoboClaw motor commands

Start it with:

```bash
source ~/start_yoloros.sh

cd ~/tank_ws/src/poolbot_tracker/poolbot_tracker

python3 poolbot_tracker_node.py
```

Successful startup:

```text
[INFO] [joy_to_motor_node]: Joystick + Target Tracking Node Started
```

The tracker reports manual control with messages such as:

```text
[JOY] M1=0, M2=0
```

Autonomous tracking reports messages such as:

```text
[AUTO] No target (low confidence)
```

---

# 14. RoboClaw

The RoboClaw is connected to the Jetson through USB.

Check the serial devices:

```bash
ls /dev/ttyACM*
```

The current device is:

```text
/dev/ttyACM0
```

The tracker communicates with the RoboClaw using:

```text
roboclaw_3.py
```

## Safety during testing

The Tank Robot should initially be tested with:

* drive motors disconnected, or
* the tank physically lifted so the tracks cannot contact the ground.

This allows joystick, camera, YOLO, ROS 2, and RoboClaw communication to be verified without allowing the robot to move.

Once the software chain has been verified, the motors can be connected/enabled.

---

# 15. Recommended Startup Sequence

Use separate terminals.

## Terminal 1 — Camera

```bash
source /opt/ros/humble/setup.bash

ros2 run v4l2_camera v4l2_camera_node \
  --ros-args -p video_device:=/dev/video0
```

Verify:

```bash
ros2 topic hz /image_raw
```

Expected:

```text
~30 Hz
```

---

## Terminal 2 — Detector

```bash
source ~/start_yoloros.sh

cd ~/tank_ws/src/poolbot_detector/poolbot_detector

python3 detector_node.py
```

---

## Terminal 3 — Joystick

```bash
source ~/start_yoloros.sh

python3 ~/tank_ws/src/poolbot_tracker/poolbot_tracker/joystick_node.py
```

---

## Terminal 4 — Tracker

```bash
source ~/start_yoloros.sh

cd ~/tank_ws/src/poolbot_tracker/poolbot_tracker

python3 poolbot_tracker_node.py
```

---

# 16. Verify the Complete System

Check running nodes:

```bash
ros2 node list
```

Check available topics:

```bash
ros2 topic list
```

Check camera:

```bash
ros2 topic info /image_raw
```

Check camera frame rate:

```bash
ros2 topic hz /image_raw
```

Check detections:

```bash
ros2 topic echo /target_detection
```

The expected data flow is:

```text
C922 Webcam
     │
     ▼
v4l2_camera_node
     │
     │ /image_raw
     ▼
detector_node.py
     │
     │ /target_detection
     ▼
poolbot_tracker_node.py
     │
     ├──────── joystick_node.py
     │
     ▼
RoboClaw
     │
     ▼
Tank Motors
```

---

# 17. Troubleshooting

## `/image_raw` has no publisher

Run:

```bash
ros2 topic info /image_raw
```

If:

```text
Publisher count: 0
```

the camera node is not running.

Start it:

```bash
ros2 run v4l2_camera v4l2_camera_node \
  --ros-args -p video_device:=/dev/video0
```

---

## `/image_raw` is publishing but detector sees nothing

Check:

```bash
ros2 topic hz /image_raw
```

If the camera is publishing at approximately 30 Hz, check the detector terminal for YOLO inference output.

Then check:

```bash
ros2 topic echo /target_detection
```

---

## Tracker reports "No target"

This means the tracker is currently receiving no sufficiently confident target detection.

Check:

```bash
ros2 topic echo /target_detection
```

If the detector publishes:

```text
[0.0, 0.0, 0.0]
```

the detector did not select a valid target.

---

## Joystick does not work

First check the Bluetooth connection:

```bash
bluetoothctl
```

Then:

```text
devices
paired-devices
```

Make sure the controller is connected.

The Tank Robot does **not** rely on the standard ROS 2 `joy_node`. Start the project's custom joystick node:

```bash
python3 ~/tank_ws/src/poolbot_tracker/poolbot_tracker/joystick_node.py
```

---

# 18. Git

The Git repository is maintained from:

```text
~/tank_ws
```

Check the repository:

```bash
cd ~/tank_ws
git status
```

Add changes:

```bash
git add .
```

Commit:

```bash
git commit -m "Describe changes"
```

Push:

```bash
git push
```

---

# 19. Project Naming

The overall project is called:

**Tank Robot**

The current ROS 2 package names remain:

```text
poolbot_detector
poolbot_tracker
```

These names are retained to avoid unnecessary changes to ROS 2 package metadata and dependencies.

They can be migrated to `tank_detector` and `tank_tracker` later if desired.

# 20. License and Copyright

Copyright © 2026 Burkhard Sommer. All rights reserved.

The Tank Robot project is proprietary software. The source code, trained models, documentation, and other original project materials are not released under an open-source license.

See the `LICENSE` file in the repository root for the complete license terms.

Third-party software and libraries used by the project remain subject to their respective licenses.
