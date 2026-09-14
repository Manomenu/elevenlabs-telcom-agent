"""Backend webhooków dla agenta ElevenLabs.

Dwa endpointy:
  POST /check-if-serviceable  — tool wołany przez agenta w trakcie rozmowy
  POST /register-call         — post-procedure hook, zapisuje wywołanie do logu
"""

import json
import logging
import os
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, model_validator

# Katalog na artefakty jest montowany jako volume; w kontenerze i lokalnie ta
# sama ścieżka względna działa inaczej, więc bierzemy ją z env.
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", ".artifacts"))
AGENT_LOG = ARTIFACTS_DIR / "agent.log"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("webhook")

app = FastAPI(title="ElevenLabs telco agent webhooks")


def append_log(event: str, payload: dict[str, Any]) -> None:
    """Dopisuje jedno zdarzenie jako linię JSON (NDJSON).

    Format linia-po-linii, żeby log dało się czytać `tail -f` i parsować
    bez wczytywania całości.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **payload,
    }
    with AGENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("%s %s", event, json.dumps(payload, ensure_ascii=False)[:300])


class ServiceabilityRequest(BaseModel):
    """Adres do sprawdzenia.

    Agent ma podać street + (zip) ALBO street + (city i state). Walidujemy to
    tutaj, a nie tylko w opisie toola, żeby niekompletne wywołanie dostało
    czytelny błąd zamiast losowego wyniku.
    """

    street: str = Field(..., min_length=1)
    zip: str | None = None
    city: str | None = None
    state: str | None = None

    @model_validator(mode="after")
    def require_zip_or_city_state(self) -> "ServiceabilityRequest":
        if self.zip:
            return self
        if self.city and self.state:
            return self
        raise ValueError(
            "Provide either (street and zip) or (street and city and state)."
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check-if-serviceable")
def check_if_serviceable(request: ServiceabilityRequest) -> dict[str, Any]:
    """Zwraca losowo serviceable/not serviceable — to zaślepka, nie realny check."""
    serviceable = random.choice([True, False])

    address = {
        "street": request.street,
        "zip": request.zip,
        "city": request.city,
        "state": request.state,
    }
    result = {
        "serviceable": serviceable,
        "message": (
            "Service is available at this address."
            if serviceable
            else "Service is not available at this address."
        ),
        "address": {key: value for key, value in address.items() if value},
    }
    append_log("check-if-serviceable", result)
    return result


@app.post("/register-call")
async def register_call(request: Request) -> dict[str, Any]:
    """Post-procedure hook. Przyjmuje cokolwiek agent wyśle i zapisuje do logu.

    Bez modelu pydantic celowo: kształt post-call payloadu zależy od
    konfiguracji agenta, a odrzucenie go walidacją zgubiłoby zdarzenie.
    """
    try:
        body = await request.json()
    except Exception:
        body = {"raw": (await request.body()).decode("utf-8", "replace")}

    append_log("register-call", {"payload": body})
    return {"registered": True}
