"""Shape Persian SVG labels consistently while preserving accessible source text."""

import re
from html import escape, unescape

import arabic_reshaper
from bidi.algorithm import get_display


def readable_labels(svg):
    reshaper = arabic_reshaper.ArabicReshaper(configuration={
        # SVG backends can draw detached dotted-circle combining marks. The
        # accessible label retains all marks; the visual form omits only harakat.
        'delete_harakat': True, 'support_ligatures': False})

    def label(match):
        opening, encoded, closing = match.groups()
        original = unescape(encoded)
        display = (get_display(reshaper.reshape(original), base_dir='L')
                   if re.search('[\u0600-\u06ff]', original) else original)
        attributes = (' aria-label="' + escape(original, quote=True)
                      + '" style="direction:ltr;unicode-bidi:bidi-override"')
        return opening[:-1] + attributes + '>' + escape(display) + closing

    # The input is our generated SVG: each text node contains escaped plain text.
    return re.sub(r'(<text\b[^>]*>)(.*?)(</text>)', label, svg, flags=re.DOTALL)
