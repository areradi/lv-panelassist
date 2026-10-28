"""Reject text that cannot be exchanged as XML 1.0 / UTF-8; never rewrite it."""

import re

from pydantic import BaseModel

from lv_assist.i18n import tr

INVALID_TEXT = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def require_exportable_text(value):
    pending = [value]
    visited = set()
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            invalid = INVALID_TEXT.search(item)
            if invalid:
                code = f'U+{ord(invalid.group()):04X}'
                # Keep diagnostic code points ASCII even when tr localizes digits.
                raise ValueError(tr('audit_text_invalid', code='__CODEPOINT__').replace('__CODEPOINT__', code))
        elif isinstance(item, (BaseModel, dict, list, tuple, set)):
            if id(item) in visited:
                continue
            visited.add(id(item))
            if isinstance(item, BaseModel):
                pending.append(item.__dict__)
            elif isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            else:
                pending.extend(item)
