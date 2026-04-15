"""
AI Status API Endpoints
"""

from fastapi import APIRouter, Depends, Request
from pythia.application.ai.error_analyzer import ErrorAnalyzer
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import Portfolio
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/status")
async def get_ai_status(request: Request, db: Session = Depends(get_db)):
    """Get current AI learning status and hyperparameters"""
    portfolio = db.query(Portfolio).first()
    config = getattr(request.app.state, "config", None)
    params = config.params if config else {}

    if not portfolio:
        return {
            "is_learning": False, 
            "epsilon": params.get("rl", {}).get("exploration_epsilon", 1.0),
            "total_experiences": 0,
            "hyperparameters": params
        }
    
    return {
        "is_learning": True,
        "phase": "exploration",
        "epsilon": params.get("rl", {}).get("exploration_epsilon", 0.5),
        "total_experiences": 0,
        "current_strategy": "Evolved Ensemble",
        "hyperparameters": params
    }


@router.get("/performance")
async def get_ai_performance(db: Session = Depends(get_db)):
    """Get AI performance metrics"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {}
    analyzer = ErrorAnalyzer(db)
    performance = analyzer.get_recent_performance(portfolio.id, days=30)
    return performance


@router.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db)):
    """Get strategy recommendations from error analysis"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {"recommendations": []}
    analyzer = ErrorAnalyzer(db)
    recommendations = analyzer.get_strategy_recommendations(portfolio.id)
    return {"recommendations": recommendations}


@router.get("/asi-evolve/status")
async def get_asi_evolve_status(request: Request):
    """Get status of the autonomous ASI-Evolve optimization engine"""
    engine = getattr(request.app.state, "asi_engine", None)
    if not engine:
        return {"error": "ASI-Evolve engine not initialized"}
    
    status = engine.get_status()

    from pathlib import Path
    import sys, yaml, sqlite3

    # Leggi best node dal DB asi_evolve
    asi_root = Path("vendor/asi_evolve")
    db_path = asi_root / "experiments/pythia_rl_evolve/database_data"
    best_node_score = None
    best_node_id = None
    score_source = "simulated_fallback"

    if db_path.exists():
        if str(asi_root.parent) not in sys.path:
            sys.path.insert(0, str(asi_root.parent))
        try:
            from asi_evolve.database.database import Database
            db = Database(storage_dir=str(db_path))
            nodes = db.get_all()
            scored = sorted([n for n in nodes if n.score is not None], key=lambda x: x.score, reverse=True)
            if scored:
                best_node_score = scored[0].score
                best_node_id = scored[0].id
        except Exception:
            pass

    # Read shadow status
    evolved_path = Path("backend/config/pythia_params_evolved.yaml")
    shadow_log = Path("backend/data/shadow_trades.jsonl")
    
    shadow_active = evolved_path.exists()
    trades_completed = 0
    trades_required = 50
    promoted = False
    
    if shadow_active:
        try:
            raw = yaml.safe_load(evolved_path.read_text())
            trades_completed = raw.get("metadata", {}).get("shadow_trades_completed", 0)
            trades_required = raw.get("metadata", {}).get("shadow_trades_required", 50)
            promoted = raw.get("metadata", {}).get("promoted", False)
        except Exception:
            pass
    elif shadow_log.exists():
        promoted = True
    
    status["best_node"] = {
        "score": best_node_score,
        "node_id": best_node_id,
        "score_source": score_source
    }
    status["shadow_status"] = {
        "active": shadow_active,
        "trades_completed": trades_completed,
        "trades_required": trades_required,
        "promoted": promoted
    }

    # Next real data run
    prod_db = Path("backend/data/pythia_prod.db")
    current_trade_count = 0
    if prod_db.exists():
        try:
            conn = sqlite3.connect(prod_db)
            current_trade_count = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
            conn.close()
        except Exception:
            pass
            
    status["next_real_data_run"] = {
        "min_trades_required": 50,
        "current_trade_count": current_trade_count,
        "ready": current_trade_count >= 50
    }
    
    return status
