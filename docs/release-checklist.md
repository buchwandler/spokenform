# Release checklist

1. Ensure the released `abbr2words>=0.2.9,<0.3.0` prerequisite containing the reviewed structured identities and initialism policy is available from the target package index.

- Confirm the released Lexhint versions allowed by the `spokenform[lexhint]` extra pass the real provider contract test.
- For Lexhint 0.2.x, confirm a compatible schema-8 `runtime` dataset is published and installable.
- Run the URL, computing-context, and sports-context smoke tests with the installed schema-8 runtime artifact.

2. Create an annotated Git tag for the target release, for example `vX.Y.Z`, only after all release gates pass.
3. Install a clean environment with `python -m pip install -e ".[dev]"` and `python -m pip install -r docs/requirements.txt`.
4. Run `python -m pytest`.
5. Run `python -m pytest --cov=spokenform --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=85`.
6. Run `python -m ruff check .` and `python -m ruff format --check .`.
7. Run `python -m mypy spokenform examples`.
8. Build with `python -m build`.
9. Validate distributions with `python -m twine check dist/*`.
10. Build docs with `sphinx-build -W -b html docs docs/_build/html`.
11. Test wheel installation, one deterministic normalization example, and the `spokenform` console command in a fresh environment.
12. Confirm the release workflow uses a PyPI trusted publisher when repository OIDC is configured; otherwise verify the configured API token without changing authentication on release day.
13. Publish the GitHub release only after all required checks pass.
14. Before a downstream kokorog2p release raises its spokenform minimum, publish
    the spokenform release and verify the real `de`, `es`, and `fr` integration
    gates against released packages.

The publish workflow deliberately remains operator-triggered by a published
GitHub release. PyPI Trusted Publishing/OIDC is the preferred future mechanism
because it avoids long-lived API tokens, but migrating credentials is a separate
operational change that must be tested before a release is cut.
