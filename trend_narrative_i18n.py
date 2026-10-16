"""Language fallback helpers for the external trend-narrative package."""

import numpy as np
from trend_narrative import get_relationship_narrative, get_segment_narrative
from trend_narrative.translations import get_translations

from translations import t
from utils import millify

# trend-narrative's single-segment sentence ends with this placeholder, then a
# closing clause that calls the trend steady ("maintaining a consistent trajectory").
_PERCENT_PLACEHOLDER = "({pct_change})"


def _is_unsupported_language_error(exc, attempted_lang):
    return (
        isinstance(exc, ValueError)
        and str(exc).startswith(f"Unsupported language '{attempted_lang}'.")
    )


def _call_with_language_fallback(func, lang, **kwargs):
    """Try the requested language, then English if it is unsupported."""
    if lang == "en":
        return func(**kwargs, lang=lang)

    try:
        return func(**kwargs, lang=lang)
    except Exception as exc:
        if not _is_unsupported_language_error(exc, lang):
            raise

        return func(**kwargs, lang="en")


def _library_translations(lang):
    try:
        return get_translations(lang)
    except ValueError as exc:
        if not _is_unsupported_language_error(exc, lang):
            raise
        return get_translations("en")


def _turning_point(extractor):
    """(year, value, is_peak) of the series' highest point, else its lowest, when it lies
    strictly inside the period of a series that changes direction; None otherwise."""
    y = np.asarray(extractor.y, dtype=float)
    if len(y) < 3:
        return None
    steps = np.diff(y)
    if (steps >= 0).all() or (steps <= 0).all():
        return None
    for index, is_peak in ((int(np.argmax(y)), True), (int(np.argmin(y)), False)):
        if 0 < index < len(y) - 1:
            return int(extractor.x[index]), float(y[index]), is_peak
    return None


def _name_turning_point(narrative, extractor, lang):
    """Replace the steady-trend closing clause of a single-segment sentence with the
    turning point, for a series that is fitted as one segment but rises then falls (or
    falls then rises)."""
    if not narrative or extractor is None:
        return narrative
    template = _library_translations(lang)["single_segment"]
    if _PERCENT_PLACEHOLDER not in template:
        return narrative
    closing = template.split(_PERCENT_PLACEHOLDER, 1)[1]
    if not closing or not narrative.endswith(closing):
        return narrative
    turn = _turning_point(extractor)
    if turn is None:
        return narrative
    year, value, is_peak = turn
    key = "narrative.turning_point_peak" if is_peak else "narrative.turning_point_low"
    return narrative[: -len(closing)] + t(key, lang, value=millify(value, lang), year=year)


def get_segment_narrative_i18n(*, lang="en", **kwargs):
    narrative = _call_with_language_fallback(get_segment_narrative, lang, **kwargs)
    return _name_turning_point(narrative, kwargs.get("extractor"), lang)


def get_relationship_narrative_i18n(*, lang="en", **kwargs):
    return _call_with_language_fallback(get_relationship_narrative, lang, **kwargs)
