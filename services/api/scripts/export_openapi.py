"""Export FastAPI's generated OpenAPI document."""

import json
from pathlib import Path

from app.main import app


target = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "openapi.generated.json"
target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(target)
