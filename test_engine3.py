from myjarvis.core.config import load_config
config = load_config()
print('intelligence.engine_config:', getattr(config.intelligence, 'engine_config', 'NOT FOUND'))
print('intelligence.preferred_engine:', config.intelligence.preferred_engine)
print('intelligence.default_model:', config.intelligence.default_model)
print('myjarvis_engine_config:', getattr(config, 'myjarvis_engine_config', 'NOT FOUND'))