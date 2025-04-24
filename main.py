import argparse
import asyncio
import json
import logging
import os
import sys
import aiohttp_cors
from aiohttp import web

# Import your classes
from frame_processor import FrameProcessor
from webrtc_server import WebRTCServer

logger = logging.getLogger("video_server")

# Global video server instance
webrtc_server = None
double_fake_camera = None


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
    global webrtc_server

    try:
        params = await request.json()

        # Process the offer using WebRTCServer class
        response = await webrtc_server.process_offer(
            sdp=params["sdp"],
            type_=params["type"],
            pc_id=params.get("pc_id")
        )

        return web.Response(
            content_type="application/json",
            text=json.dumps(response)
        )
    except Exception as e:
        logger.error(f"Error handling offer: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return web.Response(
            status=500,
            text=f"Error: {str(e)}"
        )

async def camera_control(request):
    """Handle camera control commands"""
    global double_fake_camera

    try:
        params = await request.json()
        command = params.get("command")

        if command == "start":
            double_fake_camera.start()
            return web.Response(text="Camera started")
        elif command == "stop":
            double_fake_camera.stop()
            return web.Response(text="Camera stopped")
        else:
            return web.Response(status=400, text="Invalid command")
    except Exception as e:
        logger.error(f"Error handling camera control: {str(e)}")
        return web.Response(status=500, text=f"Error: {str(e)}")

async def connection_status(request):
    """Return the number of active connections"""
    global webrtc_server

    count = webrtc_server.get_connection_count()
    return web.Response(
        content_type="application/json",
        text=json.dumps({"connections": count})
    )


async def on_shutdown(app):
    """Close all resources on shutdown"""
    global webrtc_server, double_fake_camera

    logger.info("Shutting down server")
    if webrtc_server:
        await webrtc_server.close_all_connections()

    if double_fake_camera:
        double_fake_camera.stop()


def main():
    global webrtc_server, double_fake_camera

    parser = argparse.ArgumentParser(description="WebRTC video streaming server")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Initialize WebRTC server
    webrtc_server = WebRTCServer(fps=30)
    logger.info(f"Created WebRTCServer")

    # Initialize camera with video file
    double_fake_camera = FrameProcessor(fps=30)
    double_fake_camera.set_camera_param(args.video)
    logger.info(f"FakeCamera created for {args.video}")
    double_fake_camera.set_frame_callback(webrtc_server.set_frame)
    double_fake_camera.start()

    # Create web application
    app = web.Application()
    app.on_shutdown.append(on_shutdown)

    # Configure routes
    # app.router.add_get("/", index)
    # app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    app.router.add_post("/camera_control", camera_control)
    app.router.add_get("/status", connection_status)  # Added a status endpoint

    # Enable CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

    # Run the application
    logger.info(f"Starting WebRTC server on {args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port, access_log=logger)


if __name__ == "__main__":
    main()