from myjarvis.core.config import load_config
config = load_config()

from openjarvis.engine._discovery import get_engine

result = get_engine(config, 'nvidia-openai')
print('Result:', result)
if result:
    key, engine = result
    print('Engine:', engine)
else:
    print('Engine not found')
    from openjarvis.core.registry import EngineRegistry
    print('Available:', list(EngineRegistry.keys()))