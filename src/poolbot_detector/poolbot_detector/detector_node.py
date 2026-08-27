"""
Tank Robot - YOLO Object Detector

Receives camera images from ROS 2, performs object detection using
the trained YOLO model, and publishes the selected target position
for the tracking node.
"""

# Copyright © 2026 Burkhard Sommer. All rights reserved.
#
# This file is part of the Tank Robot project.
#
# Proprietary software. No permission is granted to copy, modify,
# distribute, sublicense, publish, sell, or otherwise use this file
# without prior written permission from the copyright holder.
#
# See the LICENSE file in the repository root for the complete terms.

import sys
import site

# Add your virtualenv site-packages to sys.path
site.addsitedir('/home/user/venvs/yoloros2/lib/python3.10/site-packages')

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2

class DetectorNode(Node):
    def __init__(self):
        super().__init__('detector_node')

        self.bridge = CvBridge()

        # Subscribe to camera topic
        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10
        )

        # Publisher for detection results
        self.publisher_ = self.create_publisher(Float32MultiArray, '/target_detection', 10)

        # Load trained YOLOv5 model (inside models/best.pt)
        self.model = YOLO('/home/burkhard/poolbot_ws/src/poolbot_detector/models/best.pt')

        self.model.fuse()  # optional for Jetson speedup

        self.get_logger().info('Detector Node started with trained model.')

    def image_callback(self, msg):
        img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        results = self.model.predict(img, conf=0.5)

        output = Float32MultiArray()
        output.data = [0.0, 0.0, 0.0]  # default: nothing detected

        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                for b in boxes:
                    cls = int(b.cls[0])
                    if cls == 1:
                        x1, y1, x2, y2 = b.xyxy[0]
                        conf = float(b.conf[0])
                        x_center = ((x1 + x2) / 2) / img.shape[1]
                        y_center = ((y1 + y2) / 2) / img.shape[0]
                        output.data = [float(x_center), float(y_center), float(conf)]
                        break

        self.publisher_.publish(output)

def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
