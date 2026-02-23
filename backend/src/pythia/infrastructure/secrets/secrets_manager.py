import os
from cryptography.fernet import Fernet
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class SecretsManager:
    def __init__(self, encryption_key_path: Path = Path(".encryption_key")):
        if not encryption_key_path.exists():
            key = Fernet.generate_key()
            encryption_key_path.write_bytes(key)
            encryption_key_path.chmod(0o600)

        self.cipher = Fernet(encryption_key_path.read_bytes())

    def encrypt_secret(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt_secret(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

    def load_encrypted_env(self, env_path: Path = Path(".env.encrypted")):
        if not env_path.exists():
            raise FileNotFoundError(f"Encrypted env not found: {env_path}")

        encrypted_data = json.loads(env_path.read_text())
        for key, encrypted_value in encrypted_data.items():
            os.environ[key] = self.decrypt_secret(encrypted_value)

        logger.info(f"✅ Loaded {len(encrypted_data)} secrets")
