import json
import os
import stat
import traceback
from pathlib import Path

import pytest

from joseph_api import env


def test_shared_file_resolution_and_redacted_view(tmp_path: Path) -> None:
    path = tmp_path / "config"
    path.write_text(
        "JOSEPH_MINI_PIN=file-canary\n"
        "JOSEPH_MINI_VALUE=file-value\n"
        "JOSEPH_PILOT_VALUE=inactive-value\n"
        "JOSEPH_MINI_UNKNOWN=unknown-canary\n"
    )
    path.chmod(0o600)
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_PIN", sensitive=True))
    registry.register(env.Declaration("mini", "JOSEPH_MINI_VALUE"))
    registry.finalize()

    file_values = env.read_shared_file(path)
    values, diagnostics = registry.resolve_sources(
        file_values, {"JOSEPH_MINI_VALUE": "environment-value"}
    )
    assert values == {"JOSEPH_MINI_PIN": "file-canary", "JOSEPH_MINI_VALUE": "environment-value"}
    assert diagnostics == (
        ("JOSEPH_MINI_VALUE", "file", "environment"),
        ("JOSEPH_MINI_UNKNOWN", "file"),
    )
    redacted = registry.redacted(values)
    assert redacted == {"JOSEPH_MINI_PIN": "***", "JOSEPH_MINI_VALUE": "environment-value"}
    serialized = json.dumps({"values": redacted, "diagnostics": diagnostics})
    for value in ("file-canary", "inactive-value", "unknown-canary"):
        assert value not in serialized


def test_secure_file_reading(tmp_path: Path) -> None:
    path = tmp_path / "config"
    path.write_text("JOSEPH_MINI_VALUE=hello\n")
    path.chmod(0o600)
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    assert reader(path) == {"JOSEPH_MINI_VALUE": "hello"}


def test_redacted_view_uses_declaration_metadata() -> None:
    registry = env.Registry()
    registry.register(env.Declaration("mini", "JOSEPH_MINI_PIN", sensitive=True))
    registry.register(env.Declaration("mini", "JOSEPH_MINI_VALUE"))
    registry.finalize()
    redact = getattr(registry, "redacted", None)
    assert callable(redact)
    result = redact({"JOSEPH_MINI_PIN": "canary-value", "JOSEPH_MINI_VALUE": "visible"})
    assert result == {"JOSEPH_MINI_PIN": "***", "JOSEPH_MINI_VALUE": "visible"}
    assert "canary-value" not in json.dumps(result)
    assert "canary-value" not in str(result)


def test_unsafe_inactive_file_is_rejected_without_chmod(tmp_path: Path) -> None:
    path = tmp_path / "config"
    path.write_text("JOSEPH_PILOT_VALUE=canary-value\n")
    path.chmod(0o640)
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    with pytest.raises(ValueError) as caught:
        reader(path)
    assert "canary-value" not in "".join(traceback.format_exception(caught.value))
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_missing_and_links(tmp_path: Path) -> None:
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    path = tmp_path / "missing"
    assert reader(path) is None
    with pytest.raises(ValueError):
        reader(path, controlled=True)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        reader(link)
    path.write_text("JOSEPH_MINI_VALUE=hello\n")
    path.chmod(0o600)
    with pytest.raises(ValueError):
        reader(link)


def test_malformed_and_nonregular_fail_closed(tmp_path: Path) -> None:
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    path = tmp_path / "config"
    for content in (b'bad="canary-value', b"canary-value=\xff"):
        path.write_bytes(content)
        path.chmod(0o600)
        with pytest.raises(ValueError) as caught:
            reader(path)
        assert "canary-value" not in "".join(traceback.format_exception(caught.value))
    with pytest.raises(ValueError):
        reader(tmp_path)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(ValueError):
        reader(fifo)


def test_redaction_requires_finalization_and_drops_unknown() -> None:
    registry = env.Registry()
    redact = getattr(registry, "redacted", None)
    assert callable(redact)
    with pytest.raises(RuntimeError):
        redact({})
    registry.finalize()
    assert redact({"JOSEPH_MINI_UNKNOWN": "canary-value"}) == {}
    registry.register(env.Declaration("mini", "JOSEPH_MINI_UNKNOWN", sensitive=True))
    assert redact({"JOSEPH_MINI_UNKNOWN": "canary-value"}) == {}
    registry.finalize()
    assert redact({"JOSEPH_MINI_UNKNOWN": "canary-value"}) == {"JOSEPH_MINI_UNKNOWN": "***"}


def test_wide_parent_directory_is_allowed(tmp_path: Path) -> None:
    tmp_path.chmod(0o777)
    path = tmp_path / "config"
    path.write_text("JOSEPH_MINI_VALUE=hello")
    path.chmod(0o600)
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    assert reader(path) == {"JOSEPH_MINI_VALUE": "hello"}


def test_platform_failure_is_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reader = getattr(env, "read_shared_file", None)
    supports = getattr(env, "_supports_secure_file_reading", None)
    assert callable(reader) and callable(supports)
    monkeypatch.setattr(env, "_supports_secure_file_reading", lambda: False)
    with pytest.raises(ValueError):
        reader(tmp_path / "missing")


def test_unreadable_file_is_sanitized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)

    def denied(*args: object, **kwargs: object) -> int:
        raise PermissionError("canary-value")

    monkeypatch.setattr(os, "open", denied)
    with pytest.raises(ValueError) as caught:
        reader(tmp_path / "config")
    assert "canary-value" not in "".join(traceback.format_exception(caught.value))


def test_owner_mismatch_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config"
    path.write_text("JOSEPH_MINI_VALUE=canary-value")
    path.chmod(0o600)
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    monkeypatch.setattr(os, "geteuid", lambda: path.stat().st_uid + 1)
    with pytest.raises(ValueError) as caught:
        reader(path)
    assert "canary-value" not in "".join(traceback.format_exception(caught.value))


def test_ancestor_symlink_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    config = real / "config"
    config.write_text("JOSEPH_MINI_VALUE=canary-value")
    config.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError):
        env.read_shared_file(link / "config")


def test_ancestor_replacement_uses_open_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    config = parent / "config"
    config.write_text("JOSEPH_MINI_VALUE=original")
    config.chmod(0o600)
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    replacement_config = replacement / "config"
    replacement_config.write_text("JOSEPH_MINI_VALUE=canary-value")
    replacement_config.chmod(0o600)
    original_open = os.open

    def swapping_open(path, flags, *args, **kwargs):
        fd = original_open(path, flags, *args, **kwargs)
        if path == "parent":
            parent.rename(tmp_path / "old-parent")
            replacement.rename(parent)
        return fd

    monkeypatch.setattr(os, "open", swapping_open)
    assert env.read_shared_file(config) == {"JOSEPH_MINI_VALUE": "original"}
    assert not parent.joinpath("config").read_text().endswith("original")


def test_path_replacement_does_not_change_open_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config"
    path.write_text("JOSEPH_MINI_VALUE=original")
    path.chmod(0o600)
    replacement = tmp_path / "replacement"
    replacement.write_text("JOSEPH_MINI_VALUE=canary-value")
    replacement.chmod(0o666)
    reader = getattr(env, "read_shared_file", None)
    assert callable(reader)
    original_open = os.open

    def replacing_open(*args: object, **kwargs: object) -> int:
        fd = original_open(*args, **kwargs)
        if args[0] == "config":
            replacement.replace(path)
        return fd

    monkeypatch.setattr(os, "open", replacing_open)
    assert reader(path) == {"JOSEPH_MINI_VALUE": "original"}
