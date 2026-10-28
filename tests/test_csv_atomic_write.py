"""Failure injection at CSV publication boundaries; original bytes must survive."""

import csv
from types import SimpleNamespace

import pytest

from lv_assist.csv_export import CsvMode, write_csv
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr


@pytest.mark.parametrize('mode', list(CsvMode))
@pytest.mark.parametrize('failure', ['rows', 'encoding', 'sync', 'publish', 'create'])
def test_failed_export_preserves_previous_file_and_cleans_temporary_output(tmp_path, monkeypatch, mode, failure):
    path = tmp_path / 'report.csv'
    path.write_bytes(b'previous valid CSV')
    def fail(*args, **kwargs):
        raise OSError('synthetic disk/permission failure')
    def rows():
        yield ['new row', 12]
        if failure == 'rows':
            raise OSError('synthetic mid-write failure')
        yield ['\ud800' if failure == 'encoding' else '=INCOMING', 1]
    if failure == 'sync':
        monkeypatch.setattr('lv_assist.csv_export.os.fsync', fail)
    elif failure == 'publish':
        monkeypatch.setattr('lv_assist.csv_export.os.replace', fail)
    elif failure == 'create':
        monkeypatch.setattr('lv_assist.csv_export.tempfile.NamedTemporaryFile', fail)
    with pytest.raises((OSError, UnicodeError)):
        write_csv(path, ['text', 'number'], rows(), mode=mode)
    assert path.read_bytes() == b'previous valid CSV'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('mode', list(CsvMode))
def test_complete_output_replaces_previous_file_without_leftovers(tmp_path, mode):
    path = tmp_path / 'report.csv'
    path.write_bytes(b'previous valid CSV')
    write_csv(path, ['text', 'number'], iter([['=INCOMING', -3.5]]), mode=mode)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream))
    assert rows[1] == [("'=INCOMING" if mode == CsvMode.SPREADSHEET else '=INCOMING'), '-3.5']
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('choice', [True, False])
def test_gui_write_error_shows_failure_instead_of_success(tmp_path, monkeypatch, locale, choice):
    path = tmp_path / 'report.csv'
    path.write_bytes(b'original')
    previous = i18n.get_language()
    errors, successes = [], []
    monkeypatch.setattr('lv_assist.gui.messagebox.askyesnocancel', lambda *args: choice)
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: errors.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    def exporter(filename, *args, validations, **kwargs):
        def rows():
            yield ['partly written']
            raise OSError('synthetic write failure')
        write_csv(filename, ['text'], rows(), **kwargs)
    app = SimpleNamespace(_get_results=lambda: ([], None, []), current_project=None)
    try:
        i18n.set_language(locale)
        LVAssistApp._export_csv_for_target(app, exporter, 'Parts.csv')
        assert errors == [tr('csv_write_failed')]
        assert not successes
        assert path.read_bytes() == b'original'
    finally:
        i18n.set_language(previous)
