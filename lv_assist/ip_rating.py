"""Compare the two IP dimensions independently; this is not assembly proof."""

import re


def ip_meets(actual: str, required: str) -> bool:
    actual_match = re.fullmatch(r"IP([0-6])([0-9])", actual)
    required_match = re.fullmatch(r"IP([0-6])([0-9])", required)
    if actual_match is None or required_match is None:
        return False
    return all(int(a) >= int(r) for a, r in zip(actual_match.groups(), required_match.groups()))
