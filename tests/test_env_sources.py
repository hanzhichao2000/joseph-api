from pathlib import Path

import pytest

from joseph_api import env


@pytest.mark.parametrize("xdg", [None, "", "relative/path"])
def test_config_path_falls_back_to_home_independent_of_cwd(tmp_path, monkeypatch, xdg):
    path = getattr(env, "config_path", None)
    assert callable(path)
    home = tmp_path / "home"
    monkeypatch.chdir(tmp_path)
    assert path(xdg, home) == home / ".config/joseph/.env"
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert path(xdg, home) == home / ".config/joseph/.env"


def test_config_path_uses_absolute_xdg(tmp_path):
    assert env.config_path(str(tmp_path / "xdg"), tmp_path / "home") == Path(
        tmp_path / "xdg/joseph/.env"
    )


def test_dotenv_parses_whitespace_comments_and_values(tmp_path):
    parse = getattr(env, "parse_dotenv", None)
    assert callable(parse)
    file = tmp_path / "synthetic.env"
    file.write_text(" # comment\n JOSEPH_MINI_MODE = paper  \nJOSEPH_PROGRESS=off\n\n")
    assert parse(file.read_text()) == {"JOSEPH_MINI_MODE": "paper", "JOSEPH_PROGRESS": "off"}


def test_dotenv_empty_value_comment_and_literal_hashes():
    assert env.parse_dotenv(
        "EMPTY= # comment\nLITERAL=#literal\nSINGLE='#inside'\nDOUBLE=\"#inside\"\n"
    ) == {
        "EMPTY": "",
        "LITERAL": "#literal",
        "SINGLE": "#inside",
        "DOUBLE": "#inside",
    }


def test_dotenv_common_quoting_and_comments():
    text = (
        "A='single # value' # comment\n"
        'B="double \\"quote\\" \\\\ slash \\n newline \\t tab # kept" # comment\n'
        "C=  don't stop here  # comment\n"
        "D=abc#literal\n"
        "E=  unquoted internal space  \n"
    )
    assert env.parse_dotenv(text) == {
        "A": "single # value",
        "B": 'double "quote" \\ slash \n newline \t tab # kept',
        "C": "don't stop here",
        "D": "abc#literal",
        "E": "unquoted internal space",
    }


@pytest.mark.parametrize("text", ["A='canary' junk", 'A="canary"junk', 'A="canary', "A='canary"])
def test_dotenv_bad_quoted_values_are_sanitized(text):
    with pytest.raises(ValueError) as error:
        env.parse_dotenv(text)
    assert "canary" not in str(error.value)


@pytest.mark.parametrize(
    "text",
    [
        "JOSEPH_MINI_MODE=one\nJOSEPH_MINI_MODE=synthetic-secret",
        "export JOSEPH_MINI_MODE=synthetic-secret",
        "JOSEPH_MINI_MODE synthetic-secret",
        "BAD-KEY=synthetic-secret",
        "JOSEPH_MINI_MODE='unterminated synthetic-secret",
    ],
)
def test_dotenv_rejects_malformed_and_duplicate_without_values(text):
    with pytest.raises(ValueError) as error:
        env.parse_dotenv(text)
    assert "synthetic-secret" not in str(error.value)


def test_ordinary_environment_override_reports_only_name_and_sources():
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE"))
    registry.finalize()
    resolve = getattr(registry, "resolve_sources", None)
    assert callable(resolve)
    values, diagnostics = resolve(
        {"JOSEPH_MINI_MODE": "file-canary"}, {"JOSEPH_MINI_MODE": "env-canary"}
    )
    assert values["JOSEPH_MINI_MODE"] == "env-canary"
    assert diagnostics == (("JOSEPH_MINI_MODE", "file", "environment"),)


