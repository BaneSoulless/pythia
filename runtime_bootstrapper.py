"""
Runtime Bootstrapper
SOTA 2026

Auto-heals missing Node.js environment by downloading a portable binary.
"""
import os
import sys
import platform
import zipfile
import urllib.request
import shutil
import subprocess
NODE_VERSION = 'v20.11.0'
BASE_URL = 'https://nodejs.org/dist/'
RUNTIME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.runtime')

def setup_node_env():
    """Download Node.js if missing and return modified environment variables."""
    if platform.system() != 'Windows' or platform.machine().lower() not in ['amd64', 'x86_64']:
        print('    [BOOTSTRAP] Warning: This script is optimized for Windows x64. Skipping download.')
        return os.environ.copy()
    target_node_dir = os.path.join(RUNTIME_DIR, 'node')
    npm_path = os.path.join(target_node_dir, 'npm.cmd')
    if os.path.exists(npm_path):
        print(f'    [BOOTSTRAP] Portable Node.js detected at {target_node_dir}')
        return _get_env(target_node_dir)
    if not os.path.exists(RUNTIME_DIR):
        os.makedirs(RUNTIME_DIR)
    node_zip_name = f'node-{NODE_VERSION}-win-x64.zip'
    node_folder_name = f'node-{NODE_VERSION}-win-x64'
    download_url = f'{BASE_URL}{NODE_VERSION}/{node_zip_name}'
    local_zip = os.path.join(RUNTIME_DIR, node_zip_name)
    print(f'    [BOOTSTRAP] Downloading Node.js {NODE_VERSION} from {download_url}...')
    try:
        urllib.request.urlretrieve(download_url, local_zip)
        print('    [BOOTSTRAP] Download complete. Extracting...')
        with zipfile.ZipFile(local_zip, 'r') as zip_ref:
            zip_ref.extractall(RUNTIME_DIR)
        extracted_path = os.path.join(RUNTIME_DIR, node_folder_name)
        if os.path.exists(target_node_dir):
            shutil.rmtree(target_node_dir)
        os.rename(extracted_path, target_node_dir)
        os.remove(local_zip)
        print('    [BOOTSTRAP] Runtime installed successfully.')
    except Exception as e:
        print(f'    [BOOTSTRAP] Critical Error installing Node.js: {e}')
        return os.environ.copy()
    return _get_env(target_node_dir)

def _get_env(node_dir):
    """Inject node_dir into PATH."""
    env = os.environ.copy()
    env['PATH'] = node_dir + os.pathsep + env['PATH']
    return env
if __name__ == '__main__':
    env = setup_node_env()
    subprocess.run('npm --version', shell=True, env=env)