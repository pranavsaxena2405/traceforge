# TRACEFORGE Release & Publishing Guide

This guide provides step-by-step instructions for publishing **`pip install traceforge`** to PyPI and launching the open-source repository on GitHub.

---

## 1. Publish SDK to PyPI (`pip install traceforge`)

The PyPI distribution wheel and source packages have already been generated inside `dist/`:
- `dist/traceforge-0.1.0-py3-none-any.whl`
- `dist/traceforge-0.1.0.tar.gz`

### To Upload to PyPI:

1. Create a free account at [PyPI.org](https://pypi.org/account/register/).
2. Create an API Token under Account Settings.
3. Run the upload command:

```bash
python -m twine upload dist/*
```

4. When prompted:
   - Username: `__token__`
   - Password: `<your-pypi-api-token>`

> **Result**: Anyone in the world can now run `pip install traceforge`!

---

## 2. Launch Open-Source Repository on GitHub

1. Create a new repository on GitHub named `traceforge`.
2. Open terminal in the project directory and run:

```bash
# Initialize git repository
git init

# Add files and commit
git add .
git commit -m "feat: TRACEFORGE v0.1 release with SDK, Collector, Evals, CLI, and Web Dashboard"

# Connect to GitHub and push
git remote add origin https://github.com/<your-username>/traceforge.git
git branch -M main
git push -u origin main
```

---

## 3. Host Collector Backend on Cloud VM (AWS / DigitalOcean / GCP)

To allow developers across a team to send trace telemetry to a shared URL:

1. Launch a cloud VM (Linux Ubuntu/Debian).
2. Install Docker & Docker Compose.
3. Clone repository and run:

```bash
git clone https://github.com/<your-username>/traceforge.git
cd traceforge
docker compose up -d
```

4. Developers configure their SDKs:

```bash
export TRACEFORGE_COLLECTOR_URL="http://<your-server-ip>:8000/api/v1/traces"
```
