import os
config_path = os.path.expanduser('~/.myjarvis/config.toml')
print('Config exists:', os.path.exists(config_path))
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        print(f.read())