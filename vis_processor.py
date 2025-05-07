import logging
import threading
import time

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from vis_fake_camera import VisFakeCamera

logger = logging.getLogger("vis_processor")


class VisProcessor:
    """
    A class that simulates a camera by generating a test pattern and
    allows for double buffering of frames.
    """

    def __init__(self, fps=30):
        self.fps = fps
        self._stop = False
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0
        self._left_camera = VisFakeCamera()
        self._right_camera = VisFakeCamera()
        self.callback = None
        self._thread = None
        self.task_info = None
        self.device = 'cpu'
        self.model = None
        self.model_path = 'model/best.pt'

    def set_task_info(self, task_info):
        self.task_info = task_info

    def set_camera_param(self, param):
        """
        Set the camera parameters for both left and right cameras.
        """
        self._left_camera.set_camera_param("left", param)
        self._right_camera.set_camera_param("right", param)

    def set_frame_callback(self, callback):
        self.callback = callback

    def start(self):
        """
        Start the double fake camera.
        """
        self._stop = False
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0

        self._left_camera.start()
        self._right_camera.start()

        # Start the frame processing thread
        self._thread = threading.Thread(target=self._process_frames, daemon=True)
        self._thread.start()

        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

            # Load model and move to appropriate device
            self.model = YOLO(self.model_path, verbose=False)
            self.model.to(self.device)
            # Print device information
            if self.device == 'cuda':
                print(f"Using GPU: {torch.cuda.get_device_name(0)}")
                print(
                    f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024 ** 2:.0f}MB")
            else:
                print("GPU not available, using CPU")

            print(f"Model loaded successfully on {self.model.device}!")
        except Exception as e:
            print("Model loading failed! Error: ", e)
            self.model = None
            raise ValueError("Model loading failed! Error: {e}")

        logger.info("Processor started")

    def stop(self):
        """
        Stop the double fake camera.
        """
        logger.info("Stopping processor")

        self._stop = True
        self._left_camera.stop()
        self._right_camera.stop()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        self.model = None
        print("Model resources released!")

    def calc_iou(self, box1, box2):
        # box: [x1, y1, x2, y2]
        xA = max(box1[0], box2[0])
        yA = max(box1[1], box2[1])
        xB = min(box1[2], box2[2])
        yB = min(box1[3], box2[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        box1Area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2Area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        iou = interArea / float(box1Area + box2Area - interArea + 1e-6)
        return iou

    def center_distance(self, box1, box2):
        cx1 = (box1[0] + box1[2]) / 2
        cy1 = (box1[1] + box1[3]) / 2
        cx2 = (box2[0] + box2[2]) / 2
        cy2 = (box2[1] + box2[3]) / 2
        return np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)

    def predict(self, image):
        try:
            if not self.model:
                raise ValueError("Model is not loaded. Please call start() with a valid model path.")

            if self.device == 'cuda':
                autocast_ctx = torch.amp.autocast('cuda')
            else:
                from contextlib import nullcontext
                autocast_ctx = nullcontext()

            with autocast_ctx:
                # 降低置信度阈值，提高安全帽检测率
                predicts = self.model.predict(
                    image,
                    device=self.device,
                    # conf=0.25,  # 从0.4降低到0.25
                    verbose=False)

            if len(predicts) == 0:
                print("No detection results found!")
                return None, []

            predict = predicts[0]
            boxes = predict.boxes

            img_draw = image.copy()
            detections = []

            hardhat_boxes = []
            person_boxes = []

            # 分离人和安全帽的检测
            for box in boxes:
                cls = int(box.cls[0])
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                if cls == 0:  # 安全帽
                    hardhat_boxes.append(xyxy)
                elif cls == 5:  # 人
                    person_boxes.append((xyxy, box))

            # 调试输出
            # print(f"检测到 {len(hardhat_boxes)} 个安全帽和 {len(person_boxes)} 个人")
            # 如果安全帽个数大于人，则不进行匹配，比较糙
            if len(hardhat_boxes) >= len(person_boxes):
                return img_draw, detections

            # 为每个人检查是否有对应的安全帽
            for xyxy, box in person_boxes:
                has_hardhat = False
                person_height = xyxy[3] - xyxy[1]
                person_width = xyxy[2] - xyxy[0]

                # 计算人头部区域（大约是上部1/3）
                head_y_top = xyxy[1]
                head_y_bottom = xyxy[1] + person_height // 3
                head_x_left = xyxy[0]
                head_x_right = xyxy[2]

                # 人的中心点
                person_cx = (xyxy[0] + xyxy[2]) / 2
                person_cy = xyxy[1] + person_height // 6  # 假设头部中心在上部1/6处

                # 为每个安全帽计算与人的匹配度
                for hat_xyxy in hardhat_boxes:
                    hat_cx = (hat_xyxy[0] + hat_xyxy[2]) / 2
                    hat_cy = (hat_xyxy[1] + hat_xyxy[3]) / 2

                    # 计算安全帽与人头部的水平距离（相对于人的宽度）
                    rel_x_dist = abs(hat_cx - person_cx) / person_width

                    # 计算安全帽与人头部的垂直距离（相对于人的高度）
                    rel_y_dist = abs(hat_cy - person_cy) / person_height

                    # 计算IoU值
                    iou = self.calc_iou(xyxy, hat_xyxy)

                    # 更宽松的匹配条件：
                    # 1. 安全帽在人的头部区域附近
                    # 2. 或者IoU值足够高
                    # 3. 或者安全帽与人的相对距离足够小
                    if (head_x_left <= hat_cx <= head_x_right and head_y_top <= hat_cy <= head_y_bottom) or \
                            (iou > 0.05) or \
                            (rel_x_dist < 0.5 and rel_y_dist < 0.5):
                        has_hardhat = True
                        break

                if has_hardhat:
                    continue

                # 基于安全帽检测绘制边界框
                color = (0, 255, 0) if has_hardhat else (255, 0, 0)  # 有安全帽为绿色，没有为红色
                cv2.rectangle(img_draw, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)

                # 添加文本标签
                label = "Hardhat" if has_hardhat else "No Hardhat"
                cv2.putText(img_draw, label, (xyxy[0], xyxy[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # 添加检测信息
                detection = {
                    'bbox': box.xyxy[0].tolist(),
                    'confidence': float(box.conf[0]),
                    'class_id': 5,
                    'class_name': predict.names[5],
                    'has_hardhat': has_hardhat
                }
                detections.append(detection)

            # 绘制安全帽边界框
            # for hat_xyxy in hardhat_boxes:
            #     cv2.rectangle(img_draw, (hat_xyxy[0], hat_xyxy[1]), (hat_xyxy[2], hat_xyxy[3]), (255, 255, 0), 2)
            #     cv2.putText(img_draw, "Hardhat", (hat_xyxy[0], hat_xyxy[1] - 10),
            #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            return img_draw, detections

        except Exception as e:
            print(f"Processing failed! error: {e}")
            return None, []

    def _process_frames(self):
        """
        Get the current frame from the left camera.
        """

        last_log_time = 0

        while not self._stop:
            if self.model is None:
                logger.warning("Model is not loaded. Waiting for model to load.")
                time.sleep(1)
                continue

            loop_start = time.time()

            try:
                # Get the current frame from the left camera
                left_frame = self._left_camera.get_frame()
                right_frame = self._right_camera.get_frame()

                if left_frame is None or right_frame is None:
                    logger.warning("Failed to get frames from cameras")
                    continue

                # Log periodically to avoid flooding logs
                current_time = time.time()
                if current_time - last_log_time > 5.0:  # Log every 5 seconds
                    elapsed = current_time - self._start_time
                    fps = self._frame_count / elapsed if elapsed > 0 else 0
                    logger.info(f"frame counts={self._frame_count}, fps={fps:.2f}")
                    last_log_time = current_time

                # Combine the frames from both cameras
                combined_frame = self._combine_frames(left_frame, right_frame)

                # YOLO predict
                predicted_image, detections = self.predict(combined_frame)
                # print('detections:', detections)

                self.callback(predicted_image)
                self._frame_count += 1

                # Calculate the time taken for processing and sleep if necessary
                processing_time = time.time() - loop_start
                sleep_time = (1.0 / self.fps) - processing_time

                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                # TODO boilerplate
                logger.error(f"Error processing frames: {str(e)}")
                emergency_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(emergency_frame, f"Error: {str(e)}", (50, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                self.callback(emergency_frame)
                logger.error("Emergency frame sent")

    def _combine_frames(self, left_frame, right_frame):
        """
        Combine the frames from the left and right cameras.
        """
        # Assuming both frames are of the same size
        height, width, _ = left_frame.shape
        overlap_width = int(width * 0.8)

        # Crop the overlapping region from the right frame
        cropped_right_frame = right_frame[:, overlap_width:]

        # Add "Left" text to the left frame
        cv2.putText(left_frame, "Left", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

        # Add "Right" text to the cropped right frame
        cv2.putText(cropped_right_frame, "Right", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2,
                    cv2.LINE_AA)

        # Add opacity to the cropped right frame
        # cropped_right_frame = cv2.addWeighted(cropped_right_frame, 0.5, cropped_right_frame, 0, 0)

        # Concatenate the left frame and the cropped right frame
        combined_frame = cv2.hconcat([left_frame, cropped_right_frame])

        return combined_frame
