"""Simulated browser outcomes test integrity, not real PDF rendering."""

import subprocess
from pathlib import Path

import pytest

from lv_assist.outputs import PdfExporter

PDF = b'%PDF-1.4\nsynthetic browser output\n%%EOF\n'


@pytest.fixture
def paths(tmp_path, monkeypatch):
    source, target = tmp_path / 'input space.html', tmp_path / 'report.pdf'
    source.write_text('<html>test</html>')
    target.write_bytes(b'previous document')
    monkeypatch.setattr(PdfExporter, '_find_browser', lambda: 'synthetic-browser')
    return source, target


@pytest.mark.parametrize('outcome,reason', [
    ('missing', 'invalid_pdf'), ('empty', 'invalid_pdf'), ('html', 'invalid_pdf'),
    ('truncated', 'invalid_pdf'), ('error', 'browser_failed'), ('timeout', 'timeout'),
    ('launch', 'browser_failed'),
])
def test_failure_never_accepts_or_overwrites_previous_file(paths, monkeypatch, outcome, reason):
    source, target = paths
    profiles = []

    def run(args, **kwargs):
        profiles.append(Path(next(arg.split('=', 1)[1] for arg in args if arg.startswith('--user-data-dir='))))
        output = Path(next(arg.split('=', 1)[1] for arg in args if arg.startswith('--print-to-pdf=')))
        assert output != target
        assert args[-1] == source.as_uri()
        if outcome == 'timeout':
            raise subprocess.TimeoutExpired(args, 120)
        if outcome == 'error':
            raise subprocess.CalledProcessError(1, args)
        if outcome == 'launch':
            raise OSError('synthetic launch failure')
        if outcome != 'missing':
            output.write_bytes({'empty': b'', 'html': b'<html>error</html>', 'truncated': b'%PDF-1.4'}[outcome])

    monkeypatch.setattr('lv_assist.outputs.subprocess.run', run)
    result = PdfExporter.export_html_to_pdf_result(str(source), str(target))
    assert not result.success and result.reason == reason
    assert target.read_bytes() == b'previous document'
    assert all(not profile.parent.exists() for profile in profiles)


def test_success_replaces_only_with_new_output_and_isolates_attempts(paths, monkeypatch):
    source, target = paths
    folders = []

    def run(args, **kwargs):
        output = Path(next(arg.split('=', 1)[1] for arg in args if arg.startswith('--print-to-pdf=')))
        folders.append(output.parent)
        output.write_bytes(PDF)
        assert '--no-sandbox' not in args

    monkeypatch.setattr('lv_assist.outputs.subprocess.run', run)
    assert PdfExporter.export_html_to_pdf(str(source), str(target)) is True
    assert PdfExporter.export_html_to_pdf_result(str(source), str(target)).reason == 'ok'
    assert target.read_bytes() == PDF
    assert folders[0] != folders[1]
    assert all(not folder.exists() for folder in folders)


def test_missing_browser_has_own_reason(paths, monkeypatch):
    source, target = paths
    monkeypatch.setattr(PdfExporter, '_find_browser', lambda: None)
    assert PdfExporter.export_html_to_pdf_result(str(source), str(target)).reason == 'missing_browser'
    assert PdfExporter.export_html_to_pdf(str(source), str(target)) is False
    assert target.read_bytes() == b'previous document'


@pytest.mark.parametrize('same_path', [True, False])
def test_missing_or_conflicting_input_is_rejected(paths, same_path):
    source, target = paths
    if same_path:
        source = target
    else:
        source.unlink()
    result = PdfExporter.export_html_to_pdf_result(str(source), str(target))
    assert result.reason == 'invalid_input' and not result.success
    assert target.read_bytes() == b'previous document'


def test_publish_failure_preserves_old_document(paths, monkeypatch):
    source, target = paths

    def run(args, **kwargs):
        Path(next(arg.split('=', 1)[1] for arg in args if arg.startswith('--print-to-pdf='))).write_bytes(PDF)

    def replace(*args):
        raise PermissionError('synthetic locked target')

    monkeypatch.setattr('lv_assist.outputs.subprocess.run', run)
    monkeypatch.setattr('lv_assist.outputs.os.replace', replace)
    assert PdfExporter.export_html_to_pdf_result(str(source), str(target)).reason == 'write_failed'
    assert target.read_bytes() == b'previous document'


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_uses_specific_reason_and_removes_private_html(paths, monkeypatch, locale):
    from types import SimpleNamespace

    from lv_assist.gui import LVAssistApp
    from lv_assist.i18n import i18n, tr
    from lv_assist.outputs import PdfExportResult

    previous = i18n.get_language()
    _source, target = paths
    attempts, messages = [], []

    def render(path, *args):
        Path(path).write_text('<html>private report</html>')

    def export(html, pdf):
        assert Path(html).is_file()
        assert pdf == str(target)
        attempts.append(Path(html))
        return PdfExportResult(False, 'timeout')

    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(target))
    monkeypatch.setattr('lv_assist.gui.PrintableReportExporter.generate_html_report', render)
    monkeypatch.setattr(PdfExporter, 'export_html_to_pdf_result', export)
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: messages.append(message))
    app = SimpleNamespace(_get_results=lambda: ([], None, []), current_project=None)
    try:
        i18n.set_language(locale)
        LVAssistApp.action_export_pdf(app)
        LVAssistApp.action_export_pdf(app)
        assert messages == [tr('msg_pdf_timeout')] * 2
        assert attempts[0] != attempts[1]
        assert all(not path.parent.exists() for path in attempts)
        assert target.read_bytes() == b'previous document'
    finally:
        i18n.set_language(previous)
