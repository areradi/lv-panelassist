# -*- coding: utf-8 -*-
"""
مدیریت کاتالوگ تجهیزات، قواعد سلکتیویته، منحنی‌های قطع و جداول استاندارد مبتنی بر SQLite.
رفع یافته‌های ممیزی: F-001, F-003, F-005, F-006, F-007, F-008, F-016, F-017.
منبع حقیقت: lv_assist/data/lv_assist.db که توسط migrate_to_sqlite.py از فایل‌های JSON ساخته می‌شود.
"""

from __future__ import annotations

import math
import sqlite3
from contextlib import closing
from pathlib import Path
from lv_assist.ip_rating import ip_meets
from lv_assist.rating_table_validation import ampacity_table, derating_table, pe_sections, number, identity, invalid
from lv_assist.trip_curve_validation import validated_curve, positive_curve_argument
from lv_assist.text_validation import require_exportable_text
from lv_assist.registry_validation import registry_entries, registry_identifier, registry_rows
from lv_assist.datasheet_validation import DATASHEET_COLUMNS, datasheet_rows
from lv_assist.run_metadata import catalog_file_hash
from lv_assist.catalog_validation import CatalogValidationError, device_rows, validated_rules, curve_rows, validated_curves, breaking_capacity_rows
from lv_assist.catalog_validation import DEVICE_COLUMNS, SELECTIVITY_COLUMNS, TRIP_CURVE_COLUMNS, selectivity_rows
from typing import Any, Dict, List, Optional

from lv_assist.models import CatalogDevice, SelectivityRuleRecord, SelectivityEvalState
from lv_assist.i18n import tr, i18n

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "lv_assist.db"


def _ensure_database(db_path: Path = DB_PATH) -> Path:
    """A missing packaged catalog needs explicit recovery, never implicit migration."""
    if not db_path.is_file():
        raise FileNotFoundError(f"Catalog database is missing: {db_path}. Restore a reviewed copy; no database was created.")
    return db_path


