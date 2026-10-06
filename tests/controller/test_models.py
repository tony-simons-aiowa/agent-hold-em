from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from agent_hold_em.controller import models


def test_default_option_always_present():
    options, default_id = models.list_options()
    assert default_id == "default"
    ids = [o.id for o in options]
    assert "default" in ids
    labels = {o.id: o.label for o in options}
    assert labels["default"] == "Your default model"


def test_resolve_default_returns_none_none():
    assert models.resolve("default") == (None, None)
    assert models.resolve("") == (None, None)


def test_resolve_provider_model_pair():
    assert models.resolve("openrouter:qwen/qwen3-coder") == ("openrouter", "qwen/qwen3-coder")


def test_resolve_unrecognized_id_falls_back_to_default_safely():
    assert models.resolve("not-a-real-id-no-colon") == (None, None)
    assert models.resolve("slug:") == (None, None)
    assert models.resolve(":model") == (None, None)


def test_list_options_never_raises_when_provider_lookup_is_broken():
    """A broken/odd config.yaml must degrade to default-only, never crash the /models route."""
    with patch(
        "hermes_cli.inventory.build_aux_picker_rows", side_effect=RuntimeError("config.yaml is garbage"),
    ):
        options, default_id = models.list_options()
    assert default_id == "default"
    assert [o.id for o in options] == ["default"]


def test_list_options_never_leaks_secrets_in_labels():
    with patch(
        "hermes_cli.inventory.build_aux_picker_rows",
        return_value=[{"slug": "custom", "name": "My Endpoint", "models": [{"id": "llama-3"}]}],
    ):
        options, _ = models.list_options()
    custom = [o for o in options if o.provider == "custom"]
    assert custom and custom[0].id == "custom:llama-3"
    for opt in options:
        assert "sk-" not in opt.label and "key" not in opt.label.lower()


def test_model_listing_enters_installed_profile_scope():
    entered = []

    @contextmanager
    def fake_scope(profile):
        entered.append(profile)
        yield
        entered.append("closed")

    def fake_rows(*, max_models):
        assert entered == ["developer"]
        assert max_models == 6
        return [{"slug": "test", "name": "Test", "models": ["model-a"]}]

    with patch("agent_hold_em.runtime_scope.installed_profile_name", return_value="developer"), \
         patch("hermes_cli.web_server_profiles._config_profile_scope", fake_scope), \
         patch("hermes_cli.inventory.build_aux_picker_rows", side_effect=fake_rows):
        options, _ = models.list_options()

    assert [o.id for o in options] == ["default", "test:model-a"]
    assert entered == ["developer", "closed"]


def test_model_listing_can_target_selected_profile():
    entered = []

    @contextmanager
    def fake_scope(profile):
        entered.append(profile)
        yield

    with patch("hermes_cli.web_server_profiles._config_profile_scope", fake_scope), \
         patch("hermes_cli.inventory.build_aux_picker_rows", return_value=[]):
        options, _ = models.list_options(profile_name="writer")

    assert entered == ["writer"]
    assert options[0].label == "Profile default model"
