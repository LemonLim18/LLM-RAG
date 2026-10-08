import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .inventory_service import DeviceNotFoundError, get_inventory_device, list_inventory_devices
from .models import HealthResponse, InventoryDetailResponse, InventoryListResponse, RuntimeStatusResponse
from .runtime_status import runtime_status
from .planning_models import PlanningErrorResponse, PlanningRequest, PlanningResponse
from .planning_service import PlanningError, PlanningService


def _development_origins() -> list[str]:
    configured = os.environ.get(
        "NETWORK_RAG_CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app() -> FastAPI:
    application = FastAPI(
        title="Network RAG Workbench API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_development_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["runtime"])
    async def health() -> HealthResponse:
        return HealthResponse()

    @application.get("/api/v1/runtime/status", response_model=RuntimeStatusResponse, tags=["runtime"])
    async def get_runtime_status() -> RuntimeStatusResponse:
        return runtime_status()

    @application.get("/api/v1/inventory/devices", response_model=InventoryListResponse, tags=["inventory"])
    async def inventory_devices() -> InventoryListResponse:
        return list_inventory_devices()

    @application.get("/api/v1/inventory/devices/{device_id}", response_model=InventoryDetailResponse, tags=["inventory"])
    async def inventory_device(device_id: str) -> InventoryDetailResponse:
        try:
            return get_inventory_device(device_id)
        except DeviceNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": str(error),
                    "device_id": error.device_id,
                },
            ) from error

    planning = PlanningService()

    @application.post("/api/v1/planning/sessions", response_model=PlanningResponse,
                      responses={code: {"model": PlanningErrorResponse} for code in (409, 500, 503)},
                      tags=["planning"])
    def create_planning_session(request: PlanningRequest) -> PlanningResponse:
        # FastAPI runs synchronous endpoints in its worker pool, not the event loop.
        try:
            return planning.create(request)
        except PlanningError as error:
            raise HTTPException(status_code=error.status, detail={
                "code": error.code, "message": str(error),
                "client_request_id": str(request.client_request_id),
            }) from error

    return application


app = create_app()
