import asyncio
import fractions
import logging
import time
import uuid
from typing import Dict, Optional, Callable
import numpy as np
import cv2
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay
from av import VideoFrame

logger = logging.getLogger("webrtcserver")


class WebRTCServer(MediaStreamTrack):
    """
    A WebRTC server that handles video streaming and multiple peer connections.
    """
    kind = "video"

    def __init__(self, fps=30):
        super().__init__()
        # Video frame handling
        self.current_frame = None
        self.fps = fps
        self._new_frame_available = False
        self._last_frame_time = time.time()
        self._stop = False
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0

        # WebRTC components
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.relay = MediaRelay()

        # ICE servers configuration
        self.ice_servers = [
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(urls="stun:stun1.l.google.com:19302"),
        ]

        # Generate initial test pattern frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(test_frame, "Waiting for camera...", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        self.current_frame = test_frame

        logger.info("WebRTCServer initialized")

    def set_frame(self, frame):
        """Handle incoming frame from the camera source"""
        if not self._stop:
            self.current_frame = frame
            self._frame_count += 1
            self._new_frame_available = True
            self._last_frame_time = time.time()

    async def recv(self):
        """Handle frame retrieval for the video track"""
        if self._stop:
            logger.info("Track is stopped")
            raise MediaStreamTrack.END_OF_STREAM

        # Check for stale frames
        current_time = time.time()
        if current_time - self._last_frame_time > 1.0:
            if current_time - self._last_log_time > 5.0:
                logger.warning("No new frames received for over 1 second")
                self._last_log_time = current_time

        # Throttle to reduce CPU usage
        await asyncio.sleep(1.0 / 30)

        try:
            frame = self.current_frame

            # Periodic logging
            if current_time - self._last_log_time > 5.0:
                logger.info(f"Processing frame {self._frame_count}, "
                            f"shape={frame.shape if frame is not None else 'None'}")
                elapsed = current_time - self._start_time
                fps = self._frame_count / elapsed if elapsed > 0 else 0
                logger.info(f"WebRTC FPS: {fps:.2f}")
                logger.info(f"Active connections: {len(self.peer_connections)}")
                self._last_log_time = current_time

            self._new_frame_available = False

            # Validate frame
            if frame is None or frame.size == 0:
                logger.error("Frame is None or empty, using test pattern")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                pos = self._frame_count % 600
                cv2.rectangle(frame, (pos, 200), (pos + 40, 240), (0, 0, 255), -1)

            # Create VideoFrame
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, int(self.fps))

            return video_frame

        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            # Create emergency frame
            emergency_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(emergency_frame, f"Error: {str(e)}", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            video_frame = VideoFrame.from_ndarray(emergency_frame, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, 30)

            return video_frame

    async def process_offer(self, sdp: str, type_: str, pc_id: Optional[str] = None) -> dict:
        """
        Process an incoming WebRTC offer and create an answer

        Args:
            sdp: Session Description Protocol
            type_: Offer type
            pc_id: Peer connection ID (optional)

        Returns:
            Dict with SDP answer, type and pc_id
        """
        try:
            # Parse the offer
            offer = RTCSessionDescription(sdp=sdp, type=type_)

            # Generate PC ID if not provided
            if pc_id is None or pc_id not in self.peer_connections:
                pc_id = str(uuid.uuid4())
                logger.info(f"Creating new peer connection with ID: {pc_id}")
            else:
                logger.info(f"Using existing peer connection with ID: {pc_id}")
                # Close existing connection if it's being reused
                old_pc = self.peer_connections.pop(pc_id)
                await old_pc.close()

            # Create a new RTCPeerConnection
            rtc_config = RTCConfiguration(iceServers=self.ice_servers)
            pc = RTCPeerConnection(rtc_config)
            self.peer_connections[pc_id] = pc

            # Set up connection state change handler
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection {pc_id} state is {pc.connectionState}")
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    logger.info(f"Closing peer connection {pc_id} due to {pc.connectionState} state")
                    await pc.close()
                    if pc_id in self.peer_connections:
                        del self.peer_connections[pc_id]

            # Add the track to the peer connection
            sender = pc.addTrack(self.relay.subscribe(self))
            logger.info(f"Added track to peer connection {pc_id}")

            # Set the remote description
            await pc.setRemoteDescription(offer)
            logger.info(f"Set remote description for {pc_id}")

            # Create an answer
            try:
                answer = await pc.createAnswer()
                if answer is None:
                    logger.error("Failed to create answer, answer is None")
                    raise RuntimeError("Failed to create answer")

                # Ensure all transceivers have a proper direction
                for transceiver in pc.getTransceivers():
                    if transceiver.direction is None:
                        transceiver._direction = "sendonly"

                await pc.setLocalDescription(answer)
                logger.info(f"Created and set local description (answer) for {pc_id}")

            except Exception as e:
                logger.error(f"Error creating answer for {pc_id}: {str(e)}")
                # Try fallback - create a minimal answer manually
                if hasattr(pc, "_createAnswer"):
                    try:
                        sdp = await pc._createAnswer()
                        answer = RTCSessionDescription(sdp=sdp, type="answer")
                        await pc.setLocalDescription(answer)
                        logger.info(f"Created and set manual answer as fallback for {pc_id}")
                    except Exception as e2:
                        logger.error(f"Fallback also failed for {pc_id}: {str(e2)}")
                        raise RuntimeError(f"Failed to create answer: {str(e)}, fallback also failed: {str(e2)}")
                else:
                    raise RuntimeError(f"Failed to create answer: {str(e)}")

            # Return the answer
            return {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "pc_id": pc_id,
            }

        except Exception as e:
            logger.error(f"Error handling offer: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def get_connection_count(self):
        """Return the number of active connections"""
        return len(self.peer_connections)

    async def close_connection(self, pc_id: str):
        """Close a specific peer connection"""
        if pc_id in self.peer_connections:
            pc = self.peer_connections.pop(pc_id)
            logger.info(f"Closing peer connection {pc_id}")
            await pc.close()
            return True
        return False

    async def close_all_connections(self):
        """Close all peer connections"""
        logger.info(f"Closing all WebRTC peer connections ({len(self.peer_connections)})")
        coros = [pc.close() for pc in self.peer_connections.values()]
        await asyncio.gather(*coros)
        self.peer_connections.clear()

    def stop(self):
        """Stop the video track"""
        logger.info("Stopping WebRTC track")
        self._stop = True