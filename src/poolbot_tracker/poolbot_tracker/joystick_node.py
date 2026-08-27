
"""
Tank Robotics - Joystick Input Node

Reads joystick input and publishes joystick commands for the
Tank Robotics control system.

This custom node is used instead of the standard ROS 2 joy node,
which did not provide reliable joystick input in the current setup.

This node is part of the Tank Robotics project.
Copyright (c) 2026 Burkhard Sommer.
All rights reserved.
"""


import os
import struct
import select
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


JS_EVENT_FORMAT = "IhBB"
JS_EVENT_SIZE = struct.calcsize(JS_EVENT_FORMAT)

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80


class JoystickNode(Node):

    def __init__(self):
        super().__init__("joystick_node")

        self.device = "/dev/input/js0"

        self.axes = [0.0] * 8
        self.buttons = [0] * 14

        self.joy_pub = self.create_publisher(Joy, "/joy", 10)

        self.open_device()

        # Poll joystick frequently
        self.timer = self.create_timer(0.01, self.update)

        # Publish at ~50 Hz
        self.publish_counter = 0

        self.get_logger().info(
            f"Joystick node started using {self.device}"
        )

    def open_device(self):
        try:
            self.js = open(self.device, "rb", buffering=0)

            # Non-blocking
            os.set_blocking(self.js.fileno(), False)

            self.get_logger().info(
                f"Opened joystick: {self.device}"
            )

        except Exception as e:
            self.js = None
            self.get_logger().error(
                f"Could not open {self.device}: {e}"
            )

    def update(self):

        if self.js is None:
            self.open_device()
            return

        try:

            while True:

                ready, _, _ = select.select(
                    [self.js],
                    [],
                    [],
                    0
                )

                if not ready:
                    break

                data = self.js.read(JS_EVENT_SIZE)

                if len(data) != JS_EVENT_SIZE:
                    break

                timestamp, value, event_type, number = struct.unpack(
                    JS_EVENT_FORMAT,
                    data
                )

                # Remove initialization flag
                event_type &= ~JS_EVENT_INIT

                if event_type == JS_EVENT_AXIS:

                    if number < len(self.axes):
                        # Linux joystick values are -32767 ... +32767
                        self.axes[number] = value / 32767.0

                elif event_type == JS_EVENT_BUTTON:

                    if number < len(self.buttons):
                        self.buttons[number] = value

            # Publish at approximately 50 Hz
            self.publish_counter += 1

            if self.publish_counter >= 5:

                self.publish_counter = 0

                msg = Joy()

                msg.header.stamp = self.get_clock().now().to_msg()

                msg.axes = self.axes
                msg.buttons = self.buttons

                self.joy_pub.publish(msg)

        except Exception as e:

            self.get_logger().error(
                f"Joystick read error: {e}"
            )

            try:
                self.js.close()
            except:
                pass

            self.js = None


def main(args=None):

    rclpy.init(args=args)

    node = JoystickNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()
