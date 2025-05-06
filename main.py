import asyncio
import logging
import os
import threading

import aiohttp_cors
import psutil
from aiohttp import web

from ir_main import ir_main
from vis_main import vis_main

logger = logging.getLogger("main")
websocket_loop = True
update_interval = 2  # seconds


async def resource_usage_handler(request):
    """Handle WebSocket connections for resource usage updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Use a task to send periodic updates

    try:
        while websocket_loop:
            # Get current resource usage
            usage = {
                "cpu": psutil.cpu_percent(interval=1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            }

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


async def detected_compact(request):
    """WebSocket端点，实时返回detected文件夹下的文件列表"""
    import os

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    detected_dir = "detected"
    try:
        while websocket_loop:
            if os.path.exists(detected_dir):
                files = os.listdir(detected_dir)
            else:
                files = []

            result = []
            for file in files:
                fileinfo = os.stat(os.path.join(detected_dir, file))
                result.append({
                    "name": file,
                    "size": fileinfo.st_size,
                    "videoUrl": f"detected/{file}",
                    "ctime": fileinfo.st_ctime,
                    "mtime": fileinfo.st_mtime
                })

            await ws.send_json(result)
            await asyncio.sleep(update_interval)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if not ws.closed:
            await ws.close()
    return ws


async def detected_download(request):
    # Get the file path from the request
    rel_path = request.match_info.get('filename', '')
    abs_path = os.path.join('detected', rel_path)

    # Check if the file exists
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        raise web.HTTPNotFound()

    # Create response with the file
    response = web.FileResponse(abs_path)

    # Add download headers
    filename = os.path.basename(abs_path)
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'

    return response


async def on_shutdown(app):
    """Close all resources on shutdown"""
    logger.info("Shutting down server")
    run_websocket_loop = False

    # Create a custom static file handler


def web_main(host='0.0.0.0', port=8080, verbose=False):
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Create web application
    app = web.Application()
    app.on_shutdown.append(on_shutdown)

    # Configure routes
    app.router.add_get("/resource_usage", resource_usage_handler)
    app.router.add_get("/detected_compact", detected_compact)

    # Add the custom route for files you want to be downloaded
    app.router.add_get('/detected_download/{filename:.*}', detected_download)

    # Regular static files that don't need to be downloaded
    app.router.add_static("/detected/", path="detected", name="detected")

    # Enable CORS for API routes
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Apply CORS to regular routes
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
