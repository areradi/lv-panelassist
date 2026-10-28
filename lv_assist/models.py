# -*- coding: utf-8 -*-
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from lv_assist.result_contract import ValidationStatus
from lv_assist.core_verification import CheckResult, ShortCircuitProfile, TripTimeEstimate
from lv_assist.run_metadata import RunMetadata
from lv_assist.i18n import tr

class EarthingSystem(str, Enum):
    TN_S = "TN-S"
    TN_C_S = "TN-C-S"
    TT = "TT"
    IT = "IT"

class LoadType(str, Enum):
    MOTOR_DOL = "MOTOR_DOL"
    MOTOR_STAR_DELTA = "MOTOR_STAR_DELTA"
    MOTOR_SOFT_STARTER = "MOTOR_SOFT_STARTER"
    MOTOR_VFD = "MOTOR_VFD"
    SUB_FEEDER = "SUB_FEEDER"
    LIGHTING_SOCKET = "LIGHTING_SOCKET"
    HEATER_RESISTIVE = "HEATER_RESISTIVE"

class PanelType(str, Enum):
    MCC = "MCC"
    DISTRIBUTION = "DISTRIBUTION"
    CONTROL = "CONTROL"
    PUMP_STATION = "PUMP_STATION"

class SpecialScenario(str, Enum):
    NONE = "NONE"
    FIRE_PUMP = "FIRE_PUMP"
    ATS_MAINS_GEN = "ATS_MAINS_GEN"
    FIRE_PUMP_BYPASS = "FIRE_PUMP_BYPASS"
    ATS_MAINS_MAINS = "ATS_MAINS_MAINS"
    UPS_CRITICAL = "UPS_CRITICAL"
    EMERGENCY_LIGHTING = "EMERGENCY_LIGHTING"

class ConductorMaterial(str, Enum):
    CU = "CU"
    AL = "AL"

class InsulationType(str, Enum):
    PVC = "PVC"
    XLPE = "XLPE"

class InstallationMethod(str, Enum):
    C = "C"
    B1 = "B1"
    E = "E"
    F = "F"

class SelectivityEvalState(str, Enum):
    VERIFIED_TOTAL = "VERIFIED_TOTAL"
    VERIFIED_PARTIAL = "VERIFIED_PARTIAL"
    PRELIMINARY = "PRELIMINARY"
    PRELIMINARY_RATIO_ONLY = "PRELIMINARY_RATIO"
    VIOLATION = "VIOLATION"

class DataQuality(str, Enum):
    REAL_VERIFIED = "REAL_VERIFIED"
    ESTIMATED = "ESTIMATED"


class SourceType(str, Enum):
    USER = "USER"
    MANUFACTURER = "MANUFACTURER"
    STANDARD = "STANDARD"
    CALCULATED = "CALCULATED"
    ASSUMED = "ASSUMED"


class PropertySource(BaseModel):
    """Recorded provenance; a label alone never constitutes reviewed evidence."""

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)
    value: float | str | None = None
    unit: str
    source_type: SourceType
    source_document: str | None = None
    revision: str | None = None
    page_or_table: str | None = None
    verified_at: str | None = None
    verified_by: str | None = None
    applicability: dict[str, str] = Field(default_factory=dict)
    quality: DataQuality = DataQuality.ESTIMATED

    def has_reviewed_evidence(self) -> bool:
        return bool(self.quality == DataQuality.REAL_VERIFIED
                    and self.source_type in (SourceType.MANUFACTURER, SourceType.STANDARD)
                    and self.source_document and self.revision and self.page_or_table
                    and self.verified_at and self.verified_by and self.applicability)

    @model_validator(mode="after")
    def incomplete_source_is_estimated(self):
        if not self.has_reviewed_evidence():
            self.quality = DataQuality.ESTIMATED
        return self

class SpdClass(str, Enum):
    NONE = "NONE"
    T1 = "T1"
    T2 = "T2"
    T1_T2 = "T1_T2"

