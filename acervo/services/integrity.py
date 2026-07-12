"""Integrity & anomaly detection services (Phase 8).

Preliminary technical indicators (never forensic conclusions).
Detects metadata inconsistencies, encoding anomalies, contradictions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.models import Assertion, Contradiction, IntegrityFinding, File, Entity
from acervo.domain.integrity import AnomalyKind, AnomalySeverity, IntegrityFinding as FindingModel
from acervo.services.audit import record_event


class IntegrityAnalyzer:
    """Preliminary technical analysis (INT-001..004, never "forensic")."""

    @staticmethod
    def check_extension_mismatch(file_path: str | Path, mime_type: str | None) -> FindingModel | None:
        """Detect extension/content mismatch (e.g., .jpg with PDF mime type)."""
        path = Path(file_path)
        ext = path.suffix.lower()

        # Rough mapping; not authoritative
        ext_to_mime = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".mp4": "video/mp4",
            ".wav": "audio/wav",
        }

        expected = ext_to_mime.get(ext)
        if expected and mime_type and mime_type != expected and not mime_type.startswith(expected[:5]):
            return FindingModel(
                file_identifier="",
                anomaly_kind=AnomalyKind.EXTENSION_CONTENT_MISMATCH,
                severity=AnomalySeverity.MEDIUM,
                tool="file-inspector",
                tool_version="1.0",
                confidence=0.7,
                description=f"File extension {ext} does not match detected MIME {mime_type}",
                benign_explanations=[
                    "File renamed or has incorrect extension",
                    "MIME detection error",
                ],
            )
        return None

    @staticmethod
    def check_timestamp_consistency(
        fs_timestamp: str, metadata_timestamp: str | None
    ) -> FindingModel | None:
        """Flag if file-system and embedded timestamps differ significantly."""
        if not metadata_timestamp:
            return None
        # Simplified: check if they differ by >1 year
        try:
            fs_year = int(fs_timestamp[:4]) if fs_timestamp else 0
            meta_year = int(metadata_timestamp[:4]) if metadata_timestamp else 0
            if abs(fs_year - meta_year) > 1:
                return FindingModel(
                    file_identifier="",
                    anomaly_kind=AnomalyKind.TIMESTAMP_MISMATCH,
                    severity=AnomalySeverity.LOW,
                    tool="metadata-checker",
                    tool_version="1.0",
                    confidence=0.6,
                    description="File-system timestamp differs significantly from embedded metadata",
                    benign_explanations=[
                        "File was copied or archived",
                        "Time zone differences",
                        "File-system clock was incorrect",
                    ],
                )
        except (ValueError, IndexError):
            pass
        return None

    @staticmethod
    def detect_pdf_updates(pdf_data: bytes) -> list[FindingModel]:
        """Detect PDF incremental updates (may indicate page replacement)."""
        findings: list[FindingModel] = []
        # Simple heuristic: count "%%EOF" markers (PDF allows incremental updates)
        eof_count = pdf_data.count(b"%%EOF")
        if eof_count > 1:
            findings.append(
                FindingModel(
                    file_identifier="",
                    anomaly_kind=AnomalyKind.PDF_INCREMENTAL_UPDATE,
                    severity=AnomalySeverity.MEDIUM,
                    tool="pdf-analyzer",
                    tool_version="1.0",
                    confidence=0.8,
                    description=f"PDF contains {eof_count} incremental updates (may indicate modifications)",
                    benign_explanations=[
                        "PDF edited by standard PDF tools",
                        "Digitally signed PDF",
                    ],
                )
            )
        return findings


class ContradictionDetector:
    """Find conflicting assertions (LEGAL-005)."""

    @staticmethod
    def find_contradictions(session: Session, collection_id: int) -> list[tuple[Assertion, Assertion]]:
        """Simple heuristic: same subject + opposite predicates / conflicting dates."""
        contradictions: list[tuple[Assertion, Assertion]] = []

        # Get all entities in this collection
        collection_entity_ids = session.execute(
            select(Entity.id).where(Entity.collection_id == collection_id)
        ).scalars().all()

        # Get all assertions about these entities
        all_assertions = session.execute(
            select(Assertion).where(Assertion.subject_id.in_(collection_entity_ids))
        ).scalars().all()

        # Pairwise comparison (O(n²), but typically small set)
        for i, a1 in enumerate(all_assertions):
            for a2 in all_assertions[i + 1 :]:
                if a1.subject_id == a2.subject_id:
                    # Same subject — check for conflict
                    if _predicates_conflict(a1.predicate, a2.predicate):
                        contradictions.append((a1, a2))

        return contradictions

    @staticmethod
    def record_contradiction(
        session: Session,
        assertion_1: Assertion,
        assertion_2: Assertion,
        conflict_type: str = "factual",
    ) -> Contradiction:
        """Log a contradiction for human review."""
        from acervo.db.models import Contradiction

        contradiction = Contradiction(
            assertion_1_id=assertion_1.id,
            assertion_2_id=assertion_2.id,
            conflict_type=conflict_type,
            confidence=0.7,
            review_status="pending",
        )
        session.add(contradiction)
        session.flush()
        return contradiction


def _predicates_conflict(p1: str, p2: str) -> bool:
    """Heuristic: detect conflicting predicates."""
    opposites = [
        ("authored", "denied_authorship"),
        ("present_at", "absent_from"),
        ("employed_by", "not_employed_by"),
    ]
    for a, b in opposites:
        if (p1 == a and p2 == b) or (p1 == b and p2 == a):
            return True
    return False


def record_integrity_finding(
    session: Session, file: File, finding: FindingModel
) -> IntegrityFinding:
    """Persist an integrity finding to the database."""
    db_finding = IntegrityFinding(
        file_id=file.id,
        anomaly_kind=finding.anomaly_kind.value,
        severity=finding.severity.value,
        tool=finding.tool,
        tool_version=finding.tool_version,
        confidence=finding.confidence,
        location=finding.location,
        description=finding.description,
        benign_explanations=json.dumps(finding.benign_explanations) if finding.benign_explanations else None,
        review_status="pending",
    )
    session.add(db_finding)
    session.flush()
    record_event(
        session,
        action="integrity.finding",
        subject_type="file",
        subject_identifier=file.identifier,
        detail={
            "anomaly_kind": finding.anomaly_kind.value,
            "severity": finding.severity.value,
        },
    )
    return db_finding
