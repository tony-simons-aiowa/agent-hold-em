"""Model options listing + resolution (ARCHITECTURE.md §4/§5 `GET /models`).

Verified against the installed Hermes source (docs/CONTRACT.md, "Model listing").
We use `hermes_cli.inventory.build_aux_picker_rows`, the same function Hermes'
auxiliary-task pickers use for provider/model choices. The call runs inside the
installed profile's config and secret scope because the dashboard hosts several
profiles in one process.

Every function here MUST NOT raise: an odd or partially-broken config.yaml must
degrade to "just the default model", never crash `GET /api/plugins/agent-hold-em/models`.
Returned labels never include API keys/secrets — only slugs, model ids and
human-readable provider names, which is all `build_aux_picker_rows` returns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..runtime_scope import hermes_profile_scope

logger = logging.getLogger(__name__)

__all__ = ["ModelOption", "list_options", "resolve"]

#: The reserved id for "use the account's main configured model" (ARCHITECTURE.md §4/§5).
DEFAULT_MODEL_ID = "default"


@dataclass(frozen=True, slots=True)
class ModelOption:
    id: str
    label: str
    provider: str  # "" for the default option (resolved lazily at decision time)
    model: str  # "" for the default option


def list_options(*, profile_name: str | None = None, max_models_per_provider: int = 6) -> tuple[list[ModelOption], str]:
    """`(options, default_id)` for `GET /models` (ARCHITECTURE.md §5).

    Always returns at least the "Your default model" option, even if every provider
    lookup fails. Never raises. Hermes may probe the active custom provider.
    """
    default_label = "Profile default model" if profile_name else "Your default model"
    options = [ModelOption(id=DEFAULT_MODEL_ID, label=default_label, provider="", model="")]
    try:
        with hermes_profile_scope(profile_name):
            options.extend(_configured_provider_options(max_models_per_provider))
    except Exception:
        logger.warning("agent-hold-em: model listing degraded to default-only", exc_info=True)
    return options, DEFAULT_MODEL_ID


def _configured_provider_options(max_models_per_provider: int) -> list[ModelOption]:
    from hermes_cli.inventory import build_aux_picker_rows

    rows = build_aux_picker_rows(max_models=max_models_per_provider)
    out: list[ModelOption] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        name = str(row.get("name") or slug).strip()
        if not slug:
            continue
        for model_row in row.get("models") or []:
            model_id = model_row.get("id") if isinstance(model_row, dict) else model_row
            model_id = str(model_id or "").strip()
            if not model_id:
                continue
            out.append(ModelOption(
                id=f"{slug}:{model_id}", label=f"{name} — {model_id}", provider=slug, model=model_id,
            ))
    return out


def resolve(model_id: str) -> tuple[str | None, str | None]:
    """`(provider, model)` for `model_id`, or `(None, None)` for the default/unknown id.

    `(None, None)` tells `HermesSeatRunner` to call `resolve_runtime_provider(requested=None,
    target_model=None)`, i.e. the account's main configured `model.provider`/`model.default` —
    exactly what an unset `--provider`/`--model` resolves to on the CLI. An id this function does
    not recognize (stale config, model removed from the account) safely falls back to the same
    default rather than raising or resolving to something the model_id didn't ask for.
    """
    if not model_id or model_id == DEFAULT_MODEL_ID:
        return None, None
    if ":" not in model_id:
        logger.warning("agent-hold-em: unrecognized model_id %r, falling back to default", model_id)
        return None, None
    provider, _, model = model_id.partition(":")
    provider, model = provider.strip(), model.strip()
    if not provider or not model:
        return None, None
    return provider, model
