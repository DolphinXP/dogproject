import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import time
import fractions

import cv2
import numpy as np
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay, MediaBlackhole
from av import VideoFrame

logger = logging.getLogger("video_server")

# Dictionary to keep track of peer connections
peer_connections = {}
relay = MediaRelay()


class VideoFileTrack(MediaStreamTrack):
    """
    A video track that reads frames from an MP4 file using OpenCV.
    """
    kind = "video"

    def __init__(self, video_file):
        super().__init__()
        self.video_file = video_file
        self.cap = cv2.VideoCapture(video_file)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Check if file opened successfully
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video file: {video_file}")

        logger.info(f"Opened video file: {video_file}, FPS: {self.fps}, Resolution: {self.width}x{self.height}")

        self._stop = False
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0

    async def recv(self):
        if self._stop:
            logger.info("Track is stopped")
            raise MediaStreamTrack.END_OF_STREAM

        # Calculate time to wait based on FPS
        frame_duration = 1.0 / self.fps

        # Read a frame from the video file
        ret, frame = self.cap.read()

        # Log periodically to avoid flooding logs
        current_time = time.time()
        if current_time - self._last_log_time > 1.0:
            logger.info(f"Reading frame {self._frame_count}, ret={ret}, shape={frame.shape if ret else 'None'}")
            self._last_log_time = current_time

        # If we reached the end of the file, restart
        if not ret:
            logger.info("Reached end of video file, restarting")
            self.cap.release()
            self.cap = cv2.VideoCapture(self.video_file)
            ret, frame = self.cap.read()

            # If still can't read a frame, try a test pattern
            if not ret:
                logger.error("Failed to reopen video file, using test pattern")
                # Create a test pattern
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # Add a moving element to confirm it's live
                pos = self._frame_count % 600
                cv2.rectangle(frame, (pos, 200), (pos + 40, 240), (0, 0, 255), -1)

        # Convert BGR to RGB
        try:
            # Check if frame is valid
            if frame is None or frame.size == 0:
                logger.error("Frame is None or empty, using test pattern")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                pos = self._frame_count % 600
                cv2.rectangle(frame, (pos, 200), (pos + 40, 240), (0, 0, 255), -1)

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create VideoFrame object
            video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, int(self.fps))

            # Log frames per second periodically
            elapsed = time.time() - self._start_time
            if elapsed > 0 and self._frame_count % 50 == 0:
                logger.info(f"Current FPS: {self._frame_count / elapsed:.2f}")

            self._frame_count += 1

            # Simulate frame rate by waiting appropriate time
            await asyncio.sleep(frame_duration)

            return video_frame

        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            # Create an emergency frame
            emergency_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(emergency_frame, f"Error: {str(e)}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            video_frame = VideoFrame.from_ndarray(emergency_frame, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, 30)  # Fallback to 30fps

            self._frame_count += 1

            await asyncio.sleep(frame_duration)
            return video_frame

    def stop(self):
        logger.info("Stopping video track")
        self._stop = True
        if self.cap:
            self.cap.release()


async def index(request):
    """Serve the HTML page"""
    with open(os.path.join(os.path.dirname(__file__), "client.html"), "r") as f:
        content = f.read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    """Serve the JavaScript file"""
    with open(os.path.join(os.path.dirname(__file__), "client.js"), "r") as f:
        content = f.read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    """Handle WebRTC offer from browser client"""
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc_id = params.get("pc_id", str(uuid.uuid4()))

        # Set up ICE servers for better NAT traversal
        ice_servers = [
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(urls="stun:stun1.l.google.com:19302"),
        ]

        # Create a new RTCPeerConnection with ICE servers
        pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
        peer_connections[pc_id] = pc

        # Get the video file path from command line arguments
        video_file = request.app["video_file"]

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                # Clean up
                await pc.close()
                if pc_id in peer_connections:
                    del peer_connections[pc_id]

        # Create the video track from the file
        video_track = VideoFileTrack(video_file)
        logger.info(f"Created video track for {video_file}")

        # Add the track to the peer connection
        sender = pc.addTrack(relay.subscribe(video_track))
        logger.info(f"Added track to peer connection")

        # Close old peer connections
        for old_pc_id in list(peer_connections.keys()):
            if old_pc_id != pc_id:
                logger.info(f"Closing old peer connection: {old_pc_id}")
                old_pc = peer_connections[old_pc_id]
                await old_pc.close()
                del peer_connections[old_pc_id]

        # Set the remote description
        await pc.setRemoteDescription(offer)
        logger.info("Set remote description")

        # Create an answer
        try:
            answer = await pc.createAnswer()
            if answer is None:
                logger.error("Failed to create answer, answer is None")
                return web.Response(
                    status=500,
                    text="Failed to create answer"
                )

            # Apply workarounds for mobile devices if needed
            modified_sdp = answer.sdp

            # Make sure all transceivers have a proper direction
            for transceiver in pc.getTransceivers():
                if transceiver.direction is None:
                    transceiver._direction = "sendonly"  # Force direction

            await pc.setLocalDescription(answer)
            logger.info("Created and set local description (answer)")
        except Exception as e:
            logger.error(f"Error creating answer: {str(e)}")
            # Try a workaround - create a minimal answer manually
            if hasattr(pc, "_createAnswer"):
                try:
                    sdp = await pc._createAnswer()
                    answer = RTCSessionDescription(sdp=sdp, type="answer")
                    await pc.setLocalDescription(answer)
                    logger.info("Created and set manual answer as fallback")
                except Exception as e2:
                    logger.error(f"Fallback also failed: {str(e2)}")
                    return web.Response(
                        status=500,
                        text=f"Failed to create answer: {str(e)}, fallback also failed: {str(e2)}"
                    )
            else:
                return web.Response(
                    status=500,
                    text=f"Failed to create answer: {str(e)}"
                )

        # Return the answer to the client
        return web.Response(
            content_type="application/json",
            text=json.dumps({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "pc_id": pc_id,
            })
        )
    except Exception as e:
        logger.error(f"Error handling offer: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return web.Response(
            status=500,
            text=f"Error: {str(e)}"
        )


async def on_shutdown(app):
    """Close all peer connections on shutdown"""
    coros = [pc.close() for pc in peer_connections.values()]
    await asyncio.gather(*coros)
    peer_connections.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC video streaming server")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Create web application
    app = web.Application()
    app["video_file"] = args.video
    app.on_shutdown.append(on_shutdown)

    # Configure routes
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)

    # Run the application
    web.run_app(app, host=args.host, port=args.port)