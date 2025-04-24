from fake_camera import FakeCamera
import time
import cv2
import threading
import logging

logger = logging.getLogger("doublefakecamera")

class FrameProcessor(FakeCamera):
    """
    A class that simulates a camera by generating a test pattern and
    allows for double buffering of frames.
    """

    def __init__(self, fps=30):
        super().__init__(fps)
        self._buffer = [None, None]
        self._current_buffer_index = 0
        self._next_buffer_index = 1
        self._stop = False
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0
        self._left_camera = FakeCamera()
        self._right_camera = FakeCamera()
        self.callback = None
        self._thread = None

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

        logger.info("DoubleFakeCamera started")

    def stop(self):
        """
        Stop the double fake camera.
        """
        logger.info("Stopping DoubleFakeCamera")

        self._stop = True
        self._left_camera.stop()
        self._right_camera.stop()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None


    def _process_frames(self):
        """
        Get the current frame from the left camera.
        """
        while not self._stop:
            loop_start = time.time()
            # Get the current frame from the left camera
            left_frame = self._left_camera.get_frame()
            right_frame = self._right_camera.get_frame()

            if left_frame is None or right_frame is None:
                logger.warning("Failed to get frames from cameras")
                continue


            # Combine the frames from both cameras
            combined_frame = self._combine_frames(left_frame, right_frame)

            self.callback(combined_frame)

            processing_time = time.time() - loop_start
            sleep_time = (1.0 / self.fps) - processing_time

            if sleep_time > 0:
                time.sleep(sleep_time)


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