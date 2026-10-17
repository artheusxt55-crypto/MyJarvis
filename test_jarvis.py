
from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis
print("Creating MyJarvis...")
config = load_config()
jarvis = MyJarvis(config=config)
print("MyJarvis created!")
print("IPC bridge:", jarvis.ipc_bridge)
print("Engine key:", jarvis._resolved_engine_key)
