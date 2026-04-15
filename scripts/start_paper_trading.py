import os
import sys
import subprocess
from pathlib import Path

def main():
    print("--------------------------------------------------------------")
    print("  PYTHIA   BOOTSTRAP PAPER TRADING (Target +10%/mo)")
    print("--------------------------------------------------------------")
    
    # 1. Risoluzione percorsi
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    env_paper = root_dir / ".env.paper"
    
    # 2. Caricamento ambiente dedicato
    if env_paper.exists():
        print(f"[OK] Caricamento configurazioni da {env_paper}")
        # Inseriamo manualmente nell'env per subprocess
        with open(env_paper, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v
    else:
        print(f"[WARN] ATTENZIONE: {env_paper} non trovato. Copia .env.paper.template in .env.paper")
        print("Il sistema user  le variabili di default di .env")

    # 3. Forza modalit  PAPER
    os.environ["TRADING_MODE"] = "PAPER"
    os.environ["PYTHONPATH"] = str(backend_dir / "src")
    
    # 4. Verifica uvicorn
    venv_uvicorn = root_dir / ".venv" / "Scripts" / "uvicorn.exe"
    if not venv_uvicorn.exists():
        venv_uvicorn = "uvicorn" # Fallback a system path
    
    print(f"  Avvio Orchestrator (API + Evolution Workers)...")
    
    # Eseguiamo l'orchestratore direttamente come modulo per attivare tutti i worker async
    # (gather di API, Metrics, PM Worker, ASI Worker)
    cmd = [
        sys.executable, 
        str(backend_dir / "src" / "pythia" / "infrastructure" / "orchestrator.py")
    ]
    
    try:
        import os as _os
        _env = {**_os.environ}
        _root = Path(".").resolve()
        _env["PYTHONPATH"] = _os.pathsep.join([
            str(_root / "vendor"),
            str(_root / "backend" / "src"),
            str(_root / "backend"),
            _env.get("PYTHONPATH", ""),
        ])
        print(f"[START] {' '.join(cmd)}\n")
        result = subprocess.run(cmd, env=_env, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n  Paper trading arrestato dall'utente.")
    except Exception as e:
        print(f"  Errore inaspettato: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
