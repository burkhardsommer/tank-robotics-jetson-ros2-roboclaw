"""
Tank Robotics - YOLO Object Detection Node

ROS 2 node for camera-based object detection using a trained
Ultralytics YOLO model.

Publishes detected target information for use by the tracking node.

This node is part of the Tank Robotics project.
Copyright (c) 2026 Burkhard Sommer.
All rights reserved.
"""


import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from roboclaw_3 import Roboclaw
from std_msgs.msg import Float32MultiArray

# ---------------- CONFIG ----------------

ROBOCLAW_PORT = "/dev/ttyACM0"
ROBOCLAW_BAUDRATE = 115200
ROBOCLAW_ADDR = 0x80

MAXSPEED = 2700
SLOW_FACTOR = -0.6  # only 2% speed for testing

CONF_THRESHOLD = 0.5

# ----------------------------------------


class JoyToMotorNode(Node):
    def __init__(self):
        super().__init__("joy_to_motor_node")

        self.get_logger().info("Joystick + Target Tracking Node Started")

        # Init Roboclaw
        self.roboclaw = Roboclaw(ROBOCLAW_PORT, ROBOCLAW_BAUDRATE)
        self.roboclaw.Open()

        # Hold state
        self.joy_msg = None
        self.auto_mode = False
        self.target = {"x": 0.0, "y": 0.0, "conf": 0.0}

        # Subscriptions
        self.create_subscription(Joy, "/joy", self.joy_callback, 10)
        self.create_subscription(Float32MultiArray, "/target_detection", self.target_callback, 10)

        # Timer loop
        self.create_timer(0.03, self.update)

    # ------------ CALLBACKS ---------------

    def joy_callback(self, msg):
        self.joy_msg = msg

        # Button B = button index 1
        self.auto_mode = (msg.buttons[1] == 1)

    def target_callback(self, msg):
        # msg.data = [x, y, conf]
        if len(msg.data) != 3:
            return  # ignore invalid messages

        x, y, conf = msg.data

        # Shift to -0.5 .. 0.5 for readability/centering
        x = x - 0.5
        y = y - 0.5

        self.target = {"x": x, "y": y, "conf": conf}


    # ------------ CONTROL LOOP ------------

    def update(self):
        if self.joy_msg is None:
            return

        if not self.auto_mode:
            self.manual_control()
        else:
            self.auto_control()

    # ------------ MANUAL MODE -------------

    def manual_control(self):
        axis_y = self.joy_msg.axes[1]  # up/down
        axis_x = self.joy_msg.axes[0]  # left/right

        speed_v = int(axis_y * MAXSPEED * SLOW_FACTOR)
        speed_h = int(axis_x * MAXSPEED * SLOW_FACTOR)

        # M2 = vertical motor
        self.roboclaw.SpeedM2(ROBOCLAW_ADDR, speed_v)

        # M1 = horizontal motor
        self.roboclaw.SpeedM1(ROBOCLAW_ADDR, speed_h)

        self.get_logger().info(f"[JOY] M1={speed_h}, M2={speed_v}")

    # ------------ AUTO MODE ---------------

    def auto_control(self):
        if self.target["conf"] < CONF_THRESHOLD:
            # No good detection → stop
            self.roboclaw.SpeedM1(ROBOCLAW_ADDR, 0)
            self.roboclaw.SpeedM2(ROBOCLAW_ADDR, 0)
            self.get_logger().info("[AUTO] No target (low confidence)")
            return

        # Target.x ∈ [-0.5 .. 0.5]
        # Target.y ∈ [-0.5 .. 0.5]

        x = self.target["x"]
        y = self.target["y"]

        # DIRECTION RULES:
        # Horizontal (M1):
        #   x < 0 → object left  → move left  → +speed
        #   x > 0 → object right → move right → -speed
        speed_h = int((-x) * MAXSPEED * SLOW_FACTOR * 2)

        # Vertical (M2):
        #   y < 0 → object up    → move up   → -speed
        #   y > 0 → object down  → move down → +speed
        speed_v = int((y) * MAXSPEED * SLOW_FACTOR * 2)

        self.roboclaw.SpeedM1(ROBOCLAW_ADDR, speed_h)
        self.roboclaw.SpeedM2(ROBOCLAW_ADDR, speed_v)

        self.get_logger().info(
            f"[AUTO] x={x:.2f}, y={y:.2f}, M1={speed_h}, M2={speed_v}"
        )


# ---------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = JoyToMotorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
