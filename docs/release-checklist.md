# Release checklist

1. Ensure the released `abbr2words>=0.2.4` prerequisite containing the structured currency identities is available from the target package index.
2. Create an annotated Git tag such as `v0.2.2` only after all release gates pass.
3. Install a clean environment with `python -m pip install -e ".[dev]"`.
4. Run `python -m pytest`.
5. Run `python -m ruff check .` and `python -m ruff format --check .`.
6. Run `python -m mypy spokenform examples`.
7. Build with `python -m build`.
8. Validate distributions with `python -m twine check dist/*`.
9. Build docs with `sphinx-build -W -b html docs docs/_build/html`.
10. Test wheel installation and the `spokenform` console command in a fresh environment.
11. Confirm the release workflow uses a PyPI trusted publisher when repository OIDC is configured; otherwise verify the configured API token without changing authentication on release day.
12. Publish the GitHub release only after all required checks pass.
13. Before a downstream kokorog2p release raises its spokenform minimum, publish
    the spokenform release and verify the real `de`, `es`, and `fr` integration
    gates against released packages.

The publish workflow deliberately remains operator-triggered by a published
GitHub release. PyPI Trusted Publishing/OIDC is the preferred future mechanism
because it avoids long-lived API tokens, but migrating credentials is a separate
operational change that must be tested before a release is cut.
