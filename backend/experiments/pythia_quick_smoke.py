# -*- coding: utf-8 -*-
import os; os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
"""
pythia_quick_smoke.py — Rapid health check for evolution integration.
Verifies that all new components can be instantiated and metrics recorded.
"""
import sys
from pathlib import Path

# Path bootstrapping
BACKEND_DIR = Path(__file__).parent.parent
SRC_DIR = BACKEND_DIR / "src"
VENDOR_DIR = BACKEND_DIR.parent / "vendor"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

def run_checks():
    print("--- [PYTHIA QUICK SMOKE] ---")
    
    # 1. Check imports
    try:
        from pythia.application.asi_evolve import ASIEvolveEngine
        from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
        from pythia.domain.events.domain_events import AsiEvolveEvent
        print("[OK] Core imports successful.")
    except ImportError as e:
        print(f"[FAIL] Core imports FAILED: {e}")
        return False

    # 2. Check engine init (passive)
    try:
        # Mock event bus
        class MockBus: 
            async def publish_signal(self, s): pass
        
        # Point to a dummy config if necessary or use the newly created one
        config_path = BACKEND_DIR / "asi_evolve_pythia_config.yaml"
        if not config_path.exists():
            print("[WARN] Evolution config missing, creating dummy for smoke test...")
            config_path.write_text("asi_evolve: {enabled: true}")

        engine = ASIEvolveEngine(event_bus=MockBus(), dry_run=True)
        print(f"[OK] ASIEvolveEngine initialized. Current mutations: {engine.mutation_count}")
    except Exception as e:
        print(f"[FAIL] Engine initialization FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Check Prometheus integration
    try:
        exporter = get_metrics_exporter()
        exporter.record_asi_mutation(score=0.88)
        print("[OK] Prometheus metrics recording active.")
    except Exception as e:
        print(f"[FAIL] Prometheus test FAILED: {e}")
        return False

    print("\n[RUN] ALL INTEGRATION CHECKS PASSED.")
    return True

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
