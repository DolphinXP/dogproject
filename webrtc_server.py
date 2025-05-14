import asyncio
import fractions
import logging
import threading
import time
import uuid
from typing import Dict, Optional

import cv2
import numpy as np
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay
from av import VideoFrame

logger = logging.getLogger("webrtcserver")


class VideoSource:
    """
    视频源类，负责管理当前视频帧
    """

    def __init__(self):
        self.lock = threading.Lock()

        # 初始化测试图案
        self.test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(self.test_frame, "Waiting for camera...", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        self.current_frame = self.test_frame
        self.allow_new_frame = True
        self._last_frame_time = time.time()
        self._frame_count = 0

    def get_test_frame(self):
        """获取测试图案"""
        return self.test_frame

    def set_frame(self, frame):
        """更新视频帧"""
        with self.lock:
            if self.allow_new_frame:
                self.current_frame = frame.copy() if frame is not None else None
                self._frame_count += 1
                self._last_frame_time = time.time()
                self.allow_new_frame = False

    def get_frame(self):
        """获取当前帧"""
        current_time = time.time()

        # 检查帧是否过期
        if current_time - self._last_frame_time > 1.0:
            logger.warning("No new frames received for over 1 second")
            self._last_frame_time = current_time

        with self.lock:
            # 总是返回当前帧，不管allow_new_frame的状态
            frame = self.current_frame.copy() if self.current_frame is not None else None
            # 设置标志允许新帧
            self.allow_new_frame = True

            # 验证帧
            if frame is None or frame.size == 0 or frame.shape[0] > 2304 or frame.shape[1] > 4096:
                logger.error("Frame is None or empty, using test pattern")
                frame = self.get_test_frame()

        # add datetime to left-bottom corner
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cv2.putText(frame, time_str, (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

        return frame, self._frame_count


class VideoStreamTrack(MediaStreamTrack):
    """
    视频轨道类，为每个客户端提供独立的视频轨道
    """
    kind = "video"

    def __init__(self, source: VideoSource, fps=30):
        super().__init__()
        self.source = source
        self.fps = fps
        self._frame_count = 0
        self._start_time = time.time()
        self._last_log_time = 0
        self._stop = False

    async def recv(self):
        """处理帧获取逻辑，每个客户端调用自己的实例"""
        if self._stop:
            logger.info("Track is stopped")
            raise MediaStreamTrack.END_OF_STREAM

        # 限制帧率
        await asyncio.sleep(1.0 / self.fps)

        try:
            # 从源获取当前帧
            frame, source_frame_count = self.source.get_frame()
            self._frame_count += 1

            # 定期日志记录
            current_time = time.time()
            if current_time - self._last_log_time > 5.0:
                elapsed = current_time - self._start_time
                fps = self._frame_count / elapsed if elapsed > 0 else 0
                logger.info(f"Track processing frame {self._frame_count}, FPS: {fps:.2f}")
                self._last_log_time = current_time

            # 创建VideoFrame
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, int(self.fps))

            return video_frame

        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            # 创建应急帧
            emergency_frame = self.source.get_test_frame()

            video_frame = VideoFrame.from_ndarray(emergency_frame, format="rgb24")
            video_frame.pts = self._frame_count
            video_frame.time_base = fractions.Fraction(1, self.fps)

            return video_frame

    def stop(self):
        """停止视频轨道"""
        logger.info("Stopping video track")
        self._stop = True


class WebRTCServer:
    """
    WebRTC服务器，管理多个对等连接
    """

    def __init__(self, fps=30):
        # 视频源
        self.video_source = VideoSource()

        # 主视频轨道
        self.master_track = VideoStreamTrack(self.video_source, fps=fps)

        # WebRTC组件
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.relay = MediaRelay()

        # ICE服务器配置
        self.ice_servers = [
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(urls="stun:stun1.l.google.com:19302"),
        ]

        logger.info("WebRTCServer initialized")

    def set_frame(self, frame):
        """处理来自摄像头源的输入帧"""
        self.video_source.set_frame(frame)

    async def process_offer(self, sdp: str, type_: str, pcId: Optional[str] = None) -> dict:
        """
        处理传入的WebRTC提议并创建应答

        Args:
            sdp: 会话描述协议
            type_: 提议类型
            pcId: 对等连接ID（可选）

        Returns:
            包含SDP应答、类型和pcId的字典
        """
        try:
            # 解析提议
            offer = RTCSessionDescription(sdp=sdp, type=type_)

            # 如果未提供PC ID，则生成
            if pcId is None or pcId not in self.peer_connections:
                pcId = str(uuid.uuid4())
                logger.info(f"Creating new peer connection with ID: {pcId}")
            else:
                logger.info(f"Using existing peer connection with ID: {pcId}")
                # 如果重用，关闭现有连接
                await self.close_connection(pcId)
                # 添加短暂延迟确保资源释放
                await asyncio.sleep(0.1)

            # 创建新的RTCPeerConnection
            rtc_config = RTCConfiguration(iceServers=self.ice_servers)
            pc = RTCPeerConnection(rtc_config)
            self.peer_connections[pcId] = pc

            # 设置连接状态变更处理程序
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection {pcId} state is {pc.connectionState}")
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    logger.info(f"Closing peer connection {pcId} due to {pc.connectionState} state")
                    await self.close_connection(pcId)

            relayed_track = self.relay.subscribe(self.master_track)
            sender = pc.addTrack(relayed_track)
            logger.info(f"Added track to peer connection {pcId}")

            # 设置远程描述
            await pc.setRemoteDescription(offer)
            logger.info(f"Set remote description for {pcId}")

            # 创建应答
            try:
                answer = await pc.createAnswer()
                if answer is None:
                    logger.error("Failed to create answer, answer is None")
                    raise RuntimeError("Failed to create answer")

                # 确保所有收发器都有正确的方向
                for transceiver in pc.getTransceivers():
                    if transceiver.direction is None:
                        transceiver._direction = "sendonly"

                await pc.setLocalDescription(answer)
                logger.info(f"Created and set local description (answer) for {pcId}")

            except Exception as e:
                logger.error(f"Error creating answer for {pcId}: {str(e)}")
                # 尝试回退 - 手动创建最小应答
                if hasattr(pc, "_createAnswer"):
                    try:
                        sdp = await pc._createAnswer()
                        answer = RTCSessionDescription(sdp=sdp, type="answer")
                        await pc.setLocalDescription(answer)
                        logger.info(f"Created and set manual answer as fallback for {pcId}")
                    except Exception as e2:
                        logger.error(f"Fallback also failed for {pcId}: {str(e2)}")
                        raise RuntimeError(f"Failed to create answer: {str(e)}, fallback also failed: {str(e2)}")
                else:
                    raise RuntimeError(f"Failed to create answer: {str(e)}")

            # 返回应答
            return {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "pcId": pcId,
            }

        except Exception as e:
            logger.error(f"Error handling offer: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def get_connection_count(self):
        """返回活动连接数"""
        return len(self.peer_connections)

    async def close_connection(self, pcId: str):
        """关闭特定对等连接"""
        if pcId in self.peer_connections:
            pc = self.peer_connections.pop(pcId)
            logger.info(f"Closing peer connection {pcId}")
            await pc.close()

            self.master_track.stop()

            return True
        return False

    async def close_all_connections(self):
        """关闭所有对等连接"""
        logger.info(f"Closing all WebRTC peer connections ({len(self.peer_connections)})")

        # 关闭所有连接
        coros = [pc.close() for pc in self.peer_connections.values()]
        await asyncio.gather(*coros)

        self.master_track.stop()

        self.tracks.clear()
