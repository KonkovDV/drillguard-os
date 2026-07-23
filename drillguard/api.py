"""Local FastAPI surface — read-only screening, no control integrations."""

import io
from typing import Any

import pandas as pd

from .detector import detect
from .ingestion import IngestionError, validate_frame
from .report import build_report
from .schema import ALGORITHM_VERSION, ALLOWED_DATA_ORIGINS, schema_manifest

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def create_app():
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.responses import JSONResponse

    app = FastAPI(
        title="DrillGuard OS",
        version=ALGORITHM_VERSION,
        description=(
            "Local advisory screening API. No SCADA/ACS writes and no control actions. "
            "heuristic_score is not a probability."
        ),
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "algorithm_version": ALGORITHM_VERSION,
            "control_actions": False,
            "network_side_effects": False,
            "claim_level": "synthetic_only",
            "requires_field_validation": True,
        }

    @app.get("/schema")
    def schema() -> dict[str, Any]:
        return schema_manifest()

    @app.post("/screen")
    async def screen(
        file: UploadFile = File(...),  # noqa: B008
        origin: str = "field_unvalidated",
    ) -> JSONResponse:
        if origin not in ALLOWED_DATA_ORIGINS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid origin '{origin}'. "
                    f"Allowed: {sorted(ALLOWED_DATA_ORIGINS)}. "
                    "field_validated is not accepted without an approved validation workflow."
                ),
            )
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File too large")
            chunks.append(chunk)
        raw = b"".join(chunks)
        try:
            df = pd.read_csv(io.BytesIO(raw))
            df = validate_frame(df, source=file.filename or "upload.csv")
        except IngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {exc}") from exc
        out = detect(df)
        report = build_report(
            out,
            data_origin=origin,
            source_id=file.filename or "upload.csv",
        )
        return JSONResponse(report)

    return app


def main() -> None:
    """Local read-only server: python -m drillguard.api"""
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
