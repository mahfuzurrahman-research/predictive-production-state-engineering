# Data quality controls

The synthetic pipeline checks:

1. temporal admissibility — predictors cannot arrive after the forecast origin;
2. target ordering — the target must occur after the origin;
3. relational key uniqueness;
4. finite analytical values;
5. positive forecast horizons;
6. presence of both demonstration systems;
7. deterministic recovery receipts and hash consistency.

The SQL checks are executable and are expected to return zero failures.