class CatalogRepository:
    """مخزن داده‌های مهندسی و کاتالوگ تجهیزات مبتنی بر SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = _ensure_database(db_path)
        self._devices_cache: Optional[List[CatalogDevice]] = None
        self._cache_file_hash: str | None = catalog_file_hash(self.db_path)
        self._rules_cache: Optional[List[SelectivityRuleRecord]] = None
        self._curves_cache: Optional[Dict[str, dict]] = None
        self._standards_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._iz0_cache: Optional[Dict[float, float]] = None
        self._pe_cache: Optional[List[float]] = None

    def _connect(self) -> sqlite3.Connection:
        # Packaged engineering data is never a project store or migration target.
        conn = sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # ۱. تجهیزات کاتالوگ با اعمال صریح کیفیت داده (رفع F-016)
    # ------------------------------------------------------------------
    def load_devices(self) -> List[CatalogDevice]:
        with closing(self._connect()) as conn:
            sources = datasheet_rows(conn.execute('SELECT ' + DATASHEET_COLUMNS + ' FROM datasheet_sources'))
            rows = conn.execute('SELECT ' + DEVICE_COLUMNS + ' FROM catalog_devices').fetchall()
            return device_rows(rows, sources)

    def _invalidate_caches(self):
        self._devices_cache = self._rules_cache = self._curves_cache = None
        self._standards_cache = self._iz0_cache = self._pe_cache = None
        self._cache_file_hash = None

    def _cached(self, attribute, load):
        try:
            current_hash = catalog_file_hash(self.db_path)
            if current_hash != self._cache_file_hash:
                self._invalidate_caches()
                self._cache_file_hash = current_hash
            value = getattr(self, attribute)
            if value is None:
                value = load()
            if catalog_file_hash(self.db_path) != current_hash:
                raise CatalogValidationError(tr("audit_catalog_unstable"))
            setattr(self, attribute, value)
            return value
        except Exception:
            self._invalidate_caches()
            raise

    @property
    def devices(self) -> List[CatalogDevice]:
        return self._cached("_devices_cache", self.load_devices)

    # ------------------------------------------------------------------
    # ۲. قدرت قطع وابسته به ولتاژ پروژه (رفع F-006)
    # ------------------------------------------------------------------
    def get_device_icu_at_voltage(
        self,
        device_id: str,
        nominal_voltage_v: float,
        tolerance_v: float = 0.0,
    ) -> Optional[float]:
        """بازیابی Icu متناسب با ولتاژ نامی؛ در نبود داده دیتاشیت برای آن ولتاژ، None برمی‌گردد."""
        identity(device_id, "device_breaking_capacities", "device_id")
        tolerance = number(tolerance_v, "device_breaking_capacities", "tolerance_v")
        if tolerance != 0:
            raise ValueError("Nearby-voltage Icu lookup requires explicit manufacturer applicability; unsupported.")
        voltage = number(nominal_voltage_v, "device_breaking_capacities", "nominal_voltage_v", positive=True)
        before_hash = catalog_file_hash(self.db_path)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT device_id, voltage_v, icu_ka, ics_ka FROM device_breaking_capacities WHERE device_id = ?",
                (device_id,),
            ).fetchall()
            known_ids = {row[0] for row in conn.execute("SELECT device_id FROM catalog_devices WHERE device_id = ?", (device_id,))}
        ratings = breaking_capacity_rows(rows, known_ids)
        if catalog_file_hash(self.db_path) != before_hash:
            raise CatalogValidationError(tr("audit_catalog_unstable"))
        value = ratings.get((device_id, voltage))
        return value[0] if value is not None else None

    # ------------------------------------------------------------------
    # ۳. ضریب کاهش ظرفیت دمایی با کنترل سقف دما (رفع F-017)
    # ------------------------------------------------------------------
    def get_device_derating_factor(self, device_id: str, internal_temp_c: float) -> Optional[float]:
        """ضریب derating از جدول دما؛ برای دماهای بالای ۵۰ درجه بدون داده معتبر، None برمی‌گردد."""
        identity(device_id, "device_thermal_derating", "device_id")
        temperature = number(internal_temp_c, "device_thermal_derating", "internal_temp_c")
        target_temp = 40.0 if temperature <= 40 else (50.0 if temperature <= 50 else temperature)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT temp_c, derating_factor FROM device_thermal_derating WHERE device_id = ?",
                (device_id,),
            ).fetchall()
        # Retain the legacy <=40/<=50 proposal bins, but never borrow an
        # unrecorded higher-temperature row for a missing requested condition.
        return derating_table(rows).get(target_temp)

    # ------------------------------------------------------------------
    # ۴. بدنه تابلو با شرط IP هدف (رفع F-007)
    # ------------------------------------------------------------------
    def get_compatible_enclosures(self, target_ip: Optional[str] = None) -> List[CatalogDevice]:
        """Proposals matching supported IP categories; no assembly certification."""
        enclosures = [d for d in self.devices if d.device_type == "ENCLOSURE"]
        if not target_ip:
            return enclosures

        return [enc for enc in enclosures if ip_meets(enc.ip_rating, target_ip)]

    # ------------------------------------------------------------------
    # ۵. جداول مرجع کابل و مقاطع استاندارد PE (رفع F-001, F-005, F-008)
    # ------------------------------------------------------------------
    def get_cable_iz0_table_cu_pvc_c(self, loaded_conductors: int = 3) -> Dict[float, float]:
        """جدول کامل جریان‌دهی پایه Cu/PVC/روش C از دیتابیس استاندارد."""
        return self.get_cable_iz0_table("CU", "PVC", "C", loaded_conductors)

    def get_base_cable_iz0(
        self,
        section_mm2: float,
        material: str = "CU",
        insulation: str = "PVC",
        installation_method: str = "C",
        loaded_conductors: int = 3,
    ) -> Optional[float]:
        """جریان‌دهی پایه یک مقطع خاص؛ برای مقطع غیراستاندارد None برمی‌گردد (هرگز مقدار ساختگی)."""
        section = number(section_mm2, "cable_ampacity_reference", "section_mm2", positive=True)
        return self.get_cable_iz0_table(material, insulation, installation_method, loaded_conductors).get(section)

    def get_cable_iz0_table(self, material: str, insulation: str,
                            installation_method: str, loaded_conductors: int) -> dict[float, float]:
        """Exact combination only. An absent table is not a scaled Cu/PVC/C table."""
        material = identity(material, "cable_ampacity_reference", "material")
        insulation = identity(insulation, "cable_ampacity_reference", "insulation")
        installation_method = identity(installation_method, "cable_ampacity_reference", "installation_method")
        if not isinstance(loaded_conductors, int) or isinstance(loaded_conductors, bool) or not 0 < loaded_conductors <= 2**63 - 1:
            invalid("cable_ampacity_reference", "loaded_conductors")
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT section_mm2, iz0_a FROM cable_ampacity_reference "
                "WHERE UPPER(material)=? AND UPPER(insulation)=? AND UPPER(installation_method)=? AND loaded_conductors=?",
                (material, insulation, installation_method, loaded_conductors),
            ).fetchall()
        return ampacity_table(rows)

    def get_pe_standard_sections(self) -> List[float]:
        """فهرست مقاطع استاندارد PE از دیتابیس (بدون سقف مصنوعی)."""
        def load():
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT section_mm2 FROM pe_standard_sections ORDER BY section_mm2 ASC"
                ).fetchall()
                return pe_sections(rows)
        return self._cached("_pe_cache", load)

    def get_standard_pe_section(self, required_pe_mm2: float) -> Optional[float]:
        """اولین مقطع استاندارد PE بزرگ‌تر یا مساوی مقدار لازم؛ اگر فراتر از جدول باشد None."""
        required = number(required_pe_mm2, "pe_standard_sections", "required_pe_mm2", positive=True)
        # Validate the complete inventory before selection, including sections
        # below the requested value. Never extrapolate beyond the recorded table.
        sections = pe_sections({'section_mm2': value} for value in self.get_pe_standard_sections())
        return next((section for section in sections if section >= required), None)

    # ------------------------------------------------------------------
    # ۶. قواعد سلکتیویته، منحنی‌های قطع و رجیستری استانداردها
    # ------------------------------------------------------------------
    def load_selectivity_rules(self) -> List[SelectivityRuleRecord]:
        with closing(self._connect()) as conn:
            sources = datasheet_rows(conn.execute('SELECT ' + DATASHEET_COLUMNS + ' FROM datasheet_sources'))
            devices = device_rows(conn.execute('SELECT ' + DEVICE_COLUMNS + ' FROM catalog_devices'), sources)
            rows = conn.execute('SELECT ' + SELECTIVITY_COLUMNS + ' FROM selectivity_rules').fetchall()
            _, enabled = selectivity_rows(rows, devices)
            return enabled

    @property
    def selectivity_rules(self) -> List[SelectivityRuleRecord]:
        return self._cached("_rules_cache", self.load_selectivity_rules)

    @property
    def trip_curves(self) -> Dict[str, dict]:
        def load():
            with closing(self._connect()) as conn:
                rows = conn.execute('SELECT ' + TRIP_CURVE_COLUMNS + ' FROM trip_curves').fetchall()
                return curve_rows(rows)
        return self._cached("_curves_cache", load)

    @property
    def standards(self) -> Dict[str, Dict[str, Any]]:
        def load():
            with closing(self._connect()) as conn:
                rows = conn.execute("SELECT standard_id, raw_json FROM standards_registry").fetchall()
                return registry_rows(rows)
        return self._cached("_standards_cache", load)

    # ------------------------------------------------------------------
    # ۷. API سازگار با سایر ماژول‌ها (static)
    # ------------------------------------------------------------------
    @staticmethod
    def get_default_catalog() -> List[CatalogDevice]:
        return list(catalog_repo.devices)

    @staticmethod
    def get_selectivity_rules() -> List[SelectivityRuleRecord]:
        return list(catalog_repo.selectivity_rules)


# نمونه سراسری (Singleton) برای استفاده موتور و خروجی‌ها
catalog_repo = CatalogRepository()


class TripCurveRepository:
    """پارامترهای منحنی تریپ تیپیکال از دیتابیس (داده تقریبی سازنده، نه مدرک هماهنگی الزام‌آور).

    سری‌هایی که نقاط رسمی دیتاشیت دارند (curve_source=DATASHEET_POINTS) از
    درونیابی لگاریتمی نقاط t-I استفاده می‌کنند؛ بقیه سری‌ها با مدل پارامتری
    k / I^alpha تخمین زده می‌شوند. در هر دو حالت خروجی صرفاً تخمین مقدماتی است (F-003).
    """

    @staticmethod
    def get_curve(series: str) -> dict:
        curves = catalog_repo.trip_curves
        if not isinstance(curves, dict):
            validated_curves(curves)
        require_exportable_text(series)
        if not isinstance(series, str) or not series.strip():
            raise CatalogValidationError(tr("audit_curve_invalid", name="?", field="series"))
        if series not in curves:
            return {}
        return validated_curve(series, curves[series], CatalogValidationError)

    @classmethod
    def datasheet_points(cls, series: str) -> Optional[List[tuple]]:
        c = cls.get_curve(series)
        pts = c.get("points")
        if not pts or len(pts) < 2:
            return None
        return sorted((float(m), float(t)) for m, t in pts)

    @classmethod
    def is_datasheet_points(cls, series: str) -> bool:
        return cls.get_curve(series).get("curve_source") == "DATASHEET_POINTS"

    @classmethod
    def datasheet_ref(cls, series: str) -> str:
        return str(cls.get_curve(series).get("datasheet_ref") or "")

    @staticmethod
    def _interp_log(pts: List[tuple], current_mult: float) -> float:
        if current_mult <= pts[0][0]:
            return pts[0][1]
        for (m1, t1), (m2, t2) in zip(pts, pts[1:]):
            if m1 <= current_mult <= m2:
                if m1 <= 0.0 or m2 <= 0.0 or t1 <= 0.0 or t2 <= 0.0:
                    return t1
                frac = math.log(current_mult / m1) / math.log(m2 / m1)
                t = 10.0 ** (math.log10(t1) + frac * (math.log10(t2) - math.log10(t1)))
                return min(1000.0, max(0.01, t))
        return pts[-1][1]

    @classmethod
    def thermal_time_s(cls, series: str, current_mult: float) -> Optional[float]:
        positive_curve_argument(series, current_mult, "current_mult", CatalogValidationError)
        c = cls.get_curve(series)
        if not c:
            return None
        pts = cls.datasheet_points(series)
        if pts:
            return cls._interp_log(pts, current_mult)
        try:
            time_s = c["thermal_k"] / current_mult ** c["alpha"]
        except (OverflowError, ZeroDivisionError) as error:
            raise CatalogValidationError(tr("audit_curve_invalid", name=series, field="thermal_time_s")) from error
        positive_curve_argument(series, time_s, "thermal_time_s", CatalogValidationError)
        return min(1000.0, max(0.01, time_s))

    @classmethod
    def instantaneous_band_a(cls, series: str, rated_in_a: float):
        positive_curve_argument(series, rated_in_a, "rated_in_a", CatalogValidationError)
        c = cls.get_curve(series)
        if not c:
            return (None, None)
        low, high = c["im_min_mult"] * rated_in_a, c["im_max_mult"] * rated_in_a
        positive_curve_argument(series, low, "instantaneous_min_a", CatalogValidationError)
        positive_curve_argument(series, high, "instantaneous_max_a", CatalogValidationError)
        return (low, high)

    @classmethod
    def current_selectivity_limit_ka(cls, upstream: CatalogDevice, downstream: CatalogDevice) -> Optional[float]:
        up_min_a, _ = cls.instantaneous_band_a(upstream.series, upstream.rated_current_in_a)
        _, down_max_a = cls.instantaneous_band_a(downstream.series, downstream.rated_current_in_a)
        if up_min_a is None or down_max_a is None:
            return None
        if down_max_a >= up_min_a:
            return 0.0
        return round(up_min_a / 1000.0, 1)


class StandardsRegistry:
    @staticmethod
    def _entries() -> Dict[str, Dict[str, Any]]:
        return registry_entries(catalog_repo.standards)

    @classmethod
    def title(cls, standard_id: str) -> str:
        registry_identifier(standard_id)
        entry = cls._entries().get(standard_id)
        if not entry:
            return standard_id
        titles = entry.get("title", {})
        return titles.get(i18n.get_language()) or titles.get("en") or standard_id

    @classmethod
    def scope(cls, standard_id: str) -> str:
        registry_identifier(standard_id)
        entry = cls._entries().get(standard_id)
        if not entry:
            return ""
        scopes = entry.get("scope", {})
        return scopes.get(i18n.get_language()) or scopes.get("en") or ""


class SiemensSelectivityRepository:
    """ارزیابی سلکتیویته با تفکیک قواعد تأییدشده سازنده از تخمین منحنی تقریبی (رفع F-003)."""

    @classmethod
    def get_selectivity_rules(cls) -> List[SelectivityRuleRecord]:
        return CatalogRepository.get_selectivity_rules()

    @classmethod
    def evaluate_pair(cls, upstream: CatalogDevice, downstream: CatalogDevice,
                      prospective_ik_ka: float | None, operating_voltage_v: float | None = None,
                      upstream_setting_a: float | None = None,
                      downstream_setting_a: float | None = None, *,
                      frequency_hz: float | None = None, ambient_temp_c: float | None = None):
        for name, value in (("Ik", prospective_ik_ka), ("voltage", operating_voltage_v),
                            ("upstream setting", upstream_setting_a), ("downstream setting", downstream_setting_a),
                            ("frequency", frequency_hz), ("ambient temperature", ambient_temp_c)):
            if value is not None and (not math.isfinite(value) or (name != "ambient temperature" and value <= 0)):
                raise CatalogValidationError(f"Invalid selectivity {name}")
        ratio = upstream.rated_current_in_a / max(1.0, downstream.rated_current_in_a)

        matching_rules = [
            r for r in validated_rules(cls.get_selectivity_rules())
            if r.upstream_part_number == upstream.part_number
            and r.downstream_part_number == downstream.part_number
            and operating_voltage_v is not None and r.operating_voltage_v == operating_voltage_v
            and upstream_setting_a is not None and r.upstream_setting_a == upstream_setting_a
            and downstream_setting_a is not None and r.downstream_setting_a == downstream_setting_a
            and r.source is not None and r.source.matches(r.selectivity_limit_is_ka, "kA", {
                "upstream_part_number": upstream.part_number, "downstream_part_number": downstream.part_number,
                "upstream_manufacturer": upstream.manufacturer, "downstream_manufacturer": downstream.manufacturer,
                "voltage_v": operating_voltage_v, "upstream_setting_a": upstream_setting_a,
                "downstream_setting_a": downstream_setting_a, "frequency_hz": frequency_hz,
                "ambient_temp_c": ambient_temp_c,
            })
        ]

        if matching_rules and prospective_ik_ka is not None:
            if len(matching_rules) != 1:
                raise CatalogValidationError("Ambiguous reviewed selectivity rules; reconcile the evidence before use")
            best_rule = matching_rules[0]
            proof = best_rule.source
            if proof is None:
                raise CatalogValidationError("Matched rule lost its property evidence")
            reference = (f"{proof.source_document} | {proof.revision} | {proof.page_or_table}"
                         f" | {proof.verified_by} | {proof.verified_at}")
            if best_rule.selectivity_limit_is_ka >= prospective_ik_ka:
                return (SelectivityEvalState.VERIFIED_TOTAL, best_rule.selectivity_limit_is_ka, reference)
            else:
                return (SelectivityEvalState.VERIFIED_PARTIAL, best_rule.selectivity_limit_is_ka, reference)

        if ratio >= 1.6:
            curve_limit_ka = TripCurveRepository.current_selectivity_limit_ka(upstream, downstream)
            if curve_limit_ka is not None and curve_limit_ka > 0.0:
                # منحنی تقریبی هرگز VERIFIED صادر نمی‌کند؛ صرفاً تخمین مقدماتی (رفع F-003)
                return (SelectivityEvalState.PRELIMINARY, curve_limit_ka, tr("sel_ref_curve_prelim", a=curve_limit_ka))
            return (SelectivityEvalState.PRELIMINARY_RATIO_ONLY, None, tr("sel_ref_ratio_only", ratio=f"{ratio:.2f}"))

        return (SelectivityEvalState.PRELIMINARY_RATIO_ONLY, None, tr("sel_ref_ratio_only", ratio=f"{ratio:.2f}"))
