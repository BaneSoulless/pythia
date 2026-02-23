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

    # Folder names that likely contain source code
    src_identifiers = ['src', 'lib', 'package', 'hummingbot', 'freqtrade', 'finrl', 'qlib', 'jesse']
    
    injected_count = 0
    # Walk top-down
    for root, dirs, files in os.walk(root_path):
        dirname = os.path.basename(root)
        
        # Injection Logic:
        # 1. If folder matches a source ID
        # 2. OR if it contains __init__.py (it's a package)
        if dirname in src_identifiers or '__init__.py' in files:
            abs_path = os.path.abspath(root)
            
            # Avoid duplicating paths
            if abs_path not in sys.path:
                # USE APPEND, NOT INSERT. 
                # System libraries > Local Shadowing
                sys.path.append(abs_path) 
                injected_count += 1
    
    logging.info(f"Dependency Injector: Added {injected_count} paths from {root_path}")
