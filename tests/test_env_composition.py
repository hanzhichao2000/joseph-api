import pytest

from joseph_api import env


def test_raw_resolution_cannot_bypass_source_policy():
    registry = env.Registry()
    registry.register(
        env.Declaration("mini", "JOSEPH_MINI_MODE", allowed_sources=frozenset({"file"}))
    )
    registry.finalize()
    assert not hasattr(registry, "resolve")
    with pytest.raises(ValueError):
        registry.resolve_sources({}, {"JOSEPH_MINI_MODE": "value"})


def test_resolution_requires_explicit_finalization():
    registry = env.Registry()
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_MODE"))
    resolve = registry.resolve_sources
    with pytest.raises(RuntimeError):
        resolve({"JOSEPH_MINI_MODE": "paper"}, {})
    registry.finalize()
    assert resolve({"JOSEPH_MINI_MODE": "paper"}, {}) == ({"JOSEPH_MINI_MODE": "paper"}, ())


def test_later_module_requires_new_finalization():
    registry = env.Registry()
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_MODE"))
    registry.finalize()
    registry.register(env.Declaration(owner="pilot", name="JOSEPH_PILOT_MODE"))
    values = {"JOSEPH_MINI_MODE": "paper", "JOSEPH_PILOT_MODE": "research"}
    assert registry.resolve_sources(values, {})[0] == {"JOSEPH_MINI_MODE": "paper"}
    registry.finalize()
    assert registry.resolve_sources(values, {})[0] == values


def test_failed_later_finalization_keeps_previous_snapshot():
    registry = env.Registry()
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_MODE"))
    registry.finalize()
    registry.register(env.Declaration(owner="pilot", name="JOSEPH_PILOT_MODE"))
    registry.register(env.Declaration(owner="other", name="JOSEPH_MINI_MODE"))
    canary = "synthetic-value-never-in-diagnostics-abcdef"
    with pytest.raises(ValueError) as error:
        registry.finalize()
    assert canary not in str(error.value)
    resolved = registry.resolve_sources(
        {"JOSEPH_MINI_MODE": "paper", "JOSEPH_PILOT_MODE": canary}, {}
    )[0]
    assert set(resolved) == {"JOSEPH_MINI_MODE"}
    assert resolved["JOSEPH_MINI_MODE"] == "paper"


def test_public_reservations_and_private_extensions_are_available():
    registry = env.Registry()
    reserve = getattr(registry, "reserve", None)
    assert callable(reserve)
    registry.finalize()
    assert registry.owner_of("JOSEPH_MINI_MODE") == "mini"
    assert registry.owner_of("JOSEPH_PILOT_MODE") == "pilot"
    reserve("private", "JOSEPH_CUSTOM_")
    registry.finalize()
    assert registry.owner_of("JOSEPH_CUSTOM_MODE") == "private"


def test_overlapping_reservations_fail_without_replacing_active_snapshot():
    registry = env.Registry()
    registry.finalize()
    registry.reserve("private", "JOSEPH_MINI_EXTRA_")
    with pytest.raises(ValueError, match="JOSEPH_MINI_"):
        registry.finalize()
    assert registry.owner_of("JOSEPH_MINI_EXTRA_VALUE") == "mini"


def test_package_declaration_must_match_reservation_owner():
    registry = env.Registry()
    registry.register(env.Declaration(owner="other", name="JOSEPH_MINI_MODE"))
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.finalize()


def test_unreserved_variables_require_exact_shared_declaration():
    registry = env.Registry()
    registry.register(env.Declaration(owner="mini", name="JOSEPH_UNKNOWN_VALUE"))
    with pytest.raises(ValueError, match="JOSEPH_UNKNOWN_VALUE"):
        registry.finalize()


def test_shared_progress_is_exact_and_can_be_resolved():
    registry = env.Registry()
    shared = getattr(env.Declaration, "shared", None)
    assert callable(shared)
    registry.register(shared(owner="host", name="JOSEPH_PROGRESS"))
    registry.finalize()
    assert registry.resolve_sources({"JOSEPH_PROGRESS": "off", "JOSEPH_PROGRESS_EXTRA": "x"}, {})[
        0
    ] == {"JOSEPH_PROGRESS": "off"}


def test_identical_name_with_different_rules_conflicts():
    registry = env.Registry()
    fields = env.Declaration.__dataclass_fields__
    assert "sensitive" in fields
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_PIN", sensitive=False))
    registry.register(env.Declaration(owner="mini", name="JOSEPH_MINI_PIN", sensitive=True))
    with pytest.raises(ValueError, match="JOSEPH_MINI_PIN"):
        registry.finalize()


@pytest.mark.parametrize("name", ["PROGRESS", "JOSEPH_", "JOSEPH_BAD-NAME", "JOSEPH_bad"])
def test_shared_names_must_be_exact_canonical_joseph_names(name):
    registry = env.Registry()
    registry.register(env.Declaration.shared(owner="host", name=name))
    with pytest.raises(ValueError):
        registry.finalize()


def test_shared_declaration_cannot_claim_package_namespace():
    registry = env.Registry()
    registry.register(env.Declaration.shared(owner="mini", name="JOSEPH_MINI_MODE"))
    with pytest.raises(ValueError):
        registry.finalize()


@pytest.mark.parametrize("prefix", ["MINI_", "JOSEPH_", "JOSEPH_bad_", "JOSEPH_BAD"])
def test_reservations_require_canonical_package_prefix(prefix):
    registry = env.Registry()
    registry.reserve("private", prefix)
    with pytest.raises(ValueError):
        registry.finalize()


def test_source_policy_is_immutable_and_part_of_canonical_declaration():
    registry = env.Registry()
    assert "allowed_sources" in env.Declaration.__dataclass_fields__
    first = env.Declaration(
        owner="mini", name="JOSEPH_MINI_MODE", allowed_sources=frozenset({"file"})
    )
    second = env.Declaration(
        owner="mini", name="JOSEPH_MINI_MODE", allowed_sources=frozenset({"environment"})
    )
    registry.register(first)
    registry.register(second)
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.finalize()


def test_source_policy_cannot_be_mutated_after_registration():
    registry = env.Registry()
    sources = {"file"}
    declaration = env.Declaration(owner="mini", name="JOSEPH_MINI_MODE", allowed_sources=sources)
    registry.register(declaration)
    sources.add("environment")
    registry.finalize()
    assert declaration.allowed_sources == frozenset({"file"})


def test_invalid_source_policy_is_rejected():
    registry = env.Registry()
    registry.register(
        env.Declaration(owner="mini", name="JOSEPH_MINI_MODE", allowed_sources=frozenset({"typo"}))
    )
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.finalize()


def test_shared_declaration_accepts_sensitive_and_source_metadata():
    import inspect

    signature = inspect.signature(env.Declaration.shared)
    assert "sensitive" in signature.parameters
    declaration = env.Declaration.shared(
        owner="host", name="JOSEPH_PROGRESS", sensitive=True, allowed_sources=frozenset({"file"})
    )
    registry = env.Registry()
    registry.register(declaration)
    registry.finalize()
    assert declaration.sensitive and declaration.allowed_sources == frozenset({"file"})


def test_conflict_diagnostic_identifies_both_owners():
    registry = env.Registry()
    registry.register(env.Declaration(owner="other", name="JOSEPH_MINI_MODE"))
    registry.register(env.Declaration(owner="third", name="JOSEPH_MINI_MODE"))
    with pytest.raises(ValueError) as error:
        registry.finalize()
    text = str(error.value)
    assert "JOSEPH_MINI_MODE" in text and "other" in text and "third" in text
