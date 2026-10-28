"""Compare the two IP dimensions independently; this is not assembly proof."""

import re


def ip_upper_bound(*ratings: str) -> str | None:
    """Component-wise ceiling only; no installed assembly rating is inferred."""
    matches = [re.fullmatch(r"IP([0-6])([0-9])", rating) for rating in ratings]
    if not matches or any(match is None for match in matches):
        return None
    dimensions = [match.groups() for match in matches if match is not None]
    # Immersion/high-pressure categories are not an ordinal substitute for
    # jet protection. Their combined applicability is outside this proposal.
    if any(int(pair[1]) > 6 for pair in dimensions):
        return None
    return "IP" + "".join(str(min(int(pair[index]) for pair in dimensions)) for index in (0, 1))


def ip_meets(actual: str, required: str) -> bool:
    actual_match = re.fullmatch(r"IP([0-6])([0-9])", actual)
    required_match = re.fullmatch(r"IP([0-6])([0-9])", required)
    if actual_match is None or required_match is None:
        return False
    return all(int(a) >= int(r) for a, r in zip(actual_match.groups(), required_match.groups()))
