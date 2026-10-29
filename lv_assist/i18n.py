# -*- coding: utf-8 -*-
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar

_EXPORT_LANGUAGE = ContextVar('lvassist_export_language', default=None)

SUPPORTED_LANGUAGES = ("fa", "en", "de")

LANGUAGE_META = {
    "fa": {"name": "فارسی", "direction": "rtl", "font": "Tahoma"},
    "en": {"name": "English", "direction": "ltr", "font": "Segoe UI"},
    "de": {"name": "Deutsch", "direction": "ltr", "font": "Segoe UI"},
}

_TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations")
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


class I18n:
    def __init__(self):
        self._language = "fa"
        self._tables = {}
        self._config_path = None

    def set_config_path(self, path):
        self._config_path = path
        self.load_config()

    def load_config(self):
        try:
            with open(self._config_path, encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("language")
            if lang in SUPPORTED_LANGUAGES:
                self._language = lang
        except (OSError, json.JSONDecodeError):
            pass

    def save_config(self, extra=None):
        if not self._config_path:
            return
        try:
            with open(self._config_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data["language"] = self._language
        if extra:
            data.update(extra)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_language(self):
        scope = _EXPORT_LANGUAGE.get()
        if scope is not None and scope[0] is self:
            return scope[1]
        return self._language

    @contextmanager
    def export_language(self, language, tables):
        token = _EXPORT_LANGUAGE.set((self, language, tables))
        try:
            yield
        finally:
            _EXPORT_LANGUAGE.reset(token)

    def set_language(self, lang):
        if lang in SUPPORTED_LANGUAGES:
            self._language = lang
            self.save_config()

    def get_theme(self):
        try:
            with open(self._config_path, encoding="utf-8") as f:
                return json.load(f).get("theme", "dark")
        except (OSError, json.JSONDecodeError):
            return "dark"

    def set_theme(self, theme):
        self.save_config(extra={"theme": theme})

    def direction(self):
        return LANGUAGE_META[self.get_language()]["direction"]

    def font_family(self):
        return LANGUAGE_META[self.get_language()]["font"]

    def _table(self, lang):
        scope = _EXPORT_LANGUAGE.get()
        if scope is not None and scope[0] is self:
            return scope[2][lang]
        if lang not in self._tables:
            try:
                with open(os.path.join(_TRANSLATIONS_DIR, f"{lang}.json"), encoding="utf-8") as f:
                    self._tables[lang] = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._tables[lang] = {}
        return self._tables[lang]

    def tr(self, key, **fmt):
        text = None
        scope = _EXPORT_LANGUAGE.get()
        for lang in (self.get_language(), "fa", "en"):
            table = scope[2][lang] if scope is not None and scope[0] is self else self._table(lang)
            text = table.get(key)
            if text is not None:
                break
        if text is None:
            text = key
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError):
            pass
        if self.get_language() == "fa":
            text = text.translate(_FA_DIGITS)
        return text


i18n = I18n()


def tr(key, **fmt):
    return i18n.tr(key, **fmt)
