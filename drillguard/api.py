"""Local FastAPI surface — read-only screening, no control integrations."""

import io
from typing import Any

import pandas as pd

from .detector import detect
from .ingestion import IngestionError, validate_frame
from .report import build_report
from .schema import ALGORITHM_VERSION, schema_manifest

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
        }

    @app.get("/schema")
    def schema() -> dict[str, Any]:
        return schema_manifest()

    @app.post("/screen")
    async def screen(
        file: UploadFile = File(...),
        origin: str = "field_unvalidated",
    ) -> JSONResponse:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
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
