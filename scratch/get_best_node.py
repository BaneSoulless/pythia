import sys
from pathlib import Path
import json

# Add vendor/asi-evolve to sys.path
PROJECT_ROOT = Path("e:/Programmazione/Progetti Google Antigravity/AI-Trading-Bot")
ASI_EVOLVE_PATH = PROJECT_ROOT / "vendor" / "asi-evolve"
sys.path.insert(0, str(ASI_EVOLVE_PATH))

# Bootstrapping for Evolve package structure
import importlib.util
def _bootstrap_package():
    spec = importlib.util.spec_from_file_location(
        "Evolve",
        ASI_EVOLVE_PATH / "__init__.py",
        submodule_search_locations=[str(ASI_EVOLVE_PATH)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["Evolve"] = module
    spec.loader.exec_module(module)

_bootstrap_package()

from Evolve.database.experiment_db import ExperimentDatabase

db_dir = ASI_EVOLVE_PATH / "experiments" / "pythia_rl_evolve" / "database_data"
db = ExperimentDatabase(storage_dir=db_dir)
nodes = db.get_all_nodes()

if not nodes:
    print("No nodes found in database.")
    sys.exit(0)

best = max(nodes, key=lambda n: n.score or 0.0)
print(f"Best score: {best.score}")
print(f"Node ID: {best.id}")
print("--- Program ---")
print(best.program)
