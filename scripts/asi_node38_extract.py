# scripts/asi_node38_extract.py
"""Extract Node 38 config for consensus analysis."""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "vendor"))

from asi_evolve.database.database import Database

DB_PATH = ROOT / "vendor" / "asi_evolve" / "experiments" / "pythia_rl_evolve" / "database_data"
db = Database(storage_dir=str(DB_PATH))
nodes = db.get_all()

n38 = next((n for n in nodes if n.id == 38), None)
if n38:
    namespace = {}
    code = getattr(n38, 'program', None) or getattr(n38, 'code', None)
    exec(code, namespace)  # noqa: S102
    if "get_pythia_config" in namespace:
        print(json.dumps(namespace["get_pythia_config"](), indent=2))
    else:
        print("NO get_pythia_config() in Node 38")
        print(code)
else:
    print("Node 38 not found")
