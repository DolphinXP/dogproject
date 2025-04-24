import cv2
import threading
import time
import logging

logger = logging.getLogger("fakecamera")


class FakeCamera():

    def __init__(self, fps=30):
        super(FakeCamera, self).__init__()
        self.name = ""
        self.video_path = None
        self.fps = fps
        self.fpsMs = int(1000 / self.fps)  # Corrected calculation
        self.running = False
        self.capture = None
        self.thread = None
        self._frame_count = 0
        self._start_time = None
        self.callback = None

    def set_frame_callback(self, callback):
        """Set the receiver for the camera"""
        self.callback = callback

    def set_camera_param(self, name, param):
        self.name = name
        self.video_path = param


    def start(self):
        if self.running:
            return

        self.capture = cv2.VideoCapture(self.video_path)

        # Increase buffer size to help with smooth playback
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 3)

        # Get actual FPS from the video file
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            logger.warning(f"{self.name} Invalid FPS from video: {self.fps}, using default 30fps")
            self.fps = 30

        self.fpsMs = int(1000 / self.fps)

        # Check if file opened successfully
        if not self.capture.isOpened():
            raise ValueError(f"{self.name} Could not open video file: {self.video_path}")

        logger.info(f"{self.name} Opened video file: {self.video_path}, FPS: {self.fps}")

        self.running = True
        self._start_time = time.time()
        self._frame_count = 0
        self.thread = threading.Thread(target=self._play_video, daemon=True)
        self.thread.start()
        logger.info(f"{self.name} FakeCamera started")

    def stop(self):
        logger.info(f"{self.name} Stopping FakeCamera")
        self.running = False
        if isinstance(self.thread, threading.Thread) and self.thread.is_alive():
            self.thread.join(timeout=1.0)  # Wait max 1 second
            self.thread = None
        if self.capture:
            self.capture.release()
            self.capture = None

    def _play_video(self):
        last_log_time = 0
        return

        while self.running and self.capture and self.capture.isOpened():
            try:
                loop_start = time.time()

                ret, frame = self.capture.read()

                # Log periodically to avoid flooding logs
                current_time = time.time()
                if current_time - last_log_time > 5.0:  # Log every 5 seconds
                    elapsed = current_time - self._start_time
                    fps = self._frame_count / elapsed if elapsed > 0 else 0
                    logger.info(f"{self.name} FakeCamera: frame {self._frame_count}, fps={fps:.2f}")
                    last_log_time = current_time

                # If we reached the end of the file, restart
                if not ret:
                    logger.info(f"{self.name} Reached end of video file, restarting")
                    self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                if self.running:  # Check again before emitting
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # print(f"Emitting frame {self._frame_count}, shape={frame_rgb.shape}")
                    # self.frame_ready.emit(frame_rgb)
                    self.callback(frame_rgb)
                    self._frame_count += 1


                # Calculate time to sleep to maintain desired framerate
                processing_time = time.time() - loop_start
                sleep_time = (1.0 / self.fps) - processing_time

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"{self.name} Error in video playback: {str(e)}")
                # Add a short delay to avoid CPU spinning on errors
                time.sleep(0.1)

        logger.info(f"{self.name} Video playback thread stopped")

    def get_frame(self, frame_number=None):
        """Get a specific frame or the next frame if frame_number is None"""
        if not self.capture or not self.capture.isOpened():
            return None

        if frame_number is not None:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        ret, frame = self.capture.read()
        if not ret:
            logger.info(f"{self.name} Reached end of video file, restarting")
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.capture.read()

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)