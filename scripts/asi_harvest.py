# scripts/asi_harvest.py
import sys, json
from pathlib import Path

# Aggiungi vendor al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "backend" / "src"))

from asi_evolve.database.database import Database

DB_PATH = ROOT / "vendor" / "asi_evolve" / "experiments" / "pythia_rl_evolve" / "database_data"

db = Database(storage_dir=str(DB_PATH))
nodes = db.get_all()

# Ordina per score descending
ranked = sorted(
    [n for n in nodes if n.score is not None],
    key=lambda n: n.score,
    reverse=True
)

print(f"\nTOTAL NODES: {len(nodes)} | SCORED: {len(ranked)}\n")
print(f"{'Rank':<5} {'Node ID':<12} {'Score':<10} {'Parent':<12} {'Motivation preview'}")
print("-" * 80)
for i, n in enumerate(ranked[:20], 1):
    motivation_preview = (n.motivation or "")[:50].replace("\n", " ")
    parent = getattr(n, 'parent_id', 'root') or 'root'
    print(f"{i:<5} {str(n.id)[:10]:<12} {n.score:<10.4f} {str(parent)[:10]:<12} {motivation_preview}")

print("\n--- TOP 3 PROGRAMS ---")
for i, n in enumerate(ranked[:3], 1):
    print(f"\n{'='*60}")
    print(f"RANK {i} | Score: {n.score:.4f} | Node: {n.id}")
    print(f"Motivation: {n.motivation}")
    print(f"--- CODE ---")
    print(getattr(n, 'program', None) or getattr(n, 'code', None))
