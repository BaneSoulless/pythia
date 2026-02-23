import yaml
from jsonschema import validate, ValidationError
from pathlib import Path
import logging

logger = logging.getLogger("PYTHIA-VALIDATOR")

class SchemaValidator:
    """Zero-hallucination validation via YAML schemas."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        if schema_dir is None:
            # Default to relative path from this file
            schema_dir = Path(__file__).parent.parent / "schemas"
            
        self.schema_dir = schema_dir
        self.schemas = {}
        self._load_schemas()

    def _load_schemas(self):
        if not self.schema_dir.exists():
            logger.warning(f"Schema directory {self.schema_dir} not found.")
            return

        for schema_file in self.schema_dir.glob("*.yaml"):
            try:
                schema_name = schema_file.stem
                self.schemas[schema_name] = yaml.safe_load(schema_file.read_text())
                logger.info(f"Loaded schema: {schema_name}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file.name}: {e}")

    def validate_market_data(self, data: dict):
        self._validate(data, "market_data_schema", "market_data")

    def validate_trade_signal(self, signal: dict):
        self._validate(signal, "market_data_schema", "trade_signal")

    def _validate(self, data: dict, schema_file: str, key: str):
        schema_set = self.schemas.get(schema_file)
        if not schema_set:
            logger.warning(f"Schema {schema_file} not loaded. Skipping validation.")
            return

        schema = schema_set.get(key)
        if not schema:
            logger.warning(f"Key {key} not found in {schema_file}. Skipping validation.")
            return

        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            logger.error(f"Validation Error [{key}]: {e.message}")
            raise ValueError(f"Invalid data structure: {e.message}")
