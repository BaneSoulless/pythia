import pytest
import math
from pythia.application.asi_evolve import ASIEvolveEngine

def test_monthly_target_reward_sigmoid():
    # Test della logica sigmoid tramite l'engine
    # Target 10% should give neutral-ish scores around 0.5 for monthly component
    
    # 1. Caso Target Esatto (10%)
    score_target = ASIEvolveEngine._monthly_target_reward(
        monthly_return=0.10,
        sharpe_ratio=1.5,
        win_rate=0.50,
        max_drawdown=0.10,
        monthly_std_dev=0.05,
        asset_class="CRYPTO"
    )
    assert score_target == 0.5  # Poiché sigmoid(0)*0.35 + sigmoid(0)*0.25... = 0.5
    
    # 2. Caso High Performance
    score_high = ASIEvolveEngine._monthly_target_reward(
        monthly_return=0.15,
        sharpe_ratio=2.5,
        win_rate=0.65,
        max_drawdown=0.04,
        monthly_std_dev=0.02,
        asset_class="CRYPTO"
    )
    assert score_high > 0.8
    
    # 3. Caso Low Performance
    score_low = ASIEvolveEngine._monthly_target_reward(
        monthly_return=0.02,
        sharpe_ratio=0.5,
        win_rate=0.40,
        max_drawdown=0.20,
        monthly_std_dev=0.15,
        asset_class="CRYPTO"
    )
    assert score_low < 0.2

def test_asset_class_weights():
    # Verifica che i pesi cambino lo score finale
    # PM ha peso win_rate(0.3) > Crypto(0.2)
    
    args = {
        "monthly_return": 0.10,
        "sharpe_ratio": 1.5,
        "win_rate": 0.70, # Ottimo win rate
        "max_drawdown": 0.10,
        "monthly_std_dev": 0.05
    }
    
    score_crypto = ASIEvolveEngine._monthly_target_reward(**args, asset_class="CRYPTO")
    score_pm = ASIEvolveEngine._monthly_target_reward(**args, asset_class="PREDICTION_MARKET")
    
    # PM dovrebbe apprezzare di più l'alto win rate
    assert score_pm > score_crypto

def test_sigmoid_clamping():
    # Verifica che valori estremi non rompano math.exp
    score = ASIEvolveEngine._monthly_target_reward(
        monthly_return=1000.0,
        sharpe_ratio=1000.0,
        win_rate=1.0,
        max_drawdown=0.0,
        monthly_std_dev=0.0,
        asset_class="STOCK"
    )
    assert 0.0 <= score <= 1.0
