"""One project/feeder boundary shared by calculation and spreadsheet ingestion."""

from lv_assist.i18n import tr
from lv_assist.models import FeederInput, ProjectSpec


def validated_project_inputs(project, feeders):
    project = ProjectSpec.model_validate(project.model_dump())
    feeders = [FeederInput.model_validate(feeder.model_dump()) for feeder in feeders]
    if not feeders or len({feeder.feeder_id for feeder in feeders}) != len(feeders):
        raise ValueError(tr('audit_input_invalid'))
    return project, feeders
