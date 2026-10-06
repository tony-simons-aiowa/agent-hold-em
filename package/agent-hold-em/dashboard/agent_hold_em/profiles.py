"""Read local Hermes profile identities and their Bot Mode avatars.

Profile ids come only from Hermes' live profile roster. No arbitrary filesystem
path supplied by a client is read. Bot Mode keeps its appearance in profile.yaml
and its rendered/uploaded image in assets/avatar.<format>.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

_ASSET_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
_MAX_AVATAR_BYTES = 2_000_000  # Hermes profiles.set_asset's own limit


def _bot_meta(profile_dir: Path) -> dict[str, Any]:
    try:
        import hermes_yaml as yaml

        raw = yaml.safe_load((profile_dir / "profile.yaml").read_text(encoding="utf-8-sig")) or {}
        ui_meta = raw.get("ui_meta") if isinstance(raw, dict) else None
        bot_meta = ui_meta.get("hermes-bots") if isinstance(ui_meta, dict) else None
        return bot_meta if isinstance(bot_meta, dict) else {}
    except Exception:  # corrupt optional presentation metadata must not break setup
        return {}


def _avatar(profile_dir: Path, bot_meta: dict[str, Any], profile_id: str) -> dict[str, str | None]:
    image = None
    shape = str(bot_meta.get("shape") or "circle")[:80]
    image_kind = str(bot_meta.get("imageKind") or "shape")
    # Bot Mode's vector Blobatar is live; its stored PNG is a backfill for
    # message notices and can lag a later appearance edit.
    if image_kind == "photo" or not shape.startswith("blobatar"):
        for ext, mime in _ASSET_TYPES.items():
            path = profile_dir / "assets" / f"avatar.{ext}"
            try:
                if path.is_file() and path.stat().st_size <= _MAX_AVATAR_BYTES:
                    image = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
                    break
            except OSError:
                continue
    return {
        "image": image,
        "image_kind": image_kind,
        "shape": shape,
        "color": str(bot_meta.get("color") or "#8b5cf6")[:80],
        "seed": profile_id,
    }


def list_profile_rows() -> list[dict[str, Any]]:
    """Local, live profiles only; presentation metadata never controls identity."""
    from hermes_cli.profiles import list_profiles

    rows = []
    for profile in list_profiles(lazy_skill_count=True):
        if getattr(profile, "role", None) == "setup":
            continue
        profile_id = profile.name
        profile_dir = Path(profile.path)
        meta = _bot_meta(profile_dir)
        title = str(meta.get("title") or getattr(profile, "display_name", "") or profile_id).strip()
        rows.append({
            "id": profile_id,
            "name": title or profile_id,
            "label": f"{title} ({profile_id})" if title and title != profile_id else profile_id,
            "avatar": _avatar(profile_dir, meta, profile_id),
            "model": getattr(profile, "model", None),
            "provider": getattr(profile, "provider", None),
        })
    return rows


def get_profile_row(profile_id: str) -> dict[str, Any] | None:
    return next((row for row in list_profile_rows() if row["id"] == profile_id), None)
