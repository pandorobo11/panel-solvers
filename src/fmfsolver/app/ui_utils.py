"""FMF GUI formatting compatibility helpers."""

from ..gui_spec import format_case as format_case_text


def _as_float(value):
    try:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return None
        return float(text)
    except Exception:
        return None


__all__ = ("format_case_text",)
