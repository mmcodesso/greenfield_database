# Contributing

Use GitHub Issues for concrete errors and GitHub Discussions for broader recommendations.

- Report typos, broken links, incorrect query references, factual errors, and other concrete mistakes in GitHub Issues: <https://github.com/mmcodesso/CharlesRiver_Database/issues/new/choose>
- Start improvement ideas, teaching recommendations, and broader enhancements in GitHub Discussions: <https://github.com/mmcodesso/CharlesRiver_Database/discussions/new?category=recommendations>
- The full site-facing workflow lives in [docs/technical/contributing.md](docs/technical/contributing.md)

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
npm run build
```

If your change affects dataset generation, settings, or report exports, also run the smallest relevant dataset build before opening the pull request.
