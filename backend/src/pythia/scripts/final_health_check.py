import os
import subprocess
from pathlib import Path

# Set PYTHONPATH to include the source directory
os.environ["PYTHONPATH"] = str(Path("backend/src").absolute())


def check_file_structure():
    print("\n📁 VERIFYING FILE STRUCTURE...")
    critical_files = [
        "backend/src/pythia/adapters/pmxt_adapter.py",
        "backend/src/pythia/domain/markets/prediction_market.py",
        "backend/src/pythia/application/trading/arbitrage_detector.py",
        "backend/src/pythia/infrastructure/secrets/secrets_manager.py",
        "backend/src/pythia/infrastructure/rate_limiting/circuit_breaker.py",
        "backend/src/pythia/infrastructure/monitoring/prometheus_exporter.py",
        "docker-compose.prod.yml",
        "k8s/pythia-deployment.yaml",
        "docs/adr/0001-prediction-markets-integration.md",
    ]

    missing = []
    for f in critical_files:
        path = Path(f)
        exists = path.exists()
        print(f"  {'✅' if exists else '❌'} {f}")
        if not exists:
            missing.append(f)
    return len(missing) == 0


def check_git_status():
    print("\n📦 VERIFYING GIT STATUS...")
    try:
        result = subprocess.run(
            ["git", "status", "--short"], capture_output=True, text=True  # noqa: S607
        )
        uncommitted = result.stdout.strip()
        if uncommitted:
            print(f"  ⚠️ Working directory dirty:\n{uncommitted}")
        else:
            print("  ✅ Working directory clean")
        return True
    except Exception as e:
        print(f"  ❌ Git check failed: {e}")
        return False


def check_logic():
    print("\n🧪 VERIFYING DOMAIN LOGIC...")
    try:
        from pythia.domain.markets.prediction_market import PredictionMarket
        from pythia.infrastructure.secrets.secrets_manager import SecretsManager

        # Test 1: Arbitrage Logic
        m1 = PredictionMarket("K1", "Test", 0.45, 0.55, "kalshi", 100)
        m2 = PredictionMarket("P1", "Test", 0.55, 0.44, "polymarket", 100)
        arb = m1.arbitrage_opportunity(m2)
        assert arb is not None and arb["profit"] > 0
        print("  ✅ Domain: Arbitrage detection logic works")

        # Test 2: Secrets Encryption
        mgr = SecretsManager(encryption_key_path=Path(".encryption_key_health"))
        token = mgr.encrypt_secret("pythia_test")
        assert mgr.decrypt_secret(token) == "pythia_test"
        Path(".encryption_key_health").unlink()
        print("  ✅ Infrastructure: Secrets encryption works")

        return True
    except Exception as e:
        print(f"  ❌ Logic check failed: {e}")
        return False


def run_health_check():
    print("=" * 60)
    print("🚀 PYTHIA MULTI-ASSET READINESS REPORT")
    print("=" * 60)

    s1 = check_file_structure()
    _s2 = check_git_status()
    s3 = check_logic()

    print("\n" + "=" * 60)
    if s1 and s3:
        print("🟢 SYSTEM READY FOR LIVE DEPLOYMENT")
    else:
        print("🔴 SYSTEM COMPONENT FAILURE DETECTED")
    print("=" * 60)


if __name__ == "__main__":
    run_health_check()
