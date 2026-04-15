import os
import sys
import subprocess
from pathlib import Path

def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  PYTHIA — BOOTSTRAP PAPER TRADING (Target +10%/mo)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # 1. Risoluzione percorsi
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    env_paper = root_dir / ".env.paper"
    
    # 2. Caricamento ambiente dedicato
    if env_paper.exists():
        print(f"✅ Caricamento configurazioni da {env_paper}")
        # Inseriamo manualmente nell'env per subprocess
        with open(env_paper, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v
    else:
        print(f"⚠️ ATTENZIONE: {env_paper} non trovato. Copia .env.paper.template in .env.paper")
        print("Il sistema userà le variabili di default di .env")

    # 3. Forza modalità PAPER
    os.environ["TRADING_MODE"] = "PAPER"
    os.environ["PYTHONPATH"] = str(backend_dir / "src")
    
    # 4. Verifica uvicorn
    venv_uvicorn = root_dir / ".venv" / "Scripts" / "uvicorn.exe"
    if not venv_uvicorn.exists():
        venv_uvicorn = "uvicorn" # Fallback a system path
    
    print(f"🚀 Avvio Orchestrator (API + Evolution Workers)...")
    
    # Eseguiamo l'orchestratore direttamente come modulo per attivare tutti i worker async
    # (gather di API, Metrics, PM Worker, ASI Worker)
    cmd = [
        sys.executable, 
        str(backend_dir / "src" / "pythia" / "infrastructure" / "orchestrator.py")
    ]
    
    try:
        # Usiamo subprocess.run per bloccare finché non viene terminato (CTRL+C)
        subprocess.run(cmd, check=True, cwd=root_dir)
    except KeyboardInterrupt:
        print("\n🛑 Paper trading arrestato dall'utente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore durante l'esecuzione: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Errore inaspettato: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
