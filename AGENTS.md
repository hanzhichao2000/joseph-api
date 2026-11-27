# joseph-api contributor instructions

This package owns the shared data models, revision records, and runtime environment registry.
Keep it at the bottom of the dependency graph. It must import no other joseph package.
Keep public symbols importable and update the public contract alongside any contract change.

## Local checks

Run from the repository root with Python 3.11 or newer. The development checks match
`.github/workflows/ci.yml`.

```sh
check_dir=$(mktemp -d)
python3 -m venv "$check_dir/dev"
"$check_dir/dev/bin/python" -m pip install -e '.[dev]'
"$check_dir/dev/bin/ruff" check src tests
"$check_dir/dev/bin/ruff" format --check src tests
"$check_dir/dev/bin/mypy"
"$check_dir/dev/bin/pytest" -q
```

Build the wheel from the checkout and verify it in a separate, fresh environment.
Run the import check outside the source tree.

```sh
"$check_dir/dev/bin/python" -m pip wheel --no-deps --wheel-dir "$check_dir/wheels" .
python3 -m venv "$check_dir/clean"
(
  set -e
  cd "$check_dir"
  ./clean/bin/python -m pip install wheels/joseph_api-*.whl &&
  env -u PYTHONPATH ./clean/bin/python -c 'import joseph_api as api; assert all(hasattr(api, name) for name in api.__all__)'
)
```

Downstream repositories pin `joseph-api` in their dependency metadata to a full,
immutable Git commit SHA. Consumers that need new API behavior, such as the option-row DTOs
from [joseph-api PR #10](https://github.com/hanzhichao2000/joseph-api/pull/10),
update their pin after the API PR merges, using the full SHA of the merged commit.

## Public contributions

- Use `codex/<topic>-<issue number>` for the branch. Keep planning and coordination in the owning internal
  issue. Public PRs require approval from a private-project lead.
- In `joseph-docs-public` only, add new public-layer Markdown files to `public-layer.allow`
  in the same PR and keep each file at or below 200 lines.
- Scan public changes for vendor names, private paths and URLs, credentials, and proprietary
  strategy identifiers. Keep internal roadmap details and evidence out of public files and PR text.
- Record verification commands, results, exact repository SHAs, and CI run links in the owning
  internal issue. Keep raw logs, research evidence, and generated reports out of this repository.
  Follow the public [evidence and claims contract](https://github.com/hanzhichao2000/joseph-docs-public/blob/main/contracts/evidence-and-claims.md).
