from openjarvis.engine._discovery import get_engine
from openjarvis.core.config import load_config

config = load_config()
print('Config intelligence:', config.intelligence)
print('Config intelligence.engine_config:', getattr(config.intelligence, 'engine_config', None))

result = get_engine(config, 'nvidia-openai')
print('Result:', result)
if result:
    key, engine = result
    print('Engine:', engine)
else:
    print('Engine not found')
    from openjarvis.core.registry import EngineRegistry
    print('Available:', list(EngineRegistry.keys()))