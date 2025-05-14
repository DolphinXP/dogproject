import json
import logging
import threading
import time
import os

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
        self.module_prefix = "vis"
        self.output_width = 1280
        self.output_height = 480

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
        # for video recording
        self.allow_recording = False
        self.video_writer = None
        self.output_folder = None
        self.record_name = None
        self.record_duration = None
        self.record_start_time = None

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

    def start_recording(self, output_folder, duration):
        """
        Start recording the video with H.264 codec for HTML5 compatibility.
        """
        if self.video_writer:
            return


        self.output_folder = output_folder
        self.record_duration = duration
        self.record_start_time = time.time()

        # Create the output folder if it doesn't exist
        os.makedirs(self.output_folder, exist_ok=True)

        if self.task_info:
            with open(os.path.join(self.output_folder, f"{self.record_name}.json"), "w", encoding="utf-8") as f:
                json.dump(self.task_info, f, ensure_ascii=False, indent=4)
            self.record_name = f"{self.module_prefix}_{self.task_info['taskId']}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        else:
            self.record_name = f"{self.module_prefix}_NOTASKID_{time.strftime('%Y%m%d_%H%M%S')}.mp4"

        # Initialize video writer with H.264 codec
        output_path = os.path.join(self.output_folder, self.record_name)
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # Use H.264 codec
        frame_width, frame_height = self.output_width, self.output_height  # Ensure consistent frame size
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, (frame_width, frame_height))



    def record_frame(self, frame):
        """
        Write a frame to the video file if recording is active and within the duration limit.
        """
        if self.video_writer:
            elapsed_time = time.time() - self.record_start_time
            if elapsed_time <= self.record_duration:
                # Ensure frame size matches the initialized size
                frame = cv2.resize(frame, (self.output_width, self.output_height))
                self.video_writer.write(frame)
            else:
                logger.info("Recording duration reached, stopping recording.")
                self.stop_recording()

    def stop_recording(self):
        """
        Stop recording the video and ensure the file is properly closed.
        """
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            print("Video recording stopped and saved.")


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

            # img_draw = image.copy()
            img_draw = predict.plot()
            detections = []

            for box in boxes:
                # Get box coordinates and confidence
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detection = {
                    'bbox': xyxy,
                    'confidence': float(box.conf[0]),
                    'class_id': cls,
                    'class_name': predict.names[cls]
                }
                detections.append(detection)

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

                # add datetime to left-bottom corner
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                cv2.putText(predicted_image, time_str, (10, predicted_image.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

                # TEST
                # print('detections:', detections)
                target_class_name = "NO-Safety Vest"
                filtered_detections = [d for d in detections if d['class_name'] == target_class_name]
                if len(filtered_detections) > 0:
                    self.start_recording('detected', 10)
                    self.record_frame(predicted_image)


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
