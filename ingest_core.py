import os
import glob
from pathlib import Path

# Define whitelist extensions
whitelist_exts = {'.py', '.pyx', '.rs', '.toml'}

# Define blacklist paths (patterns)
blacklist_patterns = ['*/tests/*', '*/docs/*', '*/examples/*', '*/ui/*']

def is_blacklisted(path):
    for pattern in blacklist_patterns:
        if path.match(pattern):
            return True
    return False

def collect_core_files(root_dir):
    core_files = []
    for ext in whitelist_exts:
        pattern = f'**/*{ext}'
        for file_path in Path(root_dir).glob(pattern):
            rel_path = str(file_path.relative_to(root_dir))
            if not is_blacklisted(Path(rel_path)):
                core_files.append(rel_path)
    return core_files

# Collect from all repos
repos = ['../temp_repos/freqtrade', '../temp_repos/jesse', '../temp_repos/FinRL', '../temp_repos/hummingbot', '../temp_repos/qlib']
all_core_files = []
for repo in repos:
    if os.path.exists(repo):
        files = collect_core_files(repo)
        all_core_files.extend([(repo, f) for f in files])

print(f"Total core files collected: {len(all_core_files)}")
for repo, file in all_core_files[:10]:  # Show first 10
    print(f"{repo}: {file}")

# For dependencies, rough estimate
# To build a graph, would need to parse imports, but for now, just count
print(f"Active Context Size: {len(all_core_files)} core files")
# Token count rough: assume 100 tokens per file
approx_tokens = len(all_core_files) * 100
print(f"Approximate token count: {approx_tokens}")