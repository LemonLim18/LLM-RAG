"""CogniShield entry point. Mode selected before optional integrations import."""
from lab_config import LOCAL_LAB

if LOCAL_LAB:
    from local_app import app
else:
    from integrated_backend import *  # noqa: F403; preserved normal integration entry point

if not LOCAL_LAB:
    from environment_api import router as environment_router
    app.include_router(environment_router)
