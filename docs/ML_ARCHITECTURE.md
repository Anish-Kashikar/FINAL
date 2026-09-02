# RAILSYNC AI Simulation ML Risk Layer

RAILSYNC uses a Random Forest classifier to estimate **failure within 30 days** from simulated historical data. It does not plan railway blocks and does not claim real Indian Railways data.

`simulated history -> feature engineering -> Random Forest risk probability -> existing priority score -> CP-SAT -> safety validation -> controller approval`

Features include asset condition/type/status, criticality, task severity/type, traffic impact, duration, existing simulation failure signal, maintenance timing, deadline urgency, department, and corridor. The generated target is feature-correlated with controlled noise. A stratified train/test split uses random seed 42. The target is not an input feature.

The trained artifact and metrics are stored under `backend/ml/artifacts/`. If the artifact, scikit-learn, or inference is unavailable, the existing `failure_probability` is used unchanged. CP-SAT constraints and final approval remain authoritative.

Production use would require authorized, governed historical maintenance and failure data plus validation, monitoring, security review, and railway-system adapters.
