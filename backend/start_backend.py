import sys
import asyncio
import uvicorn

# Required for Playwright on Windows because Chromium is launched as a subprocess.
# This must be set before Uvicorn creates the event loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        loop="asyncio",
    )
