"""Shared domain core of the CarValue modular monolith.

Contains unit conventions, vehicle taxonomy helpers, listing normalization and
deduplication, stable reason codes, confidence/refusal rules, persistence
models (SQLAlchemy), the CSV/XLSX import pipeline, source adapter boundary and
the baseline valuation model. No FastAPI or scheduler imports live here so the
domain stays testable on its own.
"""

__version__ = "0.1.0"
