"""Persistence layer: SQLAlchemy engine, session factory and ORM models.

The MVP core ships the preservation-critical subset of the full domain model
(section 21). Remaining tables (OCR, transcripts, entities, dossiers, API
receipts…) are tracked in docs/BACKLOG.md and added in their respective phases.
"""
