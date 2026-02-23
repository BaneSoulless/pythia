import os
import shutil
from pathlib import Path
backend = Path('backend')
app_dir = backend / 'app'
src_dir = backend / 'src' / 'pythia'
mappings = {'agents': 'application/ai', 'api': 'api/v1', 'core': 'core', 'db': 'infrastructure/persistence', 'ml': 'application/ai', 'services': 'application', 'domain': 'domain', 'infrastructure': 'infrastructure', 'adapters': 'adapters'}
if not app_dir.exists():
    print('No app directory found.')
    exit(0)
for root, dirs, files in os.walk(app_dir):
    for f in files:
        if '__pycache__' in root or f.endswith('.pyc'):
            continue
        src_file = Path(root) / f
        rel_path_str = src_file.relative_to(app_dir).as_posix()
        dest_rel_str = rel_path_str
        for old_prefix, new_prefix in mappings.items():
            if dest_rel_str.startswith(old_prefix + '/') or dest_rel_str == old_prefix:
                dest_rel_str = dest_rel_str.replace(old_prefix, new_prefix, 1)
                break
        dest_file = src_dir / dest_rel_str
        if not dest_file.exists():
            print(f'Moving {src_file} -> {dest_file}')
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
        else:
            print(f'Skipping {src_file}, already exists at {dest_file}')
try:
    shutil.rmtree(app_dir)
    print('Successfully deleted backend/app')
except Exception as e:
    print(f'Could not delete backend/app: {e}')