// DOM elements
const statusIndicator = document.getElementById('statusIndicator');
const connectButton = document.getElementById('connectButton');
const videoElement = document.getElementById('videoElement');
const videoInfo = document.getElementById('videoInfo');
const logElement = document.getElementById('log');

// WebRTC variables
let peerConnection = null;
let pcId = null;
let mediaStream = null;

// Configuration
const ICE_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
    ]
};

// Track stream stats
let statsInterval = null;

// Check if this is a mobile device
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

// Log functionality
function log(message) {
    console.log(message);
    const logLine = document.createElement('div');
    logLine.textContent = `${new Date().toLocaleTimeString()}: ${message}`;
    logElement.appendChild(logLine);

    // Keep log from getting too long
    while (logElement.children.length > 50) {
        logElement.removeChild(logElement.firstChild);
    }

    // Auto-scroll to bottom
    logElement.scrollTop = logElement.scrollHeight;
}

// Update status indicator
function updateStatus(status) {
    statusIndicator.textContent = `Status: ${status}`;
}

// Connect to the server and establish WebRTC connection
async function connectToStream() {
    try {
        updateStatus('Connecting...');
        log(`Creating peer connection (mobile: ${isMobile})...`);

        // Create RTCPeerConnection
        peerConnection = new RTCPeerConnection(ICE_SERVERS);

        // Set up event handlers
        peerConnection.addEventListener('track', handleTrack);
        peerConnection.addEventListener('icecandidate', handleIceCandidate);
        peerConnection.addEventListener('connectionstatechange', handleConnectionStateChange);
        peerConnection.addEventListener('iceconnectionstatechange', handleIceConnectionStateChange);
        peerConnection.addEventListener('signalingstatechange', handleSignalingStateChange);

        // Add transceivers for mobile devices
        if (isMobile) {
            log("Adding video transceiver for mobile device");
            peerConnection.addTransceiver('video', {direction: 'recvonly'});
        }

        // Create offer with specific codec preferences
        const offerOptions = {
            offerToReceiveVideo: true,
            offerToReceiveAudio: false
        };

        const offer = await peerConnection.createOffer(offerOptions);
        log(`Offer created, SDP type: ${offer.type}`);

        // Modify SDP for better compatibility with various devices if needed
        let sdp = offer.sdp;

        // Apply the modified SDP
        const modifiedOffer = new RTCSessionDescription({
            type: offer.type,
            sdp: sdp
        });

        await peerConnection.setLocalDescription(modifiedOffer);
        log('Local description set, sending offer to server...');

        // Send offer to server
        const response = await fetch('http://31.41.59.100:8080/offer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sdp: peerConnection.localDescription.sdp,
                type: peerConnection.localDescription.type,
                pc_id: pcId,
                is_mobile: isMobile
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        // Process server response
        const answer = await response.json();
        pcId = answer.pc_id;

        log(`Received answer from server (PC ID: ${pcId})`);

        try {
            // Apply the remote description
            await peerConnection.setRemoteDescription(new RTCSessionDescription({
                sdp: answer.sdp,
                type: answer.type
            }));
            log('Remote description set successfully');
        } catch (e) {
            log(`Error setting remote description: ${e.message}`);
            // Try to handle Safari/iOS specific issues
            if (isMobile && e.message.includes('setRemoteDescription')) {
                log('Attempting fallback for mobile device...');
                // Add a slight delay and try again
                await new Promise(resolve => setTimeout(resolve, 500));
                await peerConnection.setRemoteDescription(new RTCSessionDescription({
                    sdp: answer.sdp,
                    type: answer.type
                }));
                log('Remote description set with fallback method');
            } else {
                throw e;
            }
        }

        connectButton.disabled = true;
        updateStatus('Waiting for media...');

        // Special handling for iOS
        if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
            log('iOS device detected, adding special handling');
            videoElement.playsInline = true;
            videoElement.controls = true;

            // Auto-play workaround for iOS
            document.addEventListener('touchstart', () => {
                videoElement.play().catch(e => log(`iOS autoplay error: ${e.message}`));
            }, { once: true });
        }

        // Start logging stats
        startStatsLogging();
    } catch (error) {
        log(`Connection error: ${error.message}`);
        updateStatus(`Error: ${error.message}`);
        closeConnection();
    }
}

// Start logging WebRTC stats periodically
function startStatsLogging() {
    if (statsInterval) {
        clearInterval(statsInterval);
    }

    statsInterval = setInterval(async () => {
        if (!peerConnection) return;

        try {
            const stats = await peerConnection.getStats();
            let videoStats = null;
            let hasInboundVideo = false;

            stats.forEach(stat => {
                if (stat.type === 'inbound-rtp' && stat.kind === 'video') {
                    hasInboundVideo = true;
                    videoStats = stat;
                    log(`Video stats: received=${stat.packetsReceived}, decoded=${stat.framesDecoded}, dropped=${stat.framesDropped}, fps=${stat.framesPerSecond || 'N/A'}`);
                }
            });

            if (!hasInboundVideo) {
                log('No inbound video stats available yet');
            }
        } catch (e) {
            log(`Error getting stats: ${e.message}`);
        }
    }, 5000); // Log stats every 5 seconds
}

