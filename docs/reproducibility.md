# Reproducibility

## Local

```bash
python -m pip install -r requirements.txt
./run_public_demo.sh
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Docker

```bash
docker build -t predictive-production-state-engineering .
docker run --rm predictive-production-state-engineering
```

All scientific inputs used here are synthetic and generated inside the repository.
