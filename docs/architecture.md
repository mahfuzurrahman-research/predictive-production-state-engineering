# Engineering architecture

The public repository demonstrates two independent engineering concerns.

## Forecast workflow

Synthetic release-vintage observations are admitted only if available by the origin date. Valid pairs are passed to two small demonstration forecasters, evaluated with standard metrics, written to a relational analytical layer, checked by SQL QA, and rendered into reports.

## Reliability workflow

Synthetic work is divided into deterministic units. Each unit receives a receipt containing source/config identities and an output hash. An intentional interruption is followed by a resume that reuses only validated units. A merged accepted artifact is written atomically.

Neither workflow reproduces the private empirical analysis.
