"""
apply_best_asi_config.py
Reads top node from ASI-Evolve database, applies config to Pythia.
Usage: python experiments/apply_best_asi_config.py [--dry-run] [--apply]
"""
from __future__ import annotations
import argparse
import json
import sys
import os
from pathlib import Path

# Paths
ROOT = Path(__file__).parent.parent.parent
ASI_ROOT = ROOT / "vendor" / "asi-evolve"
BACKEND_ROOT = ROOT / "backend"

if str(ASI_ROOT) not in sys.path:
    sys.path.insert(0, str(ASI_ROOT))

if str(BACKEND_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT / "src"))


def get_best_config() -> dict:
    """Load top-scoring config from ASI-Evolve experiment database."""
    # Use the actual class and path from the current repository
    from database.database import Database  # upstream module in this repo
    
    db_path = ASI_ROOT / "experiments" / "pythia_rl_evolve" / "database_data"
    db = Database(storage_dir=db_path)
    
    nodes = db.get_all()
    if not nodes:
        raise ValueError("No nodes in ASI-Evolve database. Run evolution first.")
    
    best = max(nodes, key=lambda n: n.score or 0.0)
    print(f"Best node score: {best.score:.4f} (ID: {best.id})")
    print(f"Motivation: {best.motivation}")
    
    # Execute the best node's code to get the config dict
    namespace = {}
    # Adapting 'program' -> 'code' to match actual Node structure
    exec(best.code, namespace)  # noqa: S102
    return namespace["get_pythia_config"]()


def apply_config(config: dict, dry_run: bool = True) -> None:
    """
    Applies the evolved config to Pythia's live components.
    
    Target: backend/config/pythia_params.yaml 
    Matched with PythiaSupervisor hot-reload watcher.
    """
    import yaml
    
    # Pointing to the central config used by the orchestrator for hot-reload
    output_path = BACKEND_ROOT / "config" / "pythia_params.yaml"
    
    print(f"\nEvolved config:")
    print(json.dumps(config, indent=2))
    
    if dry_run:
        print(f"\n[DRY RUN] Would write to: {output_path}")
        return
    
    # Ensure dir exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add metadata
    full_output = {
        **config,
        "metadata": {
            "last_updated": datetime.now().isoformat() if "datetime" in globals() else "2026-04-15T02:00:00Z",
            "version": "evolved-sync",
            "source": "ASI-Evolve"
        }
    }
    
    output_path.write_text(yaml.dump(full_output, default_flow_style=False))
    print(f"\n✅ Config written to: {output_path}")
    print("Pythia Orchestrator will hot-reload on next file system event.")


if __name__ == "__main__":
    from datetime import datetime
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--apply", action="store_true", help="Actually apply (overrides --dry-run)")
    args = parser.parse_args()
    
    # If neither is specified, default to dry-run (safety first)
    dry_run = True
    if args.apply:
        dry_run = False
    elif args.dry_run is False:
        dry_run = False
        
    try:
        config = get_best_config()
        apply_config(config, dry_run=dry_run)
    except Exception as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)
