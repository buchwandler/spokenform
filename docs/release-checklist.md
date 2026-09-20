# Release checklist

1. Ensure the released `abbr2words>=0.2.15,<0.3.0` prerequisite containing the source-aligned replacement contract, reviewed structured identities, CJK inventories, and initialism policy is available from the target package index.

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

### Spokenform Gold benchmark consumption

The Gold release workflow is operator-triggered and serializes one candidate per release tag. It plans the next version, builds and verifies deterministic candidate bytes, runs the real Spokenform consumer gate, compares an existing tag by manifest and archive SHA-256 values, publishes only equivalent or absent releases, and re-downloads the public zip for verification.

For a first dispatch, confirm that `../spokenform/benchmarks/spokenform_gold_release.json` points to a published immutable asset. Its archive and manifest hashes must be real values, not placeholders. The consumer must be able to run with `--offline` after one successful online cache fill. Do not replace the pin with a branch, a latest-release lookup, or a source checkout.

For the current pin, verify `v0.1.0-exp.2`, public release count `20,037`, embedded count `18,059`, and external-reference count `1,978`. A full consumer run must use:

```bash
python -m benchmarks.spokenform_gold \
  --split corpus \
  --accept-upstream-licenses \
  --report html
```

When updating the pin:

1. Inspect the intended release by tag, including prereleases.
2. Copy the release ZIP SHA-256 and manifest SHA-256.
3. Copy the release target commit.
4. Update `benchmarks/spokenform_gold_release.json`.
5. Run focused pin, cache, and release-consumer tests.
6. Populate the cache with the online full benchmark.
7. Verify all 20,037 records and the generated report metadata.
8. Rerun the same command with `--offline` and compare release identity, manifest hash, source revisions, counts, and results.

9. Publish the GitHub release only after all required checks pass.
10. Before a downstream kokorog2p release raises its spokenform minimum, publish
    the spokenform release and verify the real `de`, `es`, and `fr` integration
    gates against released packages.

- Before publishing Spokenform 0.4.0, verify the candidate checkout against the released PiperG2P package with `tests/test_real_piperg2p_integration.py`.
- After 0.4.0 is published, enable or verify the released Spokenform and released PiperG2P stack gate. Do not require a released Spokenform install for this API before 0.4.0 publication.

The publish workflow deliberately remains operator-triggered by a published
GitHub release. PyPI Trusted Publishing/OIDC is the preferred future mechanism
because it avoids long-lived API tokens, but migrating credentials is a separate
operational change that must be tested before a release is cut.
