# ADR-0001: Prediction Markets Integration via pmxt Framework

## Status
Accepted (2026-02-23)

## Context
Pythia is expanding from cryptocurrency-only trading to a multi-asset Control Plane AI. Prediction markets represent a high-growth opportunity with cross-platform arbitrage potential.

## Decision
Integrate prediction markets via the **pmxt framework**:
- **Platform Support**: Polymarket and Kalshi.
- **Architecture**: `PmxtAdapter`, `PredictionMarket` domain model, `ArbitrageDetector`.
- **Fault Tolerance**: `CircuitBreaker`.
- **Security**: `SecretsManager` (Fernet encryption).

## Consequences
- TAM Expansion to multi-asset.
- Revenue diversification.
- Increased operational complexity managed by circuit breakers and detailed monitoring.
