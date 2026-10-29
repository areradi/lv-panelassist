"""Conceptual equipment relationships for handoff to detailed design tools."""

from dataclasses import dataclass
from html import escape

from lv_assist.csv_export import CsvMode, write_csv
from lv_assist.i18n import tr
from lv_assist.report_export import export_current_report


@dataclass(frozen=True)
class FunctionalConnection:
    scope: str
    kind: str
    source: str
    target: str
    purpose: str
    source_parts: tuple[str, ...] = ()
    target_parts: tuple[str, ...] = ()
    status: str = 'PROPOSED'
    scope_type: str = 'FEEDER'

    def cells(self):
        return (self.scope, tr('fc_kind_' + self.kind.lower()), self.source, self.target,
                self.purpose, '; '.join(self.source_parts) or tr('fc_not_specified'),
                '; '.join(self.target_parts) or tr('fc_not_specified'), self.status)


class FunctionalConnections:
    HEADER_KEYS = ('scope', 'kind', 'source', 'target', 'purpose', 'source_parts', 'target_parts', 'status')

    @classmethod
    def headers(cls):
        return tuple(tr('fc_h_' + key) for key in cls.HEADER_KEYS)

    @staticmethod
    def build(project, feeders, summary):
        def parts(*devices):
            return tuple(dict.fromkeys(device.part_number for device in devices if device is not None))

        def node(role, devices=(), scope=None):
            label = tr('fc_node_' + role)
            return (f'{label} ({scope})' if scope else label, devices)

        rows = []
        def link(scope, kind, source, target, purpose):
            rows.append(FunctionalConnection(project.panel_tag if scope is None else scope, kind,
                source[0], target[0], tr('fc_purpose_' + purpose), source[1], target[1],
                scope_type='PANEL' if scope is None else 'FEEDER'))

        supply = node('supply')
        main = node('main_protection', parts(summary.main_breaker))
        bus = node('bus')
        auxiliary = node('aux_protection', parts(summary.selected_psu_primary_mcb))
        psu = node('control_supply', parts(summary.selected_psu_24v))
        distribution = node('control_distribution', parts(summary.selected_dc_selectivity_mod))
        controller = node('controller')
        link(None, 'POWER', supply, main, 'incoming')
        link(None, 'POWER', main, bus, 'distribution')
        if summary.selected_spd is not None:
            link(None, 'PROTECTION', bus, node('spd', parts(summary.selected_spd)), 'surge')
        if summary.ctrl_24v_total_continuous_w > 0:
            link(None, 'POWER', bus, auxiliary, 'auxiliary')
            link(None, 'POWER', auxiliary, psu, 'auxiliary')
            link(None, 'CONTROL', psu, distribution, 'control_supply')
            link(None, 'CONTROL', distribution, controller, 'control_supply')
        for feeder in feeders:
            scope = feeder.feeder_id
            protection = node('feeder_protection', parts(feeder.selected_protection), scope)
            link(scope, 'POWER', bus, protection, 'feeder')
            load = node('motor' if feeder.load_type.value.startswith('MOTOR_') else 'load', scope=scope)
            if feeder.load_type.value.startswith('MOTOR_'):
                role = {'MOTOR_DOL': 'dol', 'MOTOR_STAR_DELTA': 'star_delta',
                        'MOTOR_SOFT_STARTER': 'soft_starter', 'MOTOR_VFD': 'vfd'}[feeder.load_type.value]
                starter = node(role, parts(feeder.selected_contactor_main, feeder.selected_contactor_star,
                    feeder.selected_contactor_delta, feeder.selected_bimetal, feeder.selected_timer_yd,
                    feeder.selected_soft_starter, feeder.selected_vfd), scope)
                link(scope, 'POWER', protection, starter, 'starter')
                link(scope, 'POWER', starter, load, 'motor')
                link(scope, 'CONTROL', controller, starter, 'command')
                link(scope, 'SIGNAL', starter, controller, 'feedback')
            elif feeder.selected_rcd is not None:
                residual = node('rcd', parts(feeder.selected_rcd), scope)
                link(scope, 'POWER', protection, residual, 'feeder')
                link(scope, 'POWER', residual, load, 'load')
            else:
                link(scope, 'POWER', protection, load, 'load')
        return tuple(rows)

    @classmethod
    def html_section(cls, project, feeders, summary):
        headings = ''.join('<th>' + escape(value) + '</th>' for value in cls.headers())
        rows = ''.join('<tr>' + ''.join('<td>' + escape(str(value)) + '</td>' for value in row.cells())
                       + '</tr>' for row in cls.build(project, feeders, summary))
        return ('<section id="functional-connections"><h2>' + escape(tr('fc_title')) + '</h2><p>'
                + escape(tr('fc_scope_note')) + '</p><table><thead><tr>' + headings
                + '</tr></thead><tbody>' + rows + '</tbody></table></section>')

    @classmethod
    def export_csv(cls, filename, project, feeders, summary, *, mode=CsvMode.MACHINE, validations=None):
        return export_current_report(filename, project, feeders, summary, validations,
            lambda path, p, f, s, checks: cls._render_csv(path, p, f, s, mode=mode))

    @classmethod
    def _render_csv(cls, filename, project, feeders, summary, *, mode):
        headers = (*cls.headers(), 'Overall check status', 'Run fingerprint', 'Design scope')
        rows = [(*row.cells(), summary.status.value, summary.run_metadata.input_fingerprint,
                 tr('fc_scope_note')) for row in cls.build(project, feeders, summary)]
        write_csv(filename, headers, rows, mode=mode)