def test_controlled_rejects_inherited_values_without_permission():
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE"))
    registry.finalize()
    import inspect

    assert "controlled" in inspect.signature(registry.resolve_sources).parameters
    with pytest.raises(ValueError) as error:
        registry.resolve_sources({}, {"JOSEPH_MINI_MODE": "synthetic-secret"}, controlled=True)
    assert "JOSEPH_MINI_MODE" in str(error.value)
    assert "synthetic-secret" not in str(error.value)


def test_controlled_rejects_override_unless_explicitly_permitted():
    registry = env.Registry()
    registry.register(
        env.Declaration("mini", "JOSEPH_MINI_MODE", controlled_allow_environment=True)
    )
    registry.finalize()
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.resolve_sources(
            {"JOSEPH_MINI_MODE": "file"}, {"JOSEPH_MINI_MODE": "environment"}, controlled=True
        )


@pytest.mark.parametrize("source", ["file", "environment"])
def test_disallowed_declared_source_fails_without_value(source):
    registry = env.Registry()
    allowed = frozenset({"environment" if source == "file" else "file"})
    registry.register(
        env.Declaration(
            "mini", "JOSEPH_MINI_MODE", allowed_sources=allowed, controlled_allow_environment=True
        )
    )
    registry.finalize()
    supplied = {"JOSEPH_MINI_MODE": "synthetic-secret"}
    with pytest.raises(ValueError) as error:
        registry.resolve_sources(
            supplied if source == "file" else {},
            supplied if source == "environment" else {},
            controlled=True,
        )
    assert "JOSEPH_MINI_MODE" in str(error.value)
    assert "synthetic-secret" not in str(error.value)


def test_required_in_ordinary_mode_with_missing_file():
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE", required=True))
    registry.finalize()
    assert registry.resolve_sources(None, {"JOSEPH_MINI_MODE": "present"}) == (
        {"JOSEPH_MINI_MODE": "present"},
        (),
    )
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.resolve_sources(None, {})


def test_required_missing_fails_in_controlled_mode():
    registry = env.Registry()
    assert "required" in env.Declaration.__dataclass_fields__
    registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE", required=True))
    registry.finalize()
    with pytest.raises(ValueError, match="JOSEPH_MINI_MODE"):
        registry.resolve_sources({}, {}, controlled=True)


def test_unknown_names_reported_but_reserved_inactive_is_ignored():
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_MODE"))
    registry.finalize()
    values, diagnostics = registry.resolve_sources(
        {
            "JOSEPH_MINI_MODE": "active",
            "JOSEPH_PILOT_MODE": "inactive-canary",
            "JOSEPH_MINI_TYPO": "typo-canary",
            "JOSEPH_OTHER_VALUE": "other-canary",
            "JOSEPH_PROGRESS": "shared-canary",
        },
        {},
    )
    assert values == {"JOSEPH_MINI_MODE": "active"}
    assert set(diagnostics) == {
        ("JOSEPH_MINI_TYPO", "file"),
        ("JOSEPH_OTHER_VALUE", "file"),
        ("JOSEPH_PROGRESS", "file"),
    }


def test_controlled_requires_shared_file_even_if_no_variables_required():
    registry = env.Registry()
    registry.finalize()
    with pytest.raises(ValueError):
        registry.resolve_sources(None, {}, controlled=True)


def test_shared_required_declaration_enforced():
    import inspect

    assert "required" in inspect.signature(env.Declaration.shared).parameters
    registry = env.Registry()
    registry.register(env.Declaration.shared("host", "JOSEPH_PROGRESS", required=True))
    registry.finalize()
    with pytest.raises(ValueError, match="JOSEPH_PROGRESS"):
        registry.resolve_sources({}, {}, controlled=True)


def test_unknown_invalid_environment_name_cannot_inject_values_into_diagnostics():
    registry = env.Registry()
    registry.finalize()
    with pytest.raises(ValueError) as error:
        registry.resolve_sources({}, {"JOSEPH_BAD\nsynthetic-secret": "another-secret"})
    assert "synthetic-secret" not in str(error.value)
    assert "another-secret" not in str(error.value)
