import {Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {Button} from 'primeng/button';

@Component({
  selector: 'app-vis-view',
  imports: [
    Button
  ],
  templateUrl: './vis-view.component.html',
  styleUrl: './vis-view.component.css'
})
export class VisViewComponent implements OnInit, OnDestroy {
  @ViewChild('statusIndicator') statusIndicator!: ElementRef;
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('videoInfo') videoInfo!: ElementRef;
  @ViewChild('logElement') logElement!: ElementRef;

  peerConnection: RTCPeerConnection | null = null;
  pcId: string | null = null;
  mediaStream: MediaStream | null = null;
  statsInterval: any = null;
  isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  ngOnInit() {
    this.updateStatus('Not connected');
    this.log(`页面已加载。设备: ${this.isMobile ? 'Mobile' : 'Desktop'}。点击“Connect to Stream”开始。`);
  }

  ngOnDestroy() {
    this.closeConnection();
  }

  updateStatus(status: string) {
    if (this.statusIndicator) {
      this.statusIndicator.nativeElement.textContent = `Status: ${status}`;
    }
  }

  log(message: string) {
    console.log(message);
    if (this.logElement) {
      const logLine = document.createElement('div');
      logLine.textContent = `${new Date().toLocaleTimeString()}: ${message}`;
      this.logElement.nativeElement.appendChild(logLine);
      while (this.logElement.nativeElement.children.length > 50) {
        this.logElement.nativeElement.removeChild(this.logElement.nativeElement.firstChild);
      }
      this.logElement.nativeElement.scrollTop = this.logElement.nativeElement.scrollHeight;
    }
  }

  async connectToStream() {
    try {
      this.updateStatus('Connecting...');
      this.log(`创建 peer connection (mobile: ${this.isMobile})...`);
      const ICE_SERVERS = {
        iceServers: [
          {urls: 'stun:stun.l.google.com:19302'},
          {urls: 'stun:stun1.l.google.com:19302'},
        ]
      };
      this.peerConnection = new RTCPeerConnection(ICE_SERVERS);

      this.peerConnection.addEventListener('track', (event) => this.handleTrack(event));
      this.peerConnection.addEventListener('icecandidate', (event) => this.handleIceCandidate(event));
      this.peerConnection.addEventListener('connectionstatechange', () => this.handleConnectionStateChange());
      this.peerConnection.addEventListener('iceconnectionstatechange', () => this.handleIceConnectionStateChange());
      this.peerConnection.addEventListener('signalingstatechange', () => this.handleSignalingStateChange());

      if (this.isMobile) {
        this.log('为移动设备添加 video transceiver');
        this.peerConnection.addTransceiver('video', {direction: 'recvonly'});
      }

      const offerOptions = {offerToReceiveVideo: true, offerToReceiveAudio: false};
      const offer = await this.peerConnection.createOffer(offerOptions);
      this.log(`Offer created, SDP type: ${offer.type}`);

      await this.peerConnection.setLocalDescription(offer);
      this.log('本地描述已设置，发送 offer 到服务器...');

      const response = await fetch('http://31.41.59.100:8080/offer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          sdp: this.peerConnection.localDescription!.sdp,
          type: this.peerConnection.localDescription!.type,
          pc_id: this.pcId,
          is_mobile: this.isMobile
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }

      const answer = await response.json();
      this.pcId = answer.pc_id;
      this.log(`收到服务器应答 (PC ID: ${this.pcId})`);

      await this.peerConnection.setRemoteDescription(new RTCSessionDescription({
        sdp: answer.sdp,
        type: answer.type
      }));
      this.log('远端描述设置成功');

      this.updateStatus('Waiting for media...');
      this.startStatsLogging();
    } catch (error: any) {
      this.log(`连接错误: ${error.message}`);
      this.updateStatus(`Error: ${error.message}`);
      this.closeConnection();
    }
  }

  startStatsLogging() {
    if (this.statsInterval) clearInterval(this.statsInterval);
    this.statsInterval = setInterval(async () => {
      if (!this.peerConnection) return;
      try {
        const stats = await this.peerConnection.getStats();
        let hasInboundVideo = false;
        stats.forEach((stat: any) => {
          if (stat.type === 'inbound-rtp' && stat.kind === 'video') {
            hasInboundVideo = true;
            this.log(`视频统计: received=${stat.packetsReceived}, decoded=${stat.framesDecoded}, dropped=${stat.framesDropped}, fps=${stat.framesPerSecond || 'N/A'}`);
          }
        });
        if (!hasInboundVideo) this.log('暂无视频统计');
      } catch (e: any) {
        this.log(`获取统计信息出错: ${e.message}`);
      }
    }, 5000);
  }

  handleSignalingStateChange() {
    this.log(`信令状态: ${this.peerConnection?.signalingState}`);
  }

  handleTrack(event: RTCTrackEvent) {
    this.log(`收到 track: ${event.track.kind}, id=${event.track.id}, enabled=${event.track.enabled}`);
    if (event.track.kind === 'video') {
      this.mediaStream = event.streams[0] || new MediaStream([event.track]);
      this.videoElement.nativeElement.srcObject = this.mediaStream;
      this.log(`设置视频流: tracks=${this.mediaStream.getTracks().length}, active=${this.mediaStream.active}`);
      this.videoElement.nativeElement.onloadedmetadata = () => {
        this.videoInfo.nativeElement.textContent = `分辨率: ${this.videoElement.nativeElement.videoWidth}x${this.videoElement.nativeElement.videoHeight}`;
        this.log(`视频尺寸: ${this.videoElement.nativeElement.videoWidth}x${this.videoElement.nativeElement.videoHeight}`);
        this.updateStatus('Streaming');
      };
    }
  }

  handleIceCandidate(event: RTCPeerConnectionIceEvent) {
    if (event.candidate) {
      this.log(`ICE candidate: ${event.candidate.candidate.split(' ')[0]}`);
    }
  }

  handleConnectionStateChange() {
    this.log(`连接状态: ${this.peerConnection?.connectionState}`);
    if (['disconnected', 'failed', 'closed'].includes(this.peerConnection?.connectionState || '')) {
      this.updateStatus(`Disconnected (${this.peerConnection?.connectionState})`);
      this.closeConnection();
    } else if (this.peerConnection?.connectionState === 'connected') {
      this.updateStatus('Connected');
    }
  }

  handleIceConnectionStateChange() {
    this.log(`ICE 连接状态: ${this.peerConnection?.iceConnectionState}`);
  }

  closeConnection() {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
      this.statsInterval = null;
    }
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.videoElement) {
      this.videoElement.nativeElement.srcObject = null;
    }
    this.log('连接已关闭');
  }

  async startCamera() {
    await fetch('http://31.41.59.100:8080/camera_control', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: 'start'})
    });
  }

  async stopCamera() {
    await fetch('http://31.41.59.100:8080/camera_control', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: 'stop'})
    });
  }


  preventPause(event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    // 立即播放，防止暂停
    const video = event.target as HTMLVideoElement;
    if (video.paused) {
      video.play();
    }
  }

  disableContextMenu(event: MouseEvent) {
    event.preventDefault();
  }
}
