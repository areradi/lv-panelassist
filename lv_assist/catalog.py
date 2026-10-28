# -*- coding: utf-8 -*-
"""
مدیریت کاتالوگ تجهیزات، قواعد سلکتیویته، منحنی‌های قطع و جداول استاندارد مبتنی بر SQLite.
رفع یافته‌های ممیزی: F-001, F-003, F-005, F-006, F-007, F-008, F-016, F-017.
منبع حقیقت: lv_assist/data/lv_assist.db که توسط migrate_to_sqlite.py از فایل‌های JSON ساخته می‌شود.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from lv_assist.ip_rating import ip_meets
from lv_assist.run_metadata import catalog_file_hash
from lv_assist.catalog_validation import CatalogValidationError, catalog_object, device_rows, validated_rules
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
        self._devices_file_hash: str | None = None
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
        with self._connect() as conn:
            rows = conn.execute("SELECT device_id, raw_json, data_quality FROM catalog_devices").fetchall()
            return device_rows(rows)

    @property
    def devices(self) -> List[CatalogDevice]:
        current_hash = catalog_file_hash(self.db_path)
        if self._devices_cache is None or self._devices_file_hash != current_hash:
            self._devices_cache = self.load_devices()
            self._devices_file_hash = current_hash
            self._rules_cache = self._curves_cache = self._standards_cache = None
            self._iz0_cache = self._pe_cache = None
        return self._devices_cache

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
        if tolerance_v != 0:
            raise ValueError("Nearby-voltage Icu lookup requires explicit manufacturer applicability; unsupported.")
        if not math.isfinite(nominal_voltage_v) or nominal_voltage_v <= 0:
            raise CatalogValidationError("Operating voltage must be finite and positive")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT icu_ka FROM device_breaking_capacities
                WHERE device_id = ? AND voltage_v = ?
                LIMIT 1
                """,
                (device_id, nominal_voltage_v),
            ).fetchone()
            if row is None or row["icu_ka"] is None:
                return None
            value = float(row["icu_ka"])
            if not math.isfinite(value) or value < 0:
                raise CatalogValidationError("Icu catalog value must be finite and non-negative")
            return value if value > 0 else None

    # ------------------------------------------------------------------
    # ۳. ضریب کاهش ظرفیت دمایی با کنترل سقف دما (رفع F-017)
    # ------------------------------------------------------------------
    def get_device_derating_factor(self, device_id: str, internal_temp_c: float) -> Optional[float]:
        """ضریب derating از جدول دما؛ برای دماهای بالای ۵۰ درجه بدون داده معتبر، None برمی‌گردد."""
        if internal_temp_c <= 40.0:
            target_temp = 40.0
        elif internal_temp_c <= 50.0:
            target_temp = 50.0
        else:
            target_temp = internal_temp_c

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT derating_factor FROM device_thermal_derating
                WHERE device_id = ? AND temp_c >= ?
                ORDER BY temp_c ASC
                LIMIT 1
                """,
                (device_id, target_temp),
            ).fetchone()
            return float(row["derating_factor"]) if row else None

    # ------------------------------------------------------------------
    # ۴. بدنه تابلو با شرط IP هدف (رفع F-007)
    # ------------------------------------------------------------------
    def get_compatible_enclosures(self, target_ip: Optional[str] = None) -> List[CatalogDevice]:
        """بدنه‌هایی که درجه حفاظت IP هدف پروژه را تأمین می‌کنند."""
        enclosures = [d for d in self.devices if d.device_type == "ENCLOSURE"]
        if not target_ip:
            return enclosures

        return [enc for enc in enclosures if ip_meets(enc.ip_rating, target_ip)]

    # ------------------------------------------------------------------
    # ۵. جداول مرجع کابل و مقاطع استاندارد PE (رفع F-001, F-005, F-008)
    # ------------------------------------------------------------------
    def get_cable_iz0_table_cu_pvc_c(self, loaded_conductors: int = 3) -> Dict[float, float]:
        """جدول کامل جریان‌دهی پایه Cu/PVC/روش C از دیتابیس استاندارد."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT section_mm2, iz0_a FROM cable_ampacity_reference
                WHERE material = 'CU' AND insulation = 'PVC' AND installation_method = 'C'
                  AND loaded_conductors = ?
                """,
                (loaded_conductors,),
            ).fetchall()
            return {float(r["section_mm2"]): float(r["iz0_a"]) for r in rows}

    def get_base_cable_iz0(
        self,
        section_mm2: float,
        material: str = "CU",
        insulation: str = "PVC",
        installation_method: str = "C",
        loaded_conductors: int = 3,
    ) -> Optional[float]:
        """جریان‌دهی پایه یک مقطع خاص؛ برای مقطع غیراستاندارد None برمی‌گردد (هرگز مقدار ساختگی)."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT iz0_a FROM cable_ampacity_reference
                WHERE section_mm2 = ?
                  AND UPPER(material) = UPPER(?)
                  AND UPPER(insulation) = UPPER(?)
                  AND UPPER(installation_method) = UPPER(?)
                  AND loaded_conductors = ?
                """,
                (section_mm2, material, insulation, installation_method, loaded_conductors),
            ).fetchone()
            if row:
                return float(row["iz0_a"])
            return None

    def get_cable_iz0_table(self, material: str, insulation: str,
                            installation_method: str, loaded_conductors: int) -> dict[float, float]:
        """Exact combination only. An absent table is not a scaled Cu/PVC/C table."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT section_mm2, iz0_a FROM cable_ampacity_reference "
                "WHERE material=? AND insulation=? AND installation_method=? AND loaded_conductors=?",
                (material.upper(), insulation.upper(), installation_method.upper(), loaded_conductors),
            ).fetchall()
        return {float(row[0]): float(row[1]) for row in rows}

    def get_pe_standard_sections(self) -> List[float]:
        """فهرست مقاطع استاندارد PE از دیتابیس (بدون سقف مصنوعی)."""
        if self._pe_cache is None:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT section_mm2 FROM pe_standard_sections ORDER BY section_mm2 ASC"
                ).fetchall()
                self._pe_cache = [float(r["section_mm2"]) for r in rows]
        return self._pe_cache

    def get_standard_pe_section(self, required_pe_mm2: float) -> Optional[float]:
        """اولین مقطع استاندارد PE بزرگ‌تر یا مساوی مقدار لازم؛ اگر فراتر از جدول باشد None."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT section_mm2 FROM pe_standard_sections
                WHERE section_mm2 >= ?
                ORDER BY section_mm2 ASC
                LIMIT 1
                """,
                (required_pe_mm2,),
            ).fetchone()
            return float(row["section_mm2"]) if row else None

    # ------------------------------------------------------------------
    # ۶. قواعد سلکتیویته، منحنی‌های قطع و رجیستری استانداردها
    # ------------------------------------------------------------------
    def load_selectivity_rules(self) -> List[SelectivityRuleRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT raw_json FROM selectivity_rules WHERE is_verified_manufacturer_rule = 1"
            ).fetchall()
            return validated_rules(SelectivityRuleRecord.model_validate(catalog_object(r["raw_json"])) for r in rows)

    @property
    def selectivity_rules(self) -> List[SelectivityRuleRecord]:
        if self._rules_cache is None:
            self._rules_cache = self.load_selectivity_rules()
        return self._rules_cache

    @property
    def trip_curves(self) -> Dict[str, dict]:
        if self._curves_cache is None:
            with self._connect() as conn:
                rows = conn.execute("SELECT curve_id, raw_json FROM trip_curves").fetchall()
                self._curves_cache = {r["curve_id"]: json.loads(r["raw_json"]) for r in rows}
        return self._curves_cache

    @property
    def standards(self) -> Dict[str, Dict[str, Any]]:
        if self._standards_cache is None:
            with self._connect() as conn:
                rows = conn.execute("SELECT standard_id, raw_json FROM standards_registry").fetchall()
                self._standards_cache = {r["standard_id"]: json.loads(r["raw_json"]) for r in rows}
        return self._standards_cache

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
        return curves.get(series, curves.get("DEFAULT", {}))

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
    def thermal_time_s(cls, series: str, current_mult: float) -> float:
        pts = cls.datasheet_points(series)
        if pts:
            return cls._interp_log(pts, current_mult)
        c = cls.get_curve(series)
        k, alpha = c.get("thermal_k", 90.0), c.get("alpha", 2.0)
        return min(1000.0, max(0.01, k / max(current_mult, 1e-3) ** alpha))

    @classmethod
    def instantaneous_band_a(cls, series: str, rated_in_a: float):
        c = cls.get_curve(series)
        return (c.get("im_min_mult", 8.0) * rated_in_a, c.get("im_max_mult", 12.0) * rated_in_a)

    @classmethod
    def current_selectivity_limit_ka(cls, upstream: CatalogDevice, downstream: CatalogDevice) -> float:
        up_min_a, _ = cls.instantaneous_band_a(upstream.series, upstream.rated_current_in_a)
        _, down_max_a = cls.instantaneous_band_a(downstream.series, downstream.rated_current_in_a)
        if down_max_a >= up_min_a:
            return 0.0
        return round(up_min_a / 1000.0, 1)


