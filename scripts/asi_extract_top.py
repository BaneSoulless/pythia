# scripts/asi_extract_top.py
import sys, json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "vendor"))

from asi_evolve.database.database import Database

DB_PATH = ROOT / "vendor" / "asi_evolve" / "experiments" / "pythia_rl_evolve" / "database_data"
db = Database(storage_dir=str(DB_PATH))
nodes = db.get_all()

ranked = sorted(
    [n for n in nodes if n.score is not None],
    key=lambda n: n.score,
    reverse=True
)

if not ranked:
    print("ERROR: no scored nodes found")
    sys.exit(1)

best = ranked[0]
print(f"Best node: {best.id} | Score: {best.score:.4f}")
print(f"Simulated or real: check metrics in node data")

# Esegui il programma del best node per estrarre il config
namespace = {}
exec(getattr(best, 'program', None) or getattr(best, 'code', None), namespace)  # noqa: S102

if "get_pythia_config" not in namespace:
    print("ERROR: best node does not define get_pythia_config()")
    sys.exit(1)

config = namespace["get_pythia_config"]()
print("\n--- EXTRACTED CONFIG ---")
print(json.dumps(config, indent=2))

# Valida la struttura
required_keys = {
    "rl": ["learning_rate", "discount_factor", "exploration_epsilon"],
    "ensemble": ["weight_rl", "weight_signal", "weight_specialized", "min_confidence"]
}
valid = True
for section, keys in required_keys.items():
    for k in keys:
        if k not in config.get(section, {}):
            print(f"VALIDATION ERROR: missing {section}.{k}")
            valid = False

weights = config.get("ensemble", {})
total_weight = sum([
    weights.get("weight_rl", 0),
    weights.get("weight_signal", 0),
    weights.get("weight_specialized", 0)
])
if total_weight > 1.0:
    print(f"VALIDATION ERROR: ensemble weights sum to {total_weight:.3f} > 1.0")
    valid = False

print(f"\nVALIDATION: {'PASSED' if valid else 'FAILED'}")
