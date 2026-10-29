"""Portable output notice tied to the accepted run; never assembly approval."""

from html import escape


def output_notice(summary):
    status = getattr(getattr(summary, 'status', None), 'value', 'INSUFFICIENT_DATA')
    metadata = getattr(summary, 'run_metadata', None)
    identity = metadata.input_fingerprint if metadata is not None else 'NOT_RECORDED'
    return f'PRELIMINARY - NOT FOR CONSTRUCTION | PROPOSED | STATUS={status} | RUN={identity}'


def annotate_svg(svg, summary):
    if 'id="lvassist-run-notice"' in svg:
        return svg
    notice = escape(output_notice(summary))
    metadata = getattr(summary, 'run_metadata', None)
    record = escape(metadata.model_dump_json() if metadata is not None else 'NOT_RECORDED')
    addition = (f'<metadata id="lvassist-run-notice">{notice}\n{record}</metadata>'
                f'<text x="50%" y="50%" text-anchor="middle" fill="#B7950B" '
                f'opacity="0.22" font-size="24">PRELIMINARY - NOT FOR CONSTRUCTION</text>'
                f'<text x="50%" y="54%" text-anchor="middle" fill="#566573" '
                f'opacity="0.6" font-size="12">STATUS={escape(getattr(getattr(summary, "status", None), "value", "INSUFFICIENT_DATA"))}</text>')
    return svg.replace('</svg>', addition + '</svg>', 1)
