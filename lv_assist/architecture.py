"""Functional block overview, without fabrication dimensions or device placement."""

from html import escape
from textwrap import wrap

from lv_assist.functional_connections import FunctionalConnections
from lv_assist.i18n import tr
from lv_assist.output_notice import annotate_svg
from lv_assist.svg_typography import readable_labels


class ArchitectureOverview:
    @staticmethod
    def generate_svg(project, feeders, summary):
        connections = FunctionalConnections.build(project, feeders, summary)
        panel_rows = [row for row in connections if row.scope_type == 'PANEL']
        groups = []

        def chain(title, links):
            if not links:
                return
            nodes = [(links[0].source, links[0].source_parts)]
            nodes.extend((row.target, row.target_parts) for row in links)
            groups.append((title, nodes))

        panel_power = [row for row in panel_rows if row.kind == 'POWER']
        chain(tr('arch_main_power'), panel_power[:2])
        chain(tr('arch_control'), panel_power[2:] + [row for row in panel_rows if row.kind == 'CONTROL'])
        for row in panel_rows:
            if row.kind == 'PROTECTION':
                chain(tr('arch_protection'), [row])
        for feeder in feeders:
            chain(feeder.feeder_id + ' — ' + feeder.description,
                  [row for row in connections if row.scope_type == 'FEEDER'
                   and row.scope == feeder.feeder_id and row.kind == 'POWER'])

        width, y = 1200, 140
        parts = []
        for title, nodes in groups:
            title_lines = wrap(title, width=105) or ['']
            for line in title_lines:
                parts.append(f'<text x="30" y="{y}" font-size="16" fill="#1F4E78">{escape(line)}</text>')
                y += 20
            card_width = (width - 60 - 24 * (len(nodes) - 1)) / len(nodes)
            labels = []
            for label, numbers in nodes:
                texts = [(line, True) for line in (wrap(label, width=max(15, int(card_width / 8))) or [''])]
                for number in numbers:
                    texts.extend((line, False) for line in wrap(number, width=max(15, int(card_width / 8))))
                if not numbers:
                    texts.extend((line, False) for line in wrap(tr('fc_not_specified'), width=max(15, int(card_width / 8))))
                labels.append(texts)
            height = max(90, max(len(lines) for lines in labels) * 18 + 24)
            for index, lines in enumerate(labels):
                x = 30 + index * (card_width + 24)
                parts.append(f'<rect x="{x:.1f}" y="{y}" width="{card_width:.1f}" height="{height}" rx="8" fill="#F1F5F9" stroke="#1F4E78"/>')
                for line_index, (line, heading) in enumerate(lines):
                    parts.append(f'<text x="{x + card_width / 2:.1f}" y="{y + 24 + line_index * 18}" text-anchor="middle" font-size="12" fill="{"#1F4E78" if heading else "#566573"}">{escape(line)}</text>')
                if index:
                    parts.append(f'<path d="M {x - 22:.1f} {y + height / 2:.1f} H {x - 3:.1f}" stroke="#117A65" stroke-width="2" marker-end="url(#architecture-arrow)"/>')
            y += height + 38

        notes = wrap(tr('arch_note'), width=135)
        for line in notes:
            parts.append(f'<text x="30" y="{y}" font-size="12" fill="#566573">{escape(line)}</text>')
            y += 18
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{y + 30}" viewBox="0 0 1200 {y + 30}" font-family="Tahoma, DejaVu Sans, sans-serif">'
               '<defs><marker id="architecture-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="#117A65"/></marker></defs>'
               f'<rect width="1200" height="{y + 30}" fill="white"/>'
               f'<text x="30" y="35" font-size="22" fill="#1F4E78">{escape(tr("arch_title"))}</text>'
               f'<text x="30" y="65" font-size="15">{escape(project.project_name)} | {escape(project.panel_tag)}</text>'
               f'<text x="30" y="95" font-size="12" fill="#B7950B">{escape(tr("arch_not_layout"))}</text>'
               + ''.join(parts) + '</svg>')
        return annotate_svg(readable_labels(svg), summary, watermark=False)
