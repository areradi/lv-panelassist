"""Reject stale or mixed run identities at the bundle API boundary."""

import json
import sqlite3

from lv_assist.models import FeederInput, ProjectSpec
from lv_assist.run_metadata import run_is_current


class ExportSnapshotError(ValueError):
    """Recalculation is required before this bundle can be published."""


def require_current_bundle(project, outputs, summary, catalog_path):
    try:
        metadata = summary.run_metadata
        if metadata is None:
            raise ValueError('Missing run identity')
        snapshot = json.loads(metadata.input_snapshot_json)
        recorded_project = ProjectSpec.model_validate(snapshot['project'])
        inputs = [FeederInput.model_validate(row) for row in snapshot['feeders']]
        if (not inputs or not outputs or metadata.project_revision != project.project_revision
                or recorded_project.model_dump(mode='json') != project.model_dump(mode='json')
                or [row.feeder_id for row in inputs] != [row.feeder_id for row in outputs]
                or any(row.run_metadata != metadata for row in outputs)
                or not run_is_current(metadata, project, inputs, catalog_path)):
            raise ValueError('Stale or mixed run')
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as error:
        raise ExportSnapshotError('Recalculate before exporting this bundle') from error
