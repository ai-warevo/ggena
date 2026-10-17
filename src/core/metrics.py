from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
REQUEST_LATENCY = Histogram(
    "ggena_request_latency_seconds",
    "Histogram of request durations in seconds.",
    buckets=(.05, .1, .25, .5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

GENERATION_ERRORS = Counter(
    "ggena_generation_errors_total",
    "Counter for failed generation attempts.",
    ["module", "error_type"]
)

ACTIVE_GENERATIONS = Gauge(
    "ggena_active_generations",
    "Gauge of currently running tasks."
)
