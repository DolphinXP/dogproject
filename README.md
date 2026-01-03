  # DogProject — Robot Dog Surveillance

Robot dog surveillance — a collection of Python services and a web UI for camera streaming, perception, and robot control.

Repository: https://github.com/DolphinXP/dogproject
Maintainer: DolphinXP

Status: Template / work in progress — this README was created by scanning the repository. Update the commands and configuration to match your environment and any missing dependency files.

---

## Quick overview

- Primary languages: TypeScript, Python, JavaScript, HTML, CSS
- Focus: live/recorded camera streams, processing pipelines (vision / IR), WebRTC server, and simple tooling for recording/testing.

Top-level files and directories (found in repository root)
- .gitignore
- .idea/ (IDE metadata)
- bak/ (backup directory)
- dogweb/ (web UI / frontend; TypeScript / JS — inspect this directory for package.json / start script)
- lib/ (library / helper code)
- model/ (trained models or assets)
- ir_fake_camera.py
- ir_main.py
- ir_processor.py
- main.py
- run_test.py
- video_recorder.py
- vis_fake_camera.py
- vis_main.py
- vis_processor.py
- webrtc_server.py

---

## Suggested purpose of main scripts

- main.py — probable top-level orchestrator (start here to run full system).
- webrtc_server.py — WebRTC signaling/server for streaming video to browser clients.
- vis_main.py / vis_processor.py — visual (RGB) camera capture + processing pipeline.
- ir_main.py / ir_processor.py — infrared camera capture + processing pipeline.
- vis_fake_camera.py / ir_fake_camera.py — fake camera sources for testing without hardware.
- video_recorder.py — helper to record camera streams to disk.
- run_test.py — small smoke test or example runner.

---

## Prerequisites

- Python 3.8+
- Git
- (For frontend) Node.js 16+ and npm/yarn, if you will run files under `dogweb/`
- (Optional) Docker & docker-compose

Note: This repo does not contain a top-level `requirements.txt` (if present somewhere else, prefer that). Create one from the imports in the scripts. Common packages you may need:
- opencv-python
- numpy
- aiortc (for WebRTC)
- aiohttp / websockets / flask / fastapi (if used by the scripts)
- pyzmq (if using ZMQ messaging)
Install with:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # if you add one
# or install ad-hoc:
pip install opencv-python numpy aiortc aiohttp
```

---

## Example: running the Python services

From repository root:

1. Run the main/orchestration script (if this is the intended entrypoint)
```bash
python main.py
```

2. Run WebRTC server to stream video to a browser
```bash
python webrtc_server.py
```
Open the web UI (see dogweb/), or point a WebRTC-capable client at the signaling endpoint used by the script.

3. Run visual/IR pipelines separately (use fake cameras for testing)
```bash
# Visual processing
python vis_main.py

# Infrared processing
python ir_main.py

# Fake cameras (for local testing without hardware)
python vis_fake_camera.py
python ir_fake_camera.py
```

4. Record a stream
```bash
python video_recorder.py
```

5. Run tests / examples
```bash
python run_test.py
```

Notes:
- Many scripts may accept CLI args or environment variables (camera URLs, ports, log levels). Inspect the top of each .py file or add a `--help` flag if argparse is used:
```bash
python vis_main.py --help
```

---

## Running the web UI (dogweb)

If `dogweb/` contains a typical JS/TS project (package.json):

```bash
cd dogweb
npm install
npm run dev    # or npm start
# Build for production
npm run build
```

The UI commonly connects to the WebRTC/signaling server (webrtc_server.py) and displays camera/telemetry.

---

## Configuration & environment

Create a `.env` or `config` file for runtime configuration. Example variables you might need to set:

- CAMERA_URL (RTSP/HTTP/USB camera device index)
- WEBRTC_PORT / SIGNALING_HOST / SIGNALING_PORT
- API_HOST / API_PORT
- STORAGE_PATH (where recordings are saved)

Keep secrets and credentials out of the repo.

---

## License

MIT
