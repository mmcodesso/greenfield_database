# Contributing

Contributions are welcome after a public license is selected for the repository.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Tests

```powershell
pytest -q
```

## Generate Dataset

```powershell
python generate_dataset.py
```

## Contribution Guidelines

- Keep generated outputs out of Git.
- Keep `src/generator_dataset/schema.py` as the canonical schema registry.
- Add or update tests when changing generation rules.
- Preserve voucher-level GL balance.
- Preserve deterministic output for a fixed `random_seed`.
- Document any new anomaly type in `config/anomaly_profile.yaml` and `README.md`.

## Before Opening A Pull Request

Run:

```powershell
pytest -q
python -B -m compileall -q src tests
python generate_dataset.py
```

Then check `outputs/validation_report.json` for final validation exceptions.
