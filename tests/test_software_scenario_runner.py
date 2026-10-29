"""Exercise the runner with actual documents and deliberate observable drift."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import openpyxl
import pytest

from scripts import run_regression_scenarios as runner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def manifest():
    result, _ = runner.load_scenarios(runner.DEFAULT_SCENARIOS)
    result['scenarios'] = result['scenarios'][:1]
    return result


def test_actual_default_cli_runs_ten_cases_in_three_locales_from_any_directory(tmp_path):
    database = runner.catalog_repo.db_path.read_bytes()
    definitions = runner.DEFAULT_SCENARIOS.read_bytes()
    completed = subprocess.run([sys.executable, str(ROOT / 'scripts/run_regression_scenarios.py')],
                               cwd=tmp_path, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report['status'] == 'PASS' and report['counts'] == {'PASS': 30}
    assert report['scenario_count'] == 10 and len(report['runs']) == 30
    assert {row['locale'] for row in report['runs']} == {'fa', 'en', 'de'}
    assert report['evidence_kind'] == 'SYNTHETIC_SOFTWARE_REGRESSION'
    assert report['engineering_verification'] == 'NOT_VERIFIED' and report['independent_reference_cases'] == 0
    assert report['catalog_unchanged'] and report['scenario_set_hash'] and report['runner_hash']
    assert all(row['differences'] == [] for row in report['runs'])
    assert runner.catalog_repo.db_path.read_bytes() == database
    assert runner.DEFAULT_SCENARIOS.read_bytes() == definitions
    assert list(tmp_path.iterdir()) == []


def test_actual_cli_difference_has_expected_actual_and_nonzero_exit_without_rewriting_manifest(tmp_path, manifest):
    manifest['scenarios'][0]['expected']['bus_input_ka'] = 99
    path = tmp_path / 'changed.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    before = path.read_bytes()
    completed = subprocess.run([sys.executable, str(ROOT / 'scripts/run_regression_scenarios.py'),
                                '--locale', 'en', '--scenarios', str(path)],
                               cwd=tmp_path, capture_output=True, text=True, check=False)
    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report['status'] == 'FAIL' and report['counts'] == {'FAIL': 1}
    assert {'field': 'bus_input_ka', 'expected': 99, 'actual': None} in report['runs'][0]['differences']
    assert report['engineering_verification'] == 'NOT_VERIFIED' and path.read_bytes() == before


@pytest.mark.parametrize('kind', ['html', 'xlsx'])
def test_real_document_corruption_is_reported_as_difference(manifest, monkeypatch, kind):
    if kind == 'html':
        original = runner.PrintableReportExporter.generate_html_report
        def corrupt(*args):
            original(*args)
            path = Path(args[0])
            html = path.read_text(encoding='utf-8')
            marker = '<b>' + args[4][0].rule_id + '</b>'
            assert marker in html
            path.write_text(html.replace(marker, '<b>REGRESSION_CORRUPTED</b>', 1), encoding='utf-8')
        monkeypatch.setattr(runner.PrintableReportExporter, 'generate_html_report', corrupt)
    else:
        original = runner.ExcelExporter.export_to_excel
        def corrupt(*args):
            original(*args)
            workbook = openpyxl.load_workbook(args[0])
            try:
                workbook['03_Validation_Log']['D2'] = 'REGRESSION_CORRUPTED'
                workbook.save(args[0])
            finally:
                workbook.close()
        monkeypatch.setattr(runner.ExcelExporter, 'export_to_excel', corrupt)
    report = runner.run_scenarios(manifest, ('en',))
    assert report['status'] == 'FAIL'
    assert {'field': kind + '_validation_matches', 'expected': True, 'actual': False} in report['runs'][0]['differences']


def test_numeric_locale_drift_is_detected_and_previous_language_restored(manifest, monkeypatch):
    original = runner.observe
    previous = runner.i18n.get_language()
    def drift(*args):
        observed, identity, statuses = original(*args)
        if runner.i18n.get_language() == 'fa':
            observed['design_current_ib_a'] += 1
        return observed, identity, statuses
    monkeypatch.setattr(runner, 'observe', drift)
    before = copy.deepcopy(manifest)
    report = runner.run_scenarios(manifest, ('en', 'fa', 'de'))
    assert report['counts'] == {'PASS': 2, 'FAIL': 1}
    assert report['runs'][1]['differences'][0]['field'] == 'locale.design_current_ib_a'
    assert report['runs'][1]['differences'][0]['baseline_locale'] == 'en'
    assert runner.i18n.get_language() == previous and manifest == before


def test_export_error_is_reported_continues_next_case_and_cleans_temporary_files(manifest, monkeypatch, tmp_path):
    second = copy.deepcopy(manifest['scenarios'][0])
    second['id'] = 'after_error'
    manifest['scenarios'].append(second)
    original = runner.PrintableReportExporter.generate_html_report
    calls = 0
    def fail_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError('Synthetic export error')
        return original(*args)
    monkeypatch.setattr(runner.PrintableReportExporter, 'generate_html_report', fail_once)
    monkeypatch.setattr(runner, 'TemporaryDirectory', lambda **kwargs: TemporaryDirectory(dir=tmp_path, **kwargs))
    previous = runner.i18n.get_language()
    report = runner.run_scenarios(manifest, ('en',))
    assert report['status'] == 'FAIL' and report['counts'] == {'ERROR': 1, 'PASS': 1}
    assert report['runs'][0]['error'] == {'type': 'OSError', 'message': 'Synthetic export error'}
    assert runner.i18n.get_language() == previous and list(tmp_path.iterdir()) == []


def test_source_identity_change_never_receives_passing_report(manifest, monkeypatch):
    original = runner.observe
    def changed(*args):
        observed, identity, statuses = original(*args)
        identity['catalog_version'] = 'different-source'
        return observed, identity, statuses
    monkeypatch.setattr(runner, 'observe', changed)
    report = runner.run_scenarios(manifest, ('en',))
    assert report['status'] == 'FAIL' and report['counts'] == {'ERROR': 1}
    assert 'source identity changed' in report['runs'][0]['error']['message']


@pytest.mark.parametrize('change', ['kind', 'version', 'duplicate_id', 'unknown_field', 'bool_coercion',
                                   'invalid_number', 'empty_cases', 'missing_object', 'bad_text',
                                   'unknown_project_input', 'unknown_feeder_input'])
def test_malformed_scenarios_fail_instead_of_silently_ignoring_expectations(tmp_path, manifest, change):
    if change == 'kind':
        manifest['evidence_kind'] = 'INDEPENDENTLY_VERIFIED'
    elif change == 'version':
        manifest['schema_version'] = True
    elif change == 'duplicate_id':
        manifest['scenarios'].append(copy.deepcopy(manifest['scenarios'][0]))
    elif change == 'unknown_field':
        manifest['common_expected']['typo_field'] = True
    elif change == 'bool_coercion':
        manifest['common_expected']['pe_unknown'] = 1
    elif change == 'invalid_number':
        manifest['scenarios'][0]['expected']['bus_input_ka'] = True
    elif change == 'empty_cases':
        manifest['scenarios'] = []
    elif change == 'missing_object':
        manifest['base_feeder'] = None
    elif change == 'unknown_project_input':
        manifest['scenarios'][0]['project']['typo_voltage'] = 400
    elif change == 'unknown_feeder_input':
        manifest['base_feeder']['typo_power'] = 5
    else:
        manifest['base_feeder']['description'] = 'bad\x00text'
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises((ValueError, TypeError)):
        runner.load_scenarios(path)


def test_duplicate_json_keys_and_invalid_cli_input_produce_structured_error(tmp_path, capsys):
    path = tmp_path / 'duplicate.json'
    path.write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
    assert runner.main(['--scenarios', str(path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'ERROR' and 'Duplicate scenario key' in report['error']['message']
    assert report['engineering_verification'] == 'NOT_VERIFIED' and report['independent_reference_cases'] == 0
