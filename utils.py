import os
import sys
import logging

def recursive_dependency_injector(root_path: str):
    """
    Injects submodules from temp_repos into sys.path.
    CRITICAL FIX: Appends to END of sys.path to prevent Standard Library Shadowing.
    """
    if not os.path.exists(root_path):
        return
    src_identifiers = ['src', 'lib', 'package', 'hummingbot', 'freqtrade', 'finrl', 'qlib', 'jesse']
    injected_count = 0
    for root, dirs, files in os.walk(root_path):
        dirname = os.path.basename(root)
        if dirname in src_identifiers or '__init__.py' in files:
            abs_path = os.path.abspath(root)
            if abs_path not in sys.path:
                sys.path.append(abs_path)
                injected_count += 1
    logging.info(f'Dependency Injector: Added {injected_count} paths from {root_path}')