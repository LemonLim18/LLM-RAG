import os
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .inventory_service import DeviceNotFoundError, get_inventory_device, list_inventory_devices
from .models import HealthResponse, InventoryDetailResponse, InventoryListResponse, RuntimeStatusResponse
from .runtime_status import runtime_status
from .planning_models import AnswerRequest, AnswerResponse, PlanningErrorResponse, PlanningRequest, PlanningResponse
from .planning_service import PlanningError, PlanningService
from .planning_models import CreationOutcome, SavedSessionResponse, SavedSessionErrorResponse
from .saved_sessions import get_saved_session
from .inventory_registration import DeviceRegistration, InventoryErrorResponse
from .generated_originals import ArtifactId, CaptureRequest, CaptureResponse, GeneratedOriginal, OriginalList, list_originals, read_original
from .working_documents import DocumentId, OpenWorkingRequest, OpenWorkingResponse, SaveWorkingRequest, WorkingDocument, WorkingList, open_document, read_document, list_documents, save_document
from .edit_models import EditRequest, EditResponse
from .edit_service import EditService


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
        allow_methods=["GET", "POST", "PUT"],
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
    edits = EditService(planning)

    def artifact_error(error):
        return HTTPException(status_code=error.status, detail={'code': error.code, 'message': str(error)},
                             headers={'Cache-Control': 'no-store'})

    @application.post('/api/v1/workbench/working-documents/{document_id}/propose-edit',
                      response_model=EditResponse, tags=['working documents'])
    def propose_edit(document_id: DocumentId, request: EditRequest, response: Response) -> EditResponse:
        response.headers['Cache-Control'] = 'no-store'
        try:
            return edits.propose(document_id, request)
        except PlanningError as error:
            raise artifact_error(error) from error

    @application.post('/api/v1/workbench/working-documents', response_model=OpenWorkingResponse,
                      responses={201: {'model': OpenWorkingResponse}, **{code: {'model': SavedSessionErrorResponse} for code in (404, 409, 413, 503)}}, tags=['working documents'])
    def open_working(request: OpenWorkingRequest, response: Response) -> OpenWorkingResponse:
        response.headers['Cache-Control'] = 'no-store'
        try:
            result = planning.mutate_working_document(lambda: open_document(request))
            response.status_code = 201 if result.outcome == 'created' else 200
            return result
        except PlanningError as error:
            raise artifact_error(error) from error

    @application.get('/api/v1/workbench/working-documents', response_model=WorkingList,
                     responses={code: {'model': SavedSessionErrorResponse} for code in (409, 503)}, tags=['working documents'])
    def working_documents(response: Response) -> WorkingList:
        response.headers['Cache-Control'] = 'no-store'
        try: return list_documents()
        except PlanningError as error: raise artifact_error(error) from error

    @application.get('/api/v1/workbench/working-documents/{document_id}', response_model=WorkingDocument,
                     responses={code: {'model': SavedSessionErrorResponse} for code in (404, 409, 503)}, tags=['working documents'])
    def working_document(document_id: DocumentId, response: Response) -> WorkingDocument:
        response.headers['Cache-Control'] = 'no-store'
        try: return read_document(document_id)
        except PlanningError as error: raise artifact_error(error) from error

    @application.put('/api/v1/workbench/working-documents/{document_id}', response_model=WorkingDocument,
                     responses={code: {'model': SavedSessionErrorResponse} for code in (404, 409, 413, 503)}, tags=['working documents'])
    def save_working(document_id: DocumentId, request: SaveWorkingRequest, response: Response) -> WorkingDocument:
        response.headers['Cache-Control'] = 'no-store'
        try: return planning.mutate_working_document(lambda: save_document(document_id, request))
        except PlanningError as error: raise artifact_error(error) from error

    @application.post('/api/v1/workbench/artifacts/generated-originals', response_model=CaptureResponse,
                      responses={201: {'model': CaptureResponse}, **{code: {'model': SavedSessionErrorResponse} for code in (404, 409, 413, 503)}}, tags=['originals'])
    def capture_generated_original(request: CaptureRequest, response: Response) -> CaptureResponse:
        response.headers['Cache-Control'] = 'no-store'
        try:
            result = planning.capture_original(request)
            response.status_code = 201 if result.outcome == 'created' else 200
            return result
        except PlanningError as error:
            raise artifact_error(error) from error

    @application.get('/api/v1/workbench/artifacts/generated-originals', response_model=OriginalList,
                     responses={code: {'model': SavedSessionErrorResponse} for code in (409, 503)}, tags=['originals'])
    def generated_originals(response: Response) -> OriginalList:
        response.headers['Cache-Control'] = 'no-store'
        try:
            return list_originals()
        except PlanningError as error:
            raise artifact_error(error) from error

    @application.get('/api/v1/workbench/artifacts/generated-originals/{artifact_id}', response_model=GeneratedOriginal,
                     responses={code: {'model': SavedSessionErrorResponse} for code in (404, 409, 503)}, tags=['originals'])
    def generated_original(artifact_id: ArtifactId, response: Response) -> GeneratedOriginal:
        response.headers['Cache-Control'] = 'no-store'
        try:
            return read_original(artifact_id)
        except PlanningError as error:
            raise artifact_error(error) from error

    @application.post('/api/v1/inventory/devices', response_model=InventoryDetailResponse, status_code=201,
                      responses={code: {'model': InventoryErrorResponse} for code in (409, 503)}, tags=['inventory'])
    def register_inventory_device(request: DeviceRegistration) -> InventoryDetailResponse:
        try:
            return planning.register_inventory_device(request)
        except PlanningError as error:
            raise HTTPException(status_code=error.status, detail={
                'code': error.code, 'message': str(error),
                'current_inventory_revision': getattr(error, 'revision', None),
            }) from error

    @application.get("/api/v1/planning/requests/{client_request_id}", response_model=CreationOutcome,
                     responses={503: {"model": SavedSessionErrorResponse}}, tags=["planning"])
    def read_creation_outcome(client_request_id: UUID, response: Response) -> CreationOutcome:
        response.headers["Cache-Control"] = "no-store"
        try:
            return planning.lookup_creation(client_request_id)
        except PlanningError as error:
            raise HTTPException(status_code=error.status, detail={"code": error.code, "message": str(error)},
                                headers={"Cache-Control": "no-store"}) from error

    @application.get("/api/v1/planning/sessions/{session_id}", response_model=SavedSessionResponse,
                     responses={code: {"model": SavedSessionErrorResponse} for code in (404, 409, 503)},
                     tags=["planning"])
    def read_planning_session(session_id: UUID, response: Response) -> SavedSessionResponse:
        response.headers["Cache-Control"] = "no-store"
        try:
            return get_saved_session(str(session_id))
        except PlanningError as error:
            raise HTTPException(status_code=error.status, detail={
                "code": error.code, "message": str(error),
            }, headers={"Cache-Control": "no-store"}) from error

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

    @application.post("/api/v1/planning/sessions/{session_id}/answers", response_model=AnswerResponse,
                      responses={code: {"model": PlanningErrorResponse} for code in (404, 409, 422, 500, 503)},
                      tags=["planning"])
    def answer_planning_question(session_id: UUID, request: AnswerRequest) -> AnswerResponse:
        try:
            return planning.answer(str(session_id), request)
        except PlanningError as error:
            raise HTTPException(status_code=error.status, detail={
                "code": error.code, "message": str(error), "client_request_id": str(request.client_request_id),
                "current_session": error.current_session.model_dump(mode="json") if error.current_session else None,
            }) from error

    return application


app = create_app()
