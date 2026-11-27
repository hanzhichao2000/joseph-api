import importlib.util

import pytest


@pytest.mark.parametrize("kind", ["owner", "name", "prefix"])
@pytest.mark.parametrize("control", ["\n", "\u0085"])
def test_invalid_metadata_cannot_inject_diagnostic_lines(kind, control):
    from joseph_api import env

    registry = env.Registry()
    if kind == "owner":
        registry.register(env.Declaration(f"mini{control}FAKE_LOG", "JOSEPH_MINI_MODE"))
        registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE"))
    elif kind == "name":
        registry.register(env.Declaration("mini", f"JOSEPH_MINI_MODE{control}FAKE_LOG"))
        registry.register(env.Declaration("other", f"JOSEPH_MINI_MODE{control}FAKE_LOG"))
    else:
        registry.reserve("mini", f"JOSEPH_MINI_{control}FAKE_LOG")
    with pytest.raises(ValueError) as error:
        registry.finalize()
    assert "FAKE_LOG" not in str(error.value)
    assert "\n" not in str(error.value)


def test_runtime_environment_module_is_available():
    assert importlib.util.find_spec("joseph_api.env") is not None


def test_identical_declaration_registration_is_idempotent():
    from joseph_api import env

    registry_type = getattr(env, "Registry", None)
    declaration_type = getattr(env, "Declaration", None)
    assert registry_type is not None and declaration_type is not None
    registry = registry_type()
    declaration = declaration_type(owner="mini", name="JOSEPH_MINI_MODE")
    registry.register(declaration)
    registry.register(declaration_type(owner="mini", name="JOSEPH_MINI_MODE"))
    assert registry.finalize() == (declaration,)


def test_conflicting_owners_are_rejected_on_finalization():
    from joseph_api import env

    registry = env.Registry()
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_MODE"))
    registry.register(env.Declaration(owner="other", name="JOSEPH_MINI_MODE"))
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.finalize()