class ProjectSpec(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    project_name: str = Field(..., min_length=2)
    project_revision: int = Field(default=1, ge=1)
    panel_tag: str = Field(default="+MCC1", min_length=1)
    standard_ref: str = Field(default="IEC 61439-2 / IEC 60204-1")
    nominal_voltage_v: float = Field(default=400.0, gt=0)
    frequency_hz: float = Field(default=50.0, gt=0)
    earthing_system: EarthingSystem = Field(default=EarthingSystem.TN_S)
    panel_type: PanelType = Field(default=PanelType.MCC)
    special_scenario: SpecialScenario = Field(default=SpecialScenario.NONE)
    prospective_ik_ka: Optional[float] = Field(default=None, gt=0)
    transformer_kva: Optional[float] = Field(default=None, gt=0)
    transformer_uk_pct: float = Field(default=6.0, gt=0.0, le=20.0)
    ambient_temp_c: float = Field(default=40.0, ge=-20.0, le=60.0)
    max_internal_temp_c: float = Field(default=50.0, ge=35.0, le=70.0)
    altitude_m: float = Field(default=1000.0, ge=0.0, le=4000.0)
    target_ip: str = Field(default="IP54", pattern=r"^IP[0-6][0-9]$")
    internal_separation_form: str = Field(default="Form 2b")
    simultaneity_factor_ks: float = Field(default=0.85, gt=0.1, le=1.0)
    spare_factor: float = Field(default=0.20, ge=0.0, le=1.0)
    cable_grouping_factor_k2: float = Field(default=0.80, gt=0.3, le=1.0)
    plc_hmi_24vdc_power_w: float = Field(default=55.0, ge=0.0)
    simultaneous_motor_starts: int = Field(default=2, ge=1, le=10)
    preferred_manufacturer: str = Field(default="ANY", min_length=1)
    designer_name: Optional[str] = Field(default=None, min_length=1)
    spd_class: SpdClass = Field(default=SpdClass.T2)
    spd_connection_length_m: float = Field(default=0.5, ge=0.0, le=10.0)

class FeederInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    feeder_id: str = Field(..., min_length=1)
    func_tag: str = Field(default="=PWR")
    loc_tag: str = Field(default="+MCC1")
    description: str = Field(min_length=1)
    load_type: LoadType
    power_kw: float = Field(..., gt=0)
    phases: int = Field(default=3, ge=1, le=3)
    cos_phi: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    efficiency: Optional[float] = Field(default=None, gt=0.1, le=1.0)
    demand_factor_kd: float = Field(default=1.0, gt=0.0, le=1.0)
    cable_length_m: Optional[float] = Field(default=None, gt=0)
    cable_section_mm2: Optional[float] = Field(default=None, gt=0)
    has_socket_outlets: bool = Field(default=False)
    fire_pump_service: bool = Field(default=False)
    conductor_material: ConductorMaterial = ConductorMaterial.CU
    insulation: InsulationType = InsulationType.PVC
    installation_method: InstallationMethod = InstallationMethod.C
    fire_resistant: bool = Field(default=False)
    thdi_pct: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    protection_ir_a: float | None = Field(default=None, gt=0)
    protection_i2_a: float | None = Field(default=None, gt=0)

    @field_validator("phases")
    @classmethod
    def supported_phase_count(cls, value: int) -> int:
        if value not in (1, 3):
            raise ValueError("Only 1P and 3P loads are supported; 2P needs an explicit voltage model.")
        return value

class CatalogDevice(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    part_number: str
    manufacturer: str
    series: str
    device_type: str
    rated_current_in_a: float = 0.0
    boost_current_peak_a: float = 0.0
    setting_min_a: float = 0.0
    setting_max_a: float = 0.0
    motor_kw_400v: float = 0.0
    icu_ka_400v: float = 0.0
    power_loss_w: float = 0.0
    coil_holding_24v_w: float = 0.0
    coil_pull_in_24v_w: float = 0.0
    derating_40c: float = 1.0
    derating_50c: float = 1.0
    cap_kvar_400v: float = 0.0
    detuned_pct: float = 0.0
    tuned_hz: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0
    depth_mm: float = 0.0
    airflow_m3h: float = 0.0
    ip_rating: str = "IP20"
    data_quality: DataQuality = DataQuality.ESTIMATED
    spd_class: Optional[str] = None
    spd_uc_v: float = 0.0
    spd_up_kv: float = 0.0
    spd_in_ka: float = 0.0
    spd_imax_ka: float = 0.0
    spd_iimp_ka: float = 0.0
    spd_poles: str = "4P"
    spd_backup_fuse_a: float = 0.0
    property_sources: dict[str, PropertySource] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unsupported_quality_is_estimated(self):
        # Whole-device quality cannot be inferred from one reviewed property.
        critical = {"power_loss_w", "dimensions", "thermal", "ip"}
        if self.device_type in ("MCB", "MCCB", "MPCB"):
            critical |= {"icu_ka", "trip_curve"}
        if not critical <= self.property_sources.keys() or not all(
                source.has_reviewed_evidence() for source in self.property_sources.values()):
            self.data_quality = DataQuality.ESTIMATED
        return self

class SelectivityRuleRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    upstream_series: str
    upstream_min_in_a: float
    downstream_series: str
    downstream_max_in_a: float
    selectivity_limit_is_ka: float
    is_total_up_to_icu: bool = False
    catalog_reference: str
    upstream_part_number: str | None = None
    downstream_part_number: str | None = None
    operating_voltage_v: float | None = None
    upstream_setting_a: float | None = None
    downstream_setting_a: float | None = None
    source: PropertySource | None = None

class ValidationResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    rule_id: str
    feeder_id: str
    standard_ref: str
    status: ValidationStatus
    description: str
    supporting_evidence: str
    consequence: str
    recommended_action: str
    check_id: str = ""
    scope: str = "CHECK"
    subject_id: str = ""
    input_values: dict = Field(default_factory=dict)
    result_value: float | None = None
    unit: str | None = None
    limit: float | None = None
    method: str = "LEGACY_UNDOCUMENTED"
    source_ref: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    reason: str = ""

    @model_validator(mode="after")
    def preserve_legacy_identity(self):
        self.check_id = self.check_id or self.rule_id
        self.subject_id = self.subject_id or self.feeder_id
        self.reason = self.reason or self.description
        if self.scope == "CHECK":
            self.scope = self.feeder_id if self.feeder_id in ("PANEL", "NETWORK") else "FEEDER"
        if (self.status == ValidationStatus.COMPLETED
                and self.method == "LEGACY_UNDOCUMENTED" and self.source_ref is None):
            self.status = ValidationStatus.WARNING
            note = "Legacy calculation; no reviewed source metadata recorded."
            if note not in self.assumptions:
                self.assumptions.append(note)
            self.recommended_action = tr("audit_source_gap")
        return self

    @classmethod
    def from_check(cls, check, *, rule_id: str, subject_id: str, standard_ref: str):
        return cls(
            rule_id=rule_id, feeder_id=subject_id, standard_ref=standard_ref,
            status=check.status, description=check.title,
            supporting_evidence=check.measured_or_calc_value or check.cause or "-",
            consequence=check.effect, recommended_action=check.recommended_action,
            check_id=check.check_id, scope=check.scope, subject_id=subject_id,
            input_values=check.input_values, result_value=check.result_value,
            unit=check.unit, limit=check.limit, method=check.method,
            source_ref=check.source_ref, assumptions=check.assumptions,
            reason=check.reason,
        )

class ControlWire(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    wire_no: str
    from_dev: str
    from_term: str
    to_dev: str
    to_term: str
    color: str = "BU"
    cross_section_mm2: float = 1.5
    remark: str = ""

class LayoutDevice(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    tag: str
    part_number: str
    zone: str
    width_mm: float
    height_mm: float
    depth_mm: float = 0.0
    loss_w: float = 0.0
    clearance_mm: float = 0.0

class LayoutRow(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    row_no: int
    zone: str
    y_mm: float
    used_width_mm: float
    devices: List[LayoutDevice]

class PanelLayoutResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    panel_width_mm: float
    panel_height_mm: float
    panel_depth_mm: float
    usable_width_mm: float
    rows: List[LayoutRow]
    fill_factor_pct: float
    total_loss_w: float
    natural_dissipation_w: float
    spare_space_pct: float = 20.0
    form_partition_factor: float = 1.0
    validations: List[ValidationResult]

class BusbarResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    spec: str
    rating_a: float
    cross_section_mm2: float
    icw_1s_ka: float
    ipk_ka: float
    required_ipk_ka: Optional[float] = None
    max_support_spacing_mm: Optional[float] = None
    required_supports: int = 2
    r_mohm_m: float = 0.0
    x_mohm_m: float = 0.0
    length_m: float = 0.0
    voltage_drop_v: float = 0.0
    voltage_drop_pct: float = 0.0
    validations: List[ValidationResult] = []

class FeederCalcOutput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    feeder_id: str
    func_tag: str
    loc_tag: str
    description: str
    load_type: LoadType
    power_kw: float
    active_power_demand_kw: float
    reactive_power_demand_kvar: float
    design_current_ib_a: float
    delta_loop_current_a: Optional[float] = None
    star_current_a: Optional[float] = None
    required_in_after_derating_a: float
    cable_length_m: float | None = None
    selected_phase_mm2: float = 2.5
    selected_pe_mm2: float | None = None
    cable_derated_iz_a: Optional[float] = 0.0
    cable_Auto_sized: bool = True
    cable_designation_str: str = ""
    cable_temp_factor_k1: float = 1.0
    cable_grouping_factor_k2: float = 1.0
    cable_total_derating_k: float = 1.0
    cable_method_ref_str: str = ""
    pe_basis_str: str = ""
    protection_icu_ka: Optional[float] = None
    voltage_drop_percent: float | None = None
    status: ValidationStatus = ValidationStatus.INSUFFICIENT_DATA
    selection_status: str = "PROPOSED"
    short_circuit_profile: ShortCircuitProfile | None = None
    trip_time_estimate: TripTimeEstimate | None = None
    pe_check: CheckResult | None = None
    run_metadata: RunMetadata | None = None
    assumptions_used: List[str] = []
    selected_protection: Optional[CatalogDevice] = None
    selected_contactor_main: Optional[CatalogDevice] = None
    selected_contactor_delta: Optional[CatalogDevice] = None
    selected_contactor_star: Optional[CatalogDevice] = None
    selected_bimetal: Optional[CatalogDevice] = None
    selected_timer_yd: Optional[CatalogDevice] = None
    selected_vfd: Optional[CatalogDevice] = None
    selected_soft_starter: Optional[CatalogDevice] = None
    selected_rcd: Optional[CatalogDevice] = None
    ctrl_24v_holding_w: float = 0.0
    ctrl_24v_pull_in_surge_w: float = 0.0
    selectivity_state: SelectivityEvalState = SelectivityEvalState.PRELIMINARY_RATIO_ONLY
    selectivity_limit_is_ka: Optional[float] = None
    selectivity_ref_doc: str = "-"
    total_feeder_loss_w: float = 0.0
    selection_reason: str = ""
    suggested_spec_str: str = ""
    starting_kva: float = 0.0
    starting_dip_pct: Optional[float] = None
    fire_pump_service: bool = False
    thdi_pct: Optional[float] = None
    fire_resistant: bool = False

class PanelSummaryOutput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    total_active_kw: float
    total_reactive_kvar: float
    total_apparent_kva: float
    overall_cos_phi: float
    sum_feeder_currents_a: float
    design_main_current_a: float
    main_breaker: Optional[CatalogDevice] = None
    recommended_busbar_spec: str
    recommended_pe_busbar_spec: str
    busbar_rating_a: float = 0.0
    busbar_icw_1s_ka: float = 0.0
    busbar_ipk_ka: float = 0.0
    busbar_required_ipk_ka: Optional[float] = None
    busbar_max_support_spacing_mm: Optional[float] = None
    busbar_required_supports: int = 2
    recommended_incoming_cable_str: str
    ctrl_24v_plc_hmi_w: float = 0.0
    ctrl_24v_coils_holding_w: float = 0.0
    ctrl_24v_total_continuous_w: float = 0.0
    ctrl_24v_continuous_current_a: float = 0.0
    ctrl_24v_design_current_with_spare_a: float = 0.0
    ctrl_24v_peak_inrush_current_a: float = 0.0
    selected_psu_24v: Optional[CatalogDevice] = None
    selected_dc_selectivity_mod: Optional[CatalogDevice] = None
    selected_psu_primary_mcb: Optional[CatalogDevice] = None
    total_power_loss_w: float
    enclosure_natural_dissipation_w: float
    required_airflow_m3h: float
    selected_fan: Optional[CatalogDevice] = None
    selected_enclosure: Optional[CatalogDevice] = None
    estimated_panel_width_mm: float
    estimated_panel_height_mm: float
    estimated_panel_depth_mm: float
    ik_used_ka: Optional[float] = None
    motor_contribution_ka: Optional[float] = None
    ik_bus_total_ka: Optional[float] = None
    ip_bus_total_ka: Optional[float] = None
    busbar_du_v: float = 0.0
    busbar_du_pct: float = 0.0
    max_total_du_pct: float | None = None
    ik_source_str: str = ""
    effective_ip_str: str = ""
    suggested_main_breaker_str: str = ""
    suggested_psu_str: str = ""
    suggested_fan_str: str = ""
    max_motor_starting_dip_pct: Optional[float] = None
    max_starting_dip_motor: str = ""
    panel_thdi_pct: Optional[float] = None
    cap_bank_required_kvar: float = 0.0
    cap_bank_installed_kvar: float = 0.0
    cap_bank_steps: List[float] = []
    cap_bank_detuned_pct: float = 0.0
    cap_bank_reactor_tuned_hz: float = 0.0
    cap_bank_contactor: Optional[CatalogDevice] = None
    cap_bank_protection: Optional[CatalogDevice] = None
    cap_bank_reactor_dev: Optional[CatalogDevice] = None
    cap_bank_module_dev: Optional[CatalogDevice] = None
    cap_bank_resonance_order: Optional[float] = None
    cap_bank_suggested_str: str = ""
    selected_spd: Optional[CatalogDevice] = None
    spd_suggested_str: str = ""
    estimated_internal_temp_c: Optional[float] = None
    altitude_derating_factor: float = 1.0
    status: ValidationStatus = ValidationStatus.INSUFFICIENT_DATA
    run_metadata: RunMetadata | None = None

class VerificationMethod(str, Enum):
    CALCULATION = "CALCULATION"
    DESIGN_RULE = "DESIGN_RULE"
    MANUFACTURER_DATA = "MANUFACTURER_DATA"
    TYPE_TEST = "TYPE_TEST"

class VerificationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_VERIFIED = "NOT_VERIFIED"

class DesignVerificationItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    clause_ref: str
    title: str
    requirement: str
    method: VerificationMethod
    status: VerificationStatus
    computed_value: str
    evidence: str
    rule_ids: List[str] = []
    evidence_document: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    source_ref: str = "IEC 61439-1 Clause 10 — applicability/revision requires review"

class DesignVerificationReport(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    standard_ref: str = "IEC 61439-1"
    clause_ref: str = "Clause 10"
    items: List[DesignVerificationItem]
    conclusion_status: VerificationStatus
    conclusion_text: str
    generated_by: str = "LV-PanelAssist"
