
import asyncio
from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis

async def test():
    config = load_config()
    jarvis = MyJarvis(config=config)
    print("MyJarvis created")
    print("Starting IPC...")
    await jarvis.start_ipc()
    print("IPC started!")
    await jarvis.stop_ipc()
    print("IPC stopped!")
    jarvis.close()

asyncio.run(test())
