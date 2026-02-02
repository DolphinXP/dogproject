import cv2
import os
import json
import time
import logging

logger = logging.getLogger("video_recorder")

class VideoRecorder:
    def __init__(self, module_prefix, fps, output_width=640, output_height=480):
        self.module_prefix = module_prefix
        self.fps = fps
        self.output_width = output_width
        self.output_height = output_height
        self.allow_recording = False
        self.video_writer = None
        self.output_folder = None
        self.record_name = None
        self.record_duration = None
        self.record_start_time = None
        self.task_info = None

    def start_recording(self, task_info, output_folder, duration):
        """
        Start recording the video with H.264 codec for HTML5 compatibility.
        """
        if self.video_writer:
            return

        self.task_info = task_info
        self.output_folder = output_folder
        self.record_duration = duration
        self.record_start_time = time.time()

        # Create the output folder if it doesn't exist
        os.makedirs(self.output_folder, exist_ok=True)

        # Generate record_name BEFORE using it
        if self.task_info:
            self.record_name = f"{self.module_prefix}_{self.task_info['taskId']}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        else:
            self.record_name = f"{self.module_prefix}_no-task-id_{time.strftime('%Y%m%d_%H%M%S')}.mp4"

        # Save task info to JSON file
        if self.task_info:
            json_path = os.path.join(self.output_folder, f"{self.record_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.task_info, f, ensure_ascii=False, indent=4)

        # Initialize video writer with H.264 codec
        output_path = os.path.join(self.output_folder, self.record_name)
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # Use H.264 codec
        self.video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.output_width, self.output_height))



    def record_frame(self, frame):
        """
        Write a frame to the video file if recording is active and within the duration limit.
        """
        if not self.video_writer:
            return

        # Validate frame input
        if frame is None or len(frame.shape) < 2:
            logger.warning("Invalid frame received, skipping.")
            return

        elapsed_time = time.time() - self.record_start_time
        if elapsed_time > self.record_duration:
            logger.info("Recording duration reached, stopping recording.")
            self.stop_recording()
            return

        # Only resize if frame size doesn't match
        if frame.shape[:2] != (self.output_height, self.output_width):
            frame = cv2.resize(frame, (self.output_width, self.output_height))
        self.video_writer.write(frame)

    def stop_recording(self):
        """
        Stop recording the video and ensure the file is properly closed.
        """
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            logger.info("Video recording stopped and saved.")