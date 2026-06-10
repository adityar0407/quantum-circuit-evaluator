from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import circuits, runs, targets


app = FastAPI(title="Quantum Circuit Evaluator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517[0-9]",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(circuits.router, prefix="/api/circuits", tags=["circuits"])
app.include_router(targets.router, prefix="/api/targets", tags=["targets"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
