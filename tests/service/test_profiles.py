from types import SimpleNamespace
from unittest.mock import patch

from agent_hold_em.profiles import list_profile_rows


def test_bot_mode_title_and_avatar_are_read_from_profile(tmp_path):
    profile_dir = tmp_path / "profiles" / "writer"
    (profile_dir / "assets").mkdir(parents=True)
    (profile_dir / "profile.yaml").write_text(
        "ui_meta:\n  hermes-bots:\n    title: Storyteller\n    shape: blobatar::cloud\n    color: '#123456'\n    imageKind: photo\n"
    )
    (profile_dir / "assets" / "avatar.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    profile = SimpleNamespace(name="writer", path=profile_dir, role=None, display_name="Fallback", model="test-model", provider="test")

    with patch("hermes_cli.profiles.list_profiles", return_value=[profile]):
        rows = list_profile_rows()

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "writer"
    assert row["name"] == "Storyteller"
    assert row["label"] == "Storyteller (writer)"
    assert row["avatar"]["image"].startswith("data:image/png;base64,")
    assert row["avatar"]["shape"] == "blobatar::cloud"
    assert row["avatar"]["color"] == "#123456"


def test_blobatar_uses_live_shape_instead_of_stale_backfill_png(tmp_path):
    profile_dir = tmp_path / "profiles" / "developer"
    (profile_dir / "assets").mkdir(parents=True)
    (profile_dir / "profile.yaml").write_text(
        "ui_meta:\n  hermes-bots:\n    shape: blobatar::triangle\n    imageKind: shape\n"
    )
    (profile_dir / "assets" / "avatar.png").write_bytes(b"old snapshot")
    profile = SimpleNamespace(name="developer", path=profile_dir, role=None, display_name="", model="m", provider="p")

    with patch("hermes_cli.profiles.list_profiles", return_value=[profile]):
        avatar = list_profile_rows()[0]["avatar"]

    assert avatar["image"] is None
    assert avatar["shape"] == "blobatar::triangle"
