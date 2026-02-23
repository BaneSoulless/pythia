import logging
from datetime import datetime, timedelta

logger = logging.getLogger("PYTHIA-KEY-ROTATOR")

class APIKeyRotator:
    """Monitors API key age and warns when rotation is needed."""
    
    def __init__(self, rotation_interval_days: int = 90):
        self.rotation_interval = timedelta(days=rotation_interval_days)
        self.last_rotation = {}  # {service: datetime}

    def check_rotation_needed(self, service: str) -> bool:
        if service not in self.last_rotation:
            # Assume rotation needed if never tracked
            return True

        age = datetime.now() - self.last_rotation[service]
        if age > self.rotation_interval:
            logger.warning(f"🔑 API key for {service} needs rotation (age: {age.days} days)")
            return True
        return False

    def mark_rotated(self, service: str):
        self.last_rotation[service] = datetime.now()
        logger.info(f"✅ API key for {service} marked as rotated at {datetime.now()}")
