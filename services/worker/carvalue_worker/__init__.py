"""CarValue background worker (ingestion, scheduling, training jobs).

Runs as a separate process from the API. Scheduling is disabled by default so
that no automated source collection starts before its permission gate passes
(deny-by-default data acquisition policy in AGENTS.md / PRD section 10).
"""

__version__ = "0.1.0"
