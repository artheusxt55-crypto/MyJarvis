import openjarvis.engine._discovery as discovery
# Add our engine to _HOST_MAP so _make_engine passes config
discovery._HOST_MAP['nvidia-openai'] = 'openai_host'

from myjarvis.core.config import load_config
config = load_config()

# Also need to ensure config.engine.openai_host exists
if not hasattr(config.engine, 'openai_host'):
    config.engine.openai_host = 'https://integrate.api.nvidia.com/v1'

from openjarvis.engine._discovery import _make_engine
from openjarvis.core.registry import EngineRegistry

print('Registry contains nvidia-openai:', EngineRegistry.contains('nvidia-openai'))

factory = EngineRegistry.get('nvidia-openai')
engine = factory(config)
print('Engine created:', engine)
print('Engine health:', engine.health())

# Check what _make_engine returns
engine2 = _make_engine('nvidia-openai', config)
print('_make_engine result:', engine2)
print('Engine2 health:', engine2.health() if engine2 else 'None')