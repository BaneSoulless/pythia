import os
import shutil
import argparse
from pathlib import Path

def setup_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.touch()

def migrate(dry_run: bool):
    root = Path.cwd()
    backend = root / "backend"
    old_app = backend / "app"
    src_pythia = backend / "src" / "pythia"
    
    print(f"🚀 Avvio Migrazione Struttura PYTHIA (Dry Run: {dry_run})")
    
    if not old_app.exists() and src_pythia.exists():
        print("Struttura già migrata in precedenza.")
        return
        
    if not old_app.exists():
         print(f"Directory {old_app} non trovata.")
         return

    # 1. Crea struttura base
    directories_to_create = [
        src_pythia,
        src_pythia / "domain" / "trading",
        src_pythia / "domain" / "cognitive",
        src_pythia / "domain" / "risk",
        src_pythia / "application" / "trading",
        src_pythia / "application" / "ai",
        src_pythia / "infrastructure" / "persistence",
        src_pythia / "infrastructure" / "messaging",
        src_pythia / "infrastructure" / "ai_providers",
        src_pythia / "infrastructure" / "resilience",
        src_pythia / "infrastructure" / "idempotency",
        src_pythia / "infrastructure" / "caching",
        src_pythia / "adapters" / "freqtrade",
        src_pythia / "adapters" / "exchanges",
        src_pythia / "api" / "v1",
        src_pythia / "core" / "schemas"
    ]
    
    if not dry_run:
        for d in directories_to_create:
            setup_directory(d)
        (src_pythia / "py.typed").touch()
        
    # Mappa dei movimenti
    # Formato: (vecchio percorso relativo a app, nuovo percorso relativo a pythia)
    moves = [
        # Core
        ("core", "core"),
        ("db", "infrastructure/persistence"),
        ("middleware", "api/middleware"),
        # Adattiamo i controller/router FastAPI
        ("api", "api/v1"),
        # Cognitive & AI models -> domain/cognitive
        ("domain/cognitive", "domain/cognitive"),
        # Risk & rules -> domain/risk
        ("domain/execution", "domain/trading"),
        ("domain/events", "domain/trading"), # Aggregato TradeEvents
        # Servizi -> infrastructure
        ("services/vector_store.py", "infrastructure/persistence/vector_store.py"),
        ("services/ai_providers", "infrastructure/ai_providers"),
        ("agents", "application/ai"),
        ("ml", "application/ai"),
        # Infrastructure preesistente
        ("infrastructure/resilience", "infrastructure/resilience"),
        ("infrastructure/idempotency", "infrastructure/idempotency"),
        # Adapters
        ("adapters/freqtrade_adapter.py", "adapters/freqtrade/strategy_adapter.py")
    ]
    
    for old_rel, new_rel in moves:
        old_path = old_app / old_rel
        new_path = src_pythia / new_rel
        
        if old_path.exists():
            print(f"In mooving: {old_path.relative_to(backend)} -> {new_path.relative_to(backend)}")
            if not dry_run:
                if old_path.is_file():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_path), str(new_path))
                else:
                    new_path.mkdir(parents=True, exist_ok=True)
                    for item in os.listdir(old_path):
                         src = old_path / item
                         dst = new_path / item
                         if src.is_dir():
                             shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
                         else:
                             shutil.move(str(src), str(dst))

    # Pulizia artefatti residui
    extracted_json = backend / "extracted_code.json"
    if extracted_json.exists():
         print(f"🗑️ Eliminazione '{extracted_json.name}'...")
         if not dry_run:
             extracted_json.unlink()
             
    security_fixes = backend / "SECURITY_FIXES.py"
    if security_fixes.exists():
         print(f"🗑️ Eliminazione file di parcheggio '{security_fixes.name}'...")
         if not dry_run:
             security_fixes.unlink()
             
    print("\n✅ Migrazione struttura completata.")
    if not dry_run:
         print("Rimuovere la vecchia directory backend/app/ se vuota.")
         # Evitiamo blocco del file-system se aperta nel DB o simili
         try:
             shutil.rmtree(str(old_app))
         except Exception as e:
             print(f"⚠️ Avviso: Impossibile rimuovere backend/app/: {e}")
             
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Pythia Structure to SOTA 2026")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("--execute", action="store_true", help="Execute the migration")
    args = parser.parse_args()
    
    if args.dry_run:
        migrate(dry_run=True)
    elif args.execute:
        migrate(dry_run=False)
    else:
        print("Specifica --dry-run oppure --execute")
