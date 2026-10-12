"""
M4 Deployment Pipeline.

Exports key components for integration.
"""

from lab_config import LOCAL_LAB
if not LOCAL_LAB:
    from deploy.pipeline import DeploymentPipeline
from deploy.models import ChangeRequest, Job, JobStatus, PipelineStage
if not LOCAL_LAB:
    from deploy.api import router, setup_pipeline
