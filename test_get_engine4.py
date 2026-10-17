import openjarvis.engine._discovery as discovery
# Add our engine to _HOST_MAP so _make_engine passes config
discovery._HOST_MAP['nvidia-openai'] = 'nvidia_openai_host'

from myjarvis.core.config import load_config
config = load_config()

from openjarvis.engine._discovery import get_engine, _make_engine
from openjarvis.core.registry import EngineRegistry

print('Registry contains nvidia-openai:', EngineRegistry.contains('nvidia-openai'))
print('Testing get_engine...')
result = get_engine(config, 'nvidia-openai')
print('Result:', result)
if result:
    key, engine = result
    print('Engine:', engine)
else:
    print('Engine not found')