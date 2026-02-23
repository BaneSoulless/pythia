import sys
from pathlib import Path

def verify_structure():
    """Verifica che la nuova struttura DDD sia conforme."""
    root = Path.cwd()
    src_dir = root / "backend" / "src" / "pythia"
    
    if not src_dir.exists():
        print("❌ CRITICAL: Directory backend/src/pythia/ mancante.")
        sys.exit(1)
        
    # Check marker file
    if not (src_dir / "py.typed").exists():
        print("❌ ERRORE: File py.typed (PEP 561) mancante in src/pythia/")
        sys.exit(1)
        
    print("✅ Marker PEP 561 (py.typed) trovato.")

    # Layers check
    layers = ["domain", "application", "infrastructure", "api", "core", "adapters"]
    for layer in layers:
        layer_path = src_dir / layer
        if not layer_path.exists():
            print(f"❌ ERRORE: Layer mancante: {layer}")
            sys.exit(1)
        if not (layer_path / "__init__.py").exists():
            print(f"❌ ERRORE: __init__.py mancante nel layer: {layer}")
            sys.exit(1)

    print("✅ Tutti i layer architettonici standard (DDD) sono presenti.")
    
    # Bounded contexts check in domain
    contexts = ["trading", "cognitive", "risk"]
    for ctx in contexts:
        ctx_path = src_dir / "domain" / ctx
        if not ctx_path.exists():
            print(f"❌ ERRORE: Bounded Context '{ctx}' mancante in domain/")
            sys.exit(1)
             
    print("✅ Tutti i Bounded Contexts trovati in domain/")

    # Dependency Rule check (Domain cannot import Infrastructure)
    domain_path = src_dir / "domain"
    for py_file in domain_path.rglob("*.py"):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "from pythia.infrastructure" in content or "import pythia.infrastructure" in content:
                print(f"❌ VIOLAZIONE REGOLE CLEAN ARCHITECTURE: {py_file.name} importa da infrastructure")
                sys.exit(1)
                
    print("✅ Regola dipendenze: Nessuna infrastruttura importata dai layer di Dominio.")
    
    # Check pyproject.toml
    if not (root / "pyproject.toml").exists():
        print("❌ ERRORE: pyproject.toml PEP 621 Configuration mancante.")
        sys.exit(1)
         
    print("✅ pyproject.toml trovato.")
    print("\n🚀 Verifica Strutturale Completata: PYTHIA SOTA 2026 Ready.")

if __name__ == "__main__":
    verify_structure()
