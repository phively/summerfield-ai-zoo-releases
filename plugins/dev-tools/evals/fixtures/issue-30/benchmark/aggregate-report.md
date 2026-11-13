# Synthetic benchmark report: cache comparison

**Question:** Should the service replace its current search path with the new cache?

**Observed result:** On one development machine, one aggregate run reported 100 ms for the current path and 82 ms for the cached path. Runs were sequential. The report does not identify cold or warm cache state.

**Not measured:** Repeated observations, answer quality, error rate, memory use, setup or maintenance cost, and recovery behavior.

This fixture is synthetic. It contains no production measurements.
