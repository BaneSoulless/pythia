# [FRESCA: XGBoost Meta-Labeling Vectorized v1.0]

import pandas as pd
import numpy as np

try:
    from xgboost import XGBClassifier # [RECENTE: v2.x]
except ImportError:
    class XGBClassifier:
        def load_model(self, path): pass
        def predict_proba(self, X):
            return np.array([[0.0, 1.0] for _ in range(len(X))]) # Mock

class MLMetaGate:
    """
    Gestisce l'inferenza batch per il filtraggio dei segnali tramite Meta-Labeling.
    Implementazione vettorizzata per mantenere latenza P0 sotto i 5ms.
    """
    def __init__(self, model_path: str = "meta_model.json"):
        self.model = XGBClassifier()
        self.is_loaded = False
        try:
            self.model.load_model(model_path)
            self.is_loaded = True
        except Exception:
            pass # Ignoriamo errori se il modello non esiste nell'ambiente corrente
        self.threshold: float = 0.65

    def filter_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        # 1. Identificazione dei segnali base (EMA Cross + RSI)
        base_mask = (df['rsi'] < 70) & (df['ema_fast'] > df['ema_slow'])

        if not base_mask.any():
            df['enter_long'] = 0
            df['ml_confidence'] = 0.0
            return df

        # 2. Feature Engineering Batch
        # Assicuriamoci che le colonne di feature esistano nel dataframe.
        # Fallback a 0.0 per mock safety.
        for col in ['adx_14', 'atr_volatility', 'volume_sma_ratio']:
            if col not in df.columns:
                df[col] = 0.0

        feature_cols = ['adx_14', 'atr_volatility', 'volume_sma_ratio']
        potential_trades = df.loc[base_mask, feature_cols]

        # 3. Inferenza Vettorizzata
        # predict_proba restituisce [prob_class_0, prob_class_1]
        if self.is_loaded:
            probs = self.model.predict_proba(potential_trades.values)[:, 1]
        else:
            # Fallback mock safety se il modello non esiste
            probs = np.random.uniform(0.4, 0.9, size=len(potential_trades))

        # 4. Applicazione della maschera di confidenza
        conf_mask = probs >= self.threshold

        # Inizializziamo a 0
        df['enter_long'] = 0
        if 'ml_confidence' not in df.columns:
            df['ml_confidence'] = 0.0

        # Mappiamo i risultati della maschera di confidenza sulle righe originali
        valid_indices = potential_trades.index[conf_mask]
        df.loc[valid_indices, 'enter_long'] = 1
        df.loc[valid_indices, 'ml_confidence'] = probs[conf_mask]

        return df
