import subprocess
import sys
from pathlib import Path


def test_import_does_not_inspect_environment_or_emit_diagnostics():
    source = Path(__file__).resolve().parents[1] / "src"
    script = f"""
import os
import sys
sys.path.insert(0, {str(source)!r})
class ForbiddenEnvironment(dict):
    def __getitem__(self, key):
        if key.startswith('JOSEPH_'):
            raise AssertionError('configuration read')
        return super().__getitem__(key)
    def __iter__(self):
        raise AssertionError('environment iteration')
    def get(self, key, default=None):
        if key.startswith('JOSEPH_'):
            raise AssertionError('configuration read')
        return super().get(key, default)
os.environ = ForbiddenEnvironment(os.environ)
os.getenv = os.environ.get
import joseph_api
import joseph_api.env
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={"JOSEPH_UNKNOWN_SYNTHETIC": "synthetic-value"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert not result.stdout
    assert not result.stderr
