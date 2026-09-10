"""Fast DOM-based application autofill with no automatic submission."""

from __future__ import annotations

import json
from typing import Any

from .autofill import build_field_values, classify_field
from .models import ResumeProfile


_FORM_SCRIPT = """
() => JSON.stringify(Array.from(document.querySelectorAll('input, textarea, select')).map((el, index) => ({
  index,
  tag: el.tagName.toLowerCase(),
  type: el.getAttribute('type') || '',
  name: el.getAttribute('name') || '',
  id: el.id || '',
  placeholder: el.getAttribute('placeholder') || '',
  autocomplete: el.getAttribute('autocomplete') || '',
  aria: el.getAttribute('aria-label') || '',
  value: el.value || ''
})))
"""

_FILL_SCRIPT = """
({index, value}) => {
  const elements = Array.from(document.querySelectorAll('input, textarea, select'));
  const el = elements[index];
  if (!el) return false;
  const descriptor = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value');
  if (descriptor && descriptor.set) descriptor.set.call(el, value);
  else el.value = value;
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  return true;
}
"""


async def inspect_form(page: Any) -> list[dict[str, str | int]]:
    """Return lightweight metadata for fields on the current page."""
    raw = await page.evaluate(_FORM_SCRIPT)
    data = json.loads(str(raw))
    if not isinstance(data, list):
        raise RuntimeError("Browser returned an invalid form inspection payload")
    return data


def _field_labels(field: dict[str, str | int]) -> list[str]:
    return [
        str(field.get("name", "")),
        str(field.get("id", "")),
        str(field.get("placeholder", "")),
        str(field.get("autocomplete", "")),
        str(field.get("aria", "")),
    ]


def plan_autofill(fields: list[dict[str, str | int]], profile: ResumeProfile) -> list[tuple[int, str, str]]:
    """Create a deterministic fill plan from explicit profile facts."""
    values = build_field_values(profile)
    plan: list[tuple[int, str, str]] = []
    for field in fields:
        if str(field.get("type", "")).casefold() in {"hidden", "file", "password", "submit", "button"}:
            continue
        key = classify_field(*_field_labels(field))
        if key and key in values and not str(field.get("value", "")).strip():
            plan.append((int(field["index"]), key, values[key]))
    return plan


async def autofill_page(page: Any, profile: ResumeProfile) -> list[dict[str, str | int]]:
    """Fill only empty, confidently identified fields and never submit the form."""
    fields = await inspect_form(page)
    plan = plan_autofill(fields, profile)
    filled: list[dict[str, str | int]] = []
    for index, key, value in plan:
        result = await page.evaluate(_FILL_SCRIPT, {"index": index, "value": value})
        if str(result).casefold() not in {"true", "1"}:
            raise RuntimeError(f"Browser failed to fill field {index}")
        filled.append({"index": index, "field": key, "value": value})
    return filled