// Handle signaling state changes
function handleSignalingStateChange() {
    log(`Signaling state: ${peerConnection.signalingState}`);
}

// Handle incoming media tracks
function handleTrack(event) {
    log(`Received track: ${event.track.kind}, id=${event.track.id}, enabled=${event.track.enabled}`);

    if (event.track.kind === 'video') {
        if (!event.streams || event.streams.length === 0) {
            log('WARNING: Track received without associated stream, creating new stream');
            // Create a new MediaStream if none provided
            mediaStream = new MediaStream([event.track]);
        } else {
            mediaStream = event.streams[0];
            log(`Stream received: id=${mediaStream.id}, tracks=${mediaStream.getTracks().length}`);
        }

        // Attach stream to video element
        videoElement.srcObject = mediaStream;
        log(`Set stream to video element: tracks=${mediaStream.getTracks().length}, active=${mediaStream.active}`);

        // Force play for mobile devices
        if (isMobile) {
            try {
                videoElement.play().catch(e => {
                    log(`Error playing video: ${e.message}`);
                    // Add play button for iOS
                    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
                        const playButton = document.createElement('button');
                        playButton.textContent = 'Play Video';
                        playButton.style.position = 'absolute';
                        playButton.style.top = '50%';
                        playButton.style.left = '50%';
                        playButton.style.transform = 'translate(-50%, -50%)';
                        playButton.style.zIndex = '1000';
                        playButton.onclick = () => {
                            videoElement.play().catch(e => log(`Play error: ${e.message}`));
                            playButton.remove();
                        };
                        document.getElementById('videoContainer').appendChild(playButton);
                    }
                });
            } catch (e) {
                log(`Error starting video playback: ${e.message}`);
            }
        }

        // Update video info when metadata is loaded
        videoElement.onloadedmetadata = () => {
            videoInfo.textContent = `Resolution: ${videoElement.videoWidth}x${videoElement.videoHeight}`;
            log(`Video dimensions: ${videoElement.videoWidth}x${videoElement.videoHeight}`);
            updateStatus('Streaming');
        };

        // Add more video element event handlers
        videoElement.onplay = () => log('Video playback started');
        videoElement.onpause = () => log('Video playback paused');
        videoElement.onwaiting = () => log('Video waiting for data');
        videoElement.onplaying = () => log('Video is playing');
        videoElement.oncanplay = () => log('Video can play');
        videoElement.oncanplaythrough = () => log('Video can play through');

        // Handle video errors
        videoElement.onerror = () => {
            const error = videoElement.error;
            log(`Video error: ${error.code} - ${error.message || 'Unknown error'}`);
        };

        // Handle video ended
        videoElement.onended = () => {
            log('Video stream ended');
            updateStatus('Stream ended');
            closeConnection();
        };
    }
}

// Handle ICE candidates
function handleIceCandidate(event) {
    if (event.candidate) {
        log(`ICE candidate: ${event.candidate.candidate.split(' ')[0]}`);
    }
}

// Handle connection state changes
function handleConnectionStateChange() {
    log(`Connection state: ${peerConnection.connectionState}`);

    if (peerConnection.connectionState === 'connected') {
        updateStatus('Connected');
    } else if (peerConnection.connectionState === 'disconnected' ||
               peerConnection.connectionState === 'failed' ||
               peerConnection.connectionState === 'closed') {
        updateStatus(`Disconnected (${peerConnection.connectionState})`);
        closeConnection();
    }
}

// Handle ICE connection state changes
function handleIceConnectionStateChange() {
    log(`ICE connection state: ${peerConnection.iceConnectionState}`);
}

// Close WebRTC connection
function closeConnection() {
    // Stop stats interval
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }

    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    videoElement.srcObject = null;
    connectButton.disabled = false;
    log('Connection closed');
}

// Event listeners
connectButton.addEventListener('click', connectToStream);
startCamera.addEventListener('click', () => {
    const response =  fetch('http://31.41.59.100:8080/cameraControl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: 'start',
                })
            });
});
stopCamera.addEventListener('click', () => {
    const response =  fetch('http://31.41.59.100:8080/cameraControl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: 'stop',
                })
            });
});

// Initialize page
updateStatus('Not connected');
log(`Page loaded. Device: ${isMobile ? 'Mobile' : 'Desktop'}. Click "Connect to Stream" to start.`);

// Handle page unload
window.addEventListener('beforeunload', () => {
    closeConnection();
});