import asyncio
import fractions
import logging
import time
import uuid
from typing import Dict, Optional, List
import numpy as np
import cv2
import threading
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
        self._last_frame_time = time.time()
        self._frame_count = 0


    def get_test_frame(self):
        """获取测试图案"""
        return self.test_frame

    def set_frame(self, frame):
        """更新视频帧"""
        with self.lock:
            self.current_frame = frame.copy() if frame is not None else None
            self._frame_count += 1
            self._last_frame_time = time.time()

    def get_frame(self):
        """获取当前帧"""
        current_time = time.time()

        # 检查帧是否过期
        if current_time - self._last_frame_time > 1.0:
            logger.warning("No new frames received for over 1 second")

        with self.lock:
            frame = self.current_frame.copy() if self.current_frame is not None else None

        # 验证帧
        if frame is None or frame.size == 0:
            logger.error("Frame is None or empty, using test pattern")
            frame = self.test_frame

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

            if frame is None or frame.size == 0 or frame.shape[0] > 2304 or frame.shape[1] > 4096:
                logger.error("Frame is None or empty, using test pattern")
                frame = self.source.get_test_frame()

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
        self.fps = fps

        # WebRTC组件
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.tracks: Dict[str, VideoStreamTrack] = {}
        self.relay = MediaRelay()

        # ICE服务器配置
        self.ice_servers = [
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(urls="stun:stun1.l.google.com:19302"),
        ]


        # 启动定期清理任务
        asyncio.run(self._start_cleanup_task())

        logger.info("WebRTCServer initialized")

    def set_frame(self, frame):
        """处理来自摄像头源的输入帧"""
        self.video_source.set_frame(frame)

    async def process_offer(self, sdp: str, type_: str, pc_id: Optional[str] = None) -> dict:
        """
        处理传入的WebRTC提议并创建应答

        Args:
            sdp: 会话描述协议
            type_: 提议类型
            pc_id: 对等连接ID（可选）

        Returns:
            包含SDP应答、类型和pc_id的字典
        """
        try:
            # 解析提议
            offer = RTCSessionDescription(sdp=sdp, type=type_)

            # 如果未提供PC ID，则生成
            if pc_id is None or pc_id not in self.peer_connections:
                pc_id = str(uuid.uuid4())
                logger.info(f"Creating new peer connection with ID: {pc_id}")
            else:
                logger.info(f"Using existing peer connection with ID: {pc_id}")
                # 如果重用，关闭现有连接
                await self.close_connection(pc_id)
                # 添加短暂延迟确保资源释放
                await asyncio.sleep(0.1)

            # 创建新的RTCPeerConnection
            rtc_config = RTCConfiguration(iceServers=self.ice_servers)
            pc = RTCPeerConnection(rtc_config)
            self.peer_connections[pc_id] = pc

            # 设置连接状态变更处理程序
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection {pc_id} state is {pc.connectionState}")
                if pc.connectionState == "failed" or pc.connectionState == "closed":
                    logger.info(f"Closing peer connection {pc_id} due to {pc.connectionState} state")
                    await self.close_connection(pc_id)

            # 为此连接创建新的视频轨道
            track = VideoStreamTrack(self.video_source, self.fps)
            self.tracks[pc_id] = track

            # 添加轨道到对等连接
            # 使用relay为每个客户端创建独立轨道副本
            relayed_track = self.relay.subscribe(track)
            sender = pc.addTrack(relayed_track)
            logger.info(f"Added track to peer connection {pc_id}")

            # 设置远程描述
            await pc.setRemoteDescription(offer)
            logger.info(f"Set remote description for {pc_id}")

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
                logger.info(f"Created and set local description (answer) for {pc_id}")

            except Exception as e:
                logger.error(f"Error creating answer for {pc_id}: {str(e)}")
                # 尝试回退 - 手动创建最小应答
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

            # 返回应答
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
        """返回活动连接数"""
        return len(self.peer_connections)

    async def close_connection(self, pc_id: str):
        """关闭特定对等连接"""
        if pc_id in self.peer_connections:
            pc = self.peer_connections.pop(pc_id)
            logger.info(f"Closing peer connection {pc_id}")
            await pc.close()

            # 停止并清理相应的轨道
            if pc_id in self.tracks:
                track = self.tracks.pop(pc_id)
                track.stop()

            return True
        return False

    async def close_all_connections(self):
        """关闭所有对等连接"""
        logger.info(f"Closing all WebRTC peer connections ({len(self.peer_connections)})")

        # 关闭所有连接
        coros = [pc.close() for pc in self.peer_connections.values()]
        await asyncio.gather(*coros)

        # 停止所有轨道
        for track in self.tracks.values():
            track.stop()

        self.peer_connections.clear()
        self.tracks.clear()

    async def _start_cleanup_task(self):
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """
        定期检查并清理断开的连接，
        处理超时连接
        """
        try:
            while True:
                await asyncio.sleep(30)  # 每30秒检查一次

                try:
                    current_time = time.time()
                    # 复制连接ID，因为我们将修改字典
                    pc_ids = list(self.peer_connections.keys())

                    for pc_id in pc_ids:
                        # 跳过正在关闭的连接
                        if pc_id in self.closing_connections:
                            continue

                        pc = self.peer_connections.get(pc_id)
                        if not pc:
                            continue

                        # 检查连接状态
                        if pc.connectionState in ["failed", "closed", "disconnected"]:
                            logger.info(f"Cleanup: Closing {pc_id[:8]} in state {pc.connectionState}")
                            await self.close_connection(pc_id)
                            continue

                        # 检查连接超时（5分钟未活动）
                        last_activity = self.connection_timestamps.get(pc_id, 0)
                        if current_time - last_activity > 300:  # 5分钟
                            logger.info(f"Cleanup: Connection {pc_id[:8]} timed out (inactive for 5 minutes)")
                            await self.close_connection(pc_id)

                    # 日志记录当前状态
                    if self.peer_connections:
                        active_conn_count = len(self.peer_connections)
                        closing_conn_count = len(self.closing_connections)
                        logger.info(f"Active connections: {active_conn_count}, Closing: {closing_conn_count}")

                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {str(e)}")

        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in cleanup task: {str(e)}")
