---
title: Contributing
description: Development workflow and contribution guidelines for the dataset repository.
sidebar_label: Contributing
slug: /technical/contributing
---

# Contributing

Use this page when you are contributing code, documentation, or tests to the dataset project.

## Development Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Core Working Rules

- Keep generated outputs out of Git.
- Keep `src/generator_dataset/schema.py` as the canonical schema registry.
- Add or update tests when generation rules change.
- Preserve voucher-level `GLEntry` balance.
- Preserve deterministic output for a fixed `random_seed`.
- Document any new anomaly type in `config/anomaly_profile.yaml` and the relevant documentation.

## Tests and Validation

Run these checks before opening a pull request:

```bash
pytest -q
python -B -m compileall -q src tests
python generate_dataset.py
```

After generation, review `outputs/validation_report.json` for any remaining validation exceptions.

## Documentation Contributions

- Keep the published documentation aligned with the current dataset and current workflow.
- Use direct instructional prose and keep routes stable unless a route change is required.
- Add or update internal links when pages move or titles change.

## Pull Request Expectations

- describe the teaching or technical goal clearly
- keep changes scoped to a coherent improvement
- include test coverage or explain why tests were not needed
- note any changes that affect generated outputs, validations, or documentation paths