class StandardsRegistry:
    @staticmethod
    def _entries() -> Dict[str, Dict[str, Any]]:
        with catalog_repo._connect() as conn:
            rows = conn.execute("SELECT standard_id, raw_json FROM standards_registry").fetchall()
        entries: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            payload = json.loads(r["raw_json"])
            if isinstance(payload, dict) and "title" in payload:
                entries[r["standard_id"]] = payload
            elif isinstance(payload, dict):
                for std_id, entry in payload.items():
                    if isinstance(entry, dict) and "title" in entry:
                        entries[std_id] = entry
        return entries

    @classmethod
    def title(cls, standard_id: str) -> str:
        entry = cls._entries().get(standard_id)
        if not entry:
            return standard_id
        titles = entry.get("title", {})
        return titles.get(i18n.get_language()) or titles.get("en") or standard_id

    @classmethod
    def scope(cls, standard_id: str) -> str:
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
                      downstream_setting_a: float | None = None):
        ratio = upstream.rated_current_in_a / max(1.0, downstream.rated_current_in_a)

        matching_rules = [
            r for r in validated_rules(cls.get_selectivity_rules())
            if r.upstream_part_number == upstream.part_number
            and r.downstream_part_number == downstream.part_number
            and operating_voltage_v is not None and r.operating_voltage_v == operating_voltage_v
            and upstream_setting_a is not None and r.upstream_setting_a == upstream_setting_a
            and downstream_setting_a is not None and r.downstream_setting_a == downstream_setting_a
            and r.source is not None and r.source.has_reviewed_evidence()
            and r.source.value == r.selectivity_limit_is_ka and r.source.unit == "kA"
        ]

        if matching_rules and prospective_ik_ka is not None:
            best_rule = max(matching_rules, key=lambda x: x.selectivity_limit_is_ka)
            if best_rule.selectivity_limit_is_ka >= prospective_ik_ka:
                return (SelectivityEvalState.VERIFIED_TOTAL, best_rule.selectivity_limit_is_ka, best_rule.catalog_reference)
            else:
                return (SelectivityEvalState.VERIFIED_PARTIAL, best_rule.selectivity_limit_is_ka, best_rule.catalog_reference)

        if ratio >= 1.6:
            curve_limit_ka = TripCurveRepository.current_selectivity_limit_ka(upstream, downstream)
            if curve_limit_ka > 0.0:
                # منحنی تقریبی هرگز VERIFIED صادر نمی‌کند؛ صرفاً تخمین مقدماتی (رفع F-003)
                return (SelectivityEvalState.PRELIMINARY, curve_limit_ka, tr("sel_ref_curve_prelim", a=curve_limit_ka))
            return (SelectivityEvalState.PRELIMINARY_RATIO_ONLY, None, tr("sel_ref_ratio_only", ratio=f"{ratio:.2f}"))

        return (SelectivityEvalState.PRELIMINARY_RATIO_ONLY, None, tr("sel_ref_ratio_only", ratio=f"{ratio:.2f}"))
