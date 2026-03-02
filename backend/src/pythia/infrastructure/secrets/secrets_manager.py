import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# === PREDICTION MARKETS KEYS ===
KALSHI_API_KEY: str = os.getenv("KALSHI_API_KEY", "")
KALSHI_PRIVATE_KEY_PATH: str = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
POLYMARKET_WALLET_KEY: str = os.getenv("POLYMARKET_WALLET_KEY", "")


def validate_secrets() -> dict:
    """Verifica che tutti i secrets critici siano presenti."""
    missing = []
    warnings = []

    if not KALSHI_API_KEY:
        warnings.append("KALSHI_API_KEY non configurata")
    if not KALSHI_PRIVATE_KEY_PATH or not os.path.exists(KALSHI_PRIVATE_KEY_PATH):
        warnings.append("KALSHI_PRIVATE_KEY_PATH non valido o file non trovato")
    if not POLYMARKET_WALLET_KEY:
        warnings.append("POLYMARKET_WALLET_KEY non configurata")

    return {"missing_critical": missing, "warnings": warnings}


class SecretsManager:
    """Fernet-based secrets manager with encryption at rest.

    In production, the encryption key MUST be pre-provisioned.
    Auto-generation is only permitted in development mode.
    """

    def __init__(
        self,
        encryption_key_path: Path = Path(".encryption_key"),
        allow_key_generation: bool = False,
    ):
        if not encryption_key_path.exists():
            if allow_key_generation:
                key = Fernet.generate_key()
                encryption_key_path.write_bytes(key)
                encryption_key_path.chmod(0o600)
                logger.warning(
                    "[SECRETS] Auto-generated Fernet key at %s — NOT for production use",
                    encryption_key_path,
                )
            else:
                raise FileNotFoundError(
                    f"Encryption key not found at {encryption_key_path}. "
                    "Provision the key or set allow_key_generation=True for dev."
                )

        self.cipher = Fernet(encryption_key_path.read_bytes())

    def encrypt_secret(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt_secret(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

    def load_encrypted_env(self, env_path: Path = Path(".env.encrypted")):
        if not env_path.exists():
            raise FileNotFoundError(f"Encrypted env not found: {env_path}")

        encrypted_data = json.loads(env_path.read_text(encoding="utf-8"))
        for key, encrypted_value in encrypted_data.items():
            os.environ[key] = self.decrypt_secret(encrypted_value)

        logger.info("Loaded %d secrets", len(encrypted_data))
