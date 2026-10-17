
from myjarvis.core.config import load_config
print("Config loaded")
config = load_config()
print("Config:", config.intelligence.default_model)
print("IPC config:", config.myjarvis_ipc)
