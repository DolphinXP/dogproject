import json
import logging
import traceback

import aiohttp_cors
from aiohttp import web

from ir_processor import IRProcessor
from webrtc_server import WebRTCServer

logger = logging.getLogger("ir_main")

# Global video server instance
webrtc_server = None
ir_processor = None


async def offer(request):
    """Handle WebRTC offer from browser client"""
    global webrtc_server
    global ir_processor

    try:
        params = await request.json()

        taskInfo = params["taskInfo"]
        ir_processor.set_task_info(taskInfo)

        # Process the offer using WebRTCServer class
        response = await webrtc_server.process_offer(
            sdp=params["sdp"],
            type_=params["type"],
            pcId=params.get("pcId")
        )

        return web.Response(
            content_type="application/json",
            text=json.dumps(response)
        )
    except Exception as e:
        logger.error(f"Error handling offer: {str(e)}")
        logger.error(traceback.format_exc())
        return web.Response(
            status=500,
            text=f"Error: {str(e)}"
        )


async def camera_control(request):
    """Handle camera control commands"""
    global ir_processor

    try:
        params = await request.json()
        command = params.get("command")

        if command == "start":
            ir_processor.start()
            return web.Response(text="Camera started")
        elif command == "stop":
            ir_processor.stop()
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
    global webrtc_server, ir_processor

    logger.info("Shutting down server")
    if webrtc_server:
        await webrtc_server.close_all_connections()

    if ir_processor:
        ir_processor.stop()


def ir_main(video, host='0.0.0.0', port=8082, verbose=False):
    global webrtc_server, ir_processor

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Initialize WebRTC server
    webrtc_server = WebRTCServer()
    logger.info(f"Created WebRTCServer")

    # Initialize camera with video file
    ir_processor = IRProcessor(fps=30)
    ir_processor.set_camera_param(video)
    logger.info(f"FakeCamera created for {video}")
    ir_processor.set_frame_callback(webrtc_server.set_frame)
    ir_processor.start()

    # Create web application
    app = web.Application()
    app.on_shutdown.append(on_shutdown)

    # Configure routes
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
    logger.info(f"Starting IR WebRTC server on {host}:{port}")
    web.run_app(app, host=host, port=port, access_log=logger)


if __name__ == "__main__":
    ir_main(video="")
