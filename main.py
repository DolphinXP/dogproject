import asyncio
import logging
import threading

import aiohttp_cors
import psutil
from aiohttp import web

from ir_main import ir_main
from vis_main import vis_main

logger = logging.getLogger("main")


async def get_resource_usage():
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }


async def resource_usage_handler(request):
    """Handle WebSocket connections for resource usage updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Use a task to send periodic updates
    update_interval = 2  # seconds

    try:
        while True:
            # Get current resource usage
            usage = await get_resource_usage()

            # Send as JSON
            await ws.send_json(usage)

            # Wait before sending next update
            await asyncio.sleep(update_interval)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Close the WebSocket connection
        if not ws.closed:
            await ws.close()

    return ws


def web_main(host='0.0.0.0', port=8080, verbose=False):
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Create web application
    app = web.Application()
    # app.on_shutdown.append(on_shutdown)

    # Configure routes
    # app.router.add_post("/offer", offer)
    # app.router.add_post("/camera_control", camera_control)
    # app.router.add_get("/status", connection_status)  # Added a status endpoint

    # add a cpu, memory, disk usage websocket endpoint
    app.router.add_get("/resource_usage", resource_usage_handler)  # Updated to a WebSocket endpoint

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
    logger.info(f"Starting server on {host}:{port}")
    web.run_app(app, host=host, port=port, access_log=logger)


if __name__ == "__main__":
    vis_thread = threading.Thread(target=vis_main, args=("d:/test/test.mp4", "0.0.0.0", 8081))
    ir_thread = threading.Thread(target=ir_main, args=("d:/test/test1.mp4", "0.0.0.0", 8082))

    vis_thread.start()
    ir_thread.start()

    web_main()

    vis_thread.join()
    ir_thread.join()
