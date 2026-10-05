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

## Fitted ML workflow

Raw daily records require canonical UTC arrivals, fabricated IDs, explicit
synthetic markers, finite values, exact fields and unique neutral row IDs.
Truth/unknown fields and observations reported before their daily period ends
are rejected. Repeated area/day records block affected feature histories rather
than being silently deduplicated.

Every scheduled origin/horizon remains visible. Missing or unavailable required
history produces a blocked feature row and null predictions. Later target labels
have explicit mature, pending, missing or duplicate status. None of those absent
values are imputed as zero. Training and evaluation admit labels according to
their actual recorded arrival, not only their event date.

Fifteen independent DuckDB checks cover source inventory, feature availability,
feature-value reconstruction, training-label cutoffs, forecast horizons,
model/reference availability, null/finite predictions, evaluation maturity,
forecast/evaluation inventory, final metric parity and unauthorized retraining.
Corruption tests deliberately violate temporal, numeric and inventory rules.
These checks validate the synthetic software contract, not a real source's
accuracy or measurement validity.
