"""Schema cache and property resolver."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

from notion.errors import ValidationError

CACHE_DIR = Path.home() / ".cache" / "notion-agent" / "schemas"
CACHE_TTL = 900  # 15 minutes


class SchemaCache:
    """Disk-based cache for database schemas with TTL."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR

    def _path(self, db_id: str) -> Path:
        # Normalise ID for filename
        clean_id = db_id.replace("-", "").lower()
        return self.cache_dir / f"{clean_id}.json"

    def get(self, db_id: str) -> dict | None:
        """Return cached schema if exists and not expired."""
        path = self._path(db_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data.get("cached_at", 0) > CACHE_TTL:
                return None
            return data.get("schema")
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, db_id: str, schema: dict) -> None:
        """Write schema to cache with current timestamp."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(db_id)
        path.write_text(json.dumps({
            "cached_at": time.time(),
            "schema": schema,
        }))

    def invalidate(self, db_id: str) -> None:
        """Remove cached schema for a database."""
        path = self._path(db_id)
        if path.exists():
            path.unlink()


class PropertyResolver:
    """Resolves user-supplied key=value pairs against a database schema."""

    def resolve_all(self, schema_properties: dict, data: dict) -> dict:
        """
        Given the schema properties dict and a user data dict,
        return a complete Notion 'properties' payload.

        schema_properties: the `properties` field from GET /databases/{id}
        data: user input like {"Name": "My Page", "Tags": "python,testing"}

        Raises ValidationError for unknown properties.
        """
        from notion.coerce import coerce_value

        # Build a case-insensitive lookup: lower(name) → (actual_name, prop_def)
        schema_lookup = {}
        for prop_name, prop_def in schema_properties.items():
            schema_lookup[prop_name.lower()] = (prop_name, prop_def)

        result = {}
        for key, value in data.items():
            if value is None:
                continue  # Skip None values
            # Try exact match first, then case-insensitive
            if key in schema_properties:
                prop_name = key
                prop_def = schema_properties[key]
            elif key.lower() in schema_lookup:
                prop_name, prop_def = schema_lookup[key.lower()]
            else:
                raise ValidationError(
                    f"Unknown property: {key!r}",
                    {"available": list(schema_properties.keys())}
                )

            prop_type = prop_def.get("type")
            if prop_type is None:
                raise ValidationError(f"Property {key!r} has no type in schema")

            try:
                coerced = coerce_value(prop_type, value)
            except ValueError as e:
                raise ValidationError(str(e))

            result[prop_name] = coerced

        return result
