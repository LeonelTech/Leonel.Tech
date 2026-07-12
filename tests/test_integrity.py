"""Tests for Phase 8: Integrity Analysis, Anomalies, and Contradictions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.base import get_session_factory
from acervo.db.models import (
    Collection,
    Entity,
    Assertion,
    File,
    IntegrityFinding,
    Contradiction,
    CatalogingSession,
    SourceMedia,
)
from acervo.domain.integrity import (
    AnomalyKind,
    AnomalySeverity,
    IntegrityFinding as FindingModel,
)
from acervo.domain.entities import EntityKind, ConfidenceLevel
from acervo.services.integrity import (
    IntegrityAnalyzer,
    ContradictionDetector,
    record_integrity_finding,
)
from acervo.services.sessions import create_collection
from acervo.services.dossiers import create_entity, add_assertion


@pytest.fixture
def collection_with_files(isolated_env: dict) -> tuple[Collection, list[File], Session]:
    """Create a test collection with multiple files."""
    session = get_session_factory()()
    try:
        collection = create_collection(
            session=session,
            name="Integrity Test Collection",
            description="For integrity analysis tests",
        )

        # Create source media and cataloging session
        media = SourceMedia(
            identifier="MED-2024-0002",
            collection_id=collection.id,
            label="Test Media",
            source_root="/tmp/test_source",
        )
        session.add(media)
        session.flush()

        cs = CatalogingSession(
            identifier="CS-2024-0002",
            collection_id=collection.id,
            source_media_id=media.id,
            source_root="/tmp/test_source",
            destination_root="/tmp/test_dest",
            software_version="0.2.0",
        )
        session.add(cs)
        session.flush()

        # Create multiple test files
        files = []
        for i in range(3):
            file_obj = File(
                identifier=f"FILE-2024-{1001 + i}",
                collection_id=collection.id,
                source_media_id=media.id,
                session_id=cs.id,
                original_filename=f"document_{i}.pdf",
                source_path=f"/tmp/test_source/document_{i}.pdf",
                size_bytes=10000 + (i * 1000),
                mime_type="application/pdf",
            )
            session.add(file_obj)
            files.append(file_obj)

        session.commit()
        yield collection, files, session
    finally:
        session.close()


class TestIntegrityAnalyzerExtensionMismatch:
    """Tests for IntegrityAnalyzer.check_extension_mismatch()."""

    def test_extension_mismatch_detected(self):
        """Detect when file extension doesn't match MIME type."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="document.jpg", mime_type="application/pdf"
        )

        assert finding is not None
        assert finding.anomaly_kind == AnomalyKind.EXTENSION_CONTENT_MISMATCH
        assert finding.severity == AnomalySeverity.MEDIUM
        assert finding.confidence == 0.7
        assert "extension" in finding.description.lower()
        assert "jpg" in finding.description.lower()

    def test_matching_extension_and_mime(self):
        """No finding when extension and MIME match."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="document.pdf", mime_type="application/pdf"
        )

        assert finding is None

    def test_partial_mime_match(self):
        """Allow partial MIME type matches."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="image.jpg", mime_type="image/jpeg"
        )

        assert finding is None

    def test_no_mime_type_provided(self):
        """No finding when MIME type is not provided."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="document.pdf", mime_type=None
        )

        assert finding is None

    def test_unknown_extension(self):
        """No finding for unknown/unsupported extensions."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="document.xyz", mime_type="application/unknown"
        )

        assert finding is None

    def test_benign_explanations_included(self):
        """Verify benign explanations are suggested."""
        finding = IntegrityAnalyzer.check_extension_mismatch(
            file_path="file.txt", mime_type="application/pdf"
        )

        assert finding is not None
        assert finding.benign_explanations is not None
        assert len(finding.benign_explanations) > 0
        assert any("rename" in exp.lower() for exp in finding.benign_explanations)


class TestIntegrityAnalyzerTimestampConsistency:
    """Tests for IntegrityAnalyzer.check_timestamp_consistency()."""

    def test_timestamps_within_one_year(self):
        """No finding when timestamps are within 1 year."""
        finding = IntegrityAnalyzer.check_timestamp_consistency(
            fs_timestamp="2024-05-15", metadata_timestamp="2024-06-20"
        )

        assert finding is None

    def test_timestamps_differ_by_two_years(self):
        """Find when timestamps differ by more than 1 year."""
        finding = IntegrityAnalyzer.check_timestamp_consistency(
            fs_timestamp="2022-05-15", metadata_timestamp="2024-06-20"
        )

        assert finding is not None
        assert finding.anomaly_kind == AnomalyKind.TIMESTAMP_MISMATCH
        assert finding.severity == AnomalySeverity.LOW
        assert finding.confidence == 0.6

    def test_no_metadata_timestamp(self):
        """No finding when metadata timestamp is missing."""
        finding = IntegrityAnalyzer.check_timestamp_consistency(
            fs_timestamp="2024-05-15", metadata_timestamp=None
        )

        assert finding is None

    def test_invalid_timestamp_format(self):
        """Handle invalid timestamp formats gracefully."""
        finding = IntegrityAnalyzer.check_timestamp_consistency(
            fs_timestamp="invalid", metadata_timestamp="2024-05-15"
        )

        # Should not crash, return None
        assert finding is None

    def test_benign_explanations_for_timestamp(self):
        """Verify benign explanations for timestamp mismatches."""
        finding = IntegrityAnalyzer.check_timestamp_consistency(
            fs_timestamp="2020-01-01", metadata_timestamp="2023-01-01"
        )

        assert finding is not None
        assert finding.benign_explanations is not None
        assert any("copy" in exp.lower() or "archive" in exp.lower() for exp in finding.benign_explanations)


class TestIntegrityAnalyzerPdfUpdates:
    """Tests for IntegrityAnalyzer.detect_pdf_updates()."""

    def test_single_pdf_no_updates(self):
        """PDF with single %%EOF (no incremental updates)."""
        pdf_data = b"%PDF-1.4\nstream\n%%EOF"
        findings = IntegrityAnalyzer.detect_pdf_updates(pdf_data)

        assert len(findings) == 0

    def test_multiple_pdf_updates(self):
        """PDF with multiple %%EOF markers (incremental updates detected)."""
        pdf_data = b"%PDF-1.4\nstream\n%%EOF\nupdate1\n%%EOF\nupdate2\n%%EOF"
        findings = IntegrityAnalyzer.detect_pdf_updates(pdf_data)

        assert len(findings) == 1
        assert findings[0].anomaly_kind == AnomalyKind.PDF_INCREMENTAL_UPDATE
        assert findings[0].severity == AnomalySeverity.MEDIUM
        assert findings[0].confidence == 0.8
        assert "3" in findings[0].description  # 3 EOF markers

    def test_pdf_with_two_updates(self):
        """PDF with exactly 2 %%EOF markers."""
        pdf_data = b"PDF content\n%%EOF\nincremental update\n%%EOF"
        findings = IntegrityAnalyzer.detect_pdf_updates(pdf_data)

        assert len(findings) == 1
        assert "2" in findings[0].description

    def test_benign_explanations_for_pdf(self):
        """Verify benign explanations for PDF updates."""
        pdf_data = b"PDF\n%%EOF\n%%EOF\n%%EOF"
        findings = IntegrityAnalyzer.detect_pdf_updates(pdf_data)

        assert len(findings) == 1
        assert findings[0].benign_explanations is not None
        assert any("edit" in exp.lower() or "sign" in exp.lower() for exp in findings[0].benign_explanations)

    def test_empty_pdf(self):
        """Handle empty PDF gracefully."""
        pdf_data = b""
        findings = IntegrityAnalyzer.detect_pdf_updates(pdf_data)

        assert len(findings) == 0


class TestRecordIntegrityFinding:
    """Tests for record_integrity_finding()."""

    def test_record_finding_persists_to_database(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Record a finding and verify it's persisted."""
        collection, files, session = collection_with_files
        file_obj = files[0]

        finding_model = FindingModel(
            file_identifier=file_obj.identifier,
            anomaly_kind=AnomalyKind.EXTENSION_CONTENT_MISMATCH,
            severity=AnomalySeverity.MEDIUM,
            tool="file-inspector",
            tool_version="1.0",
            confidence=0.75,
            description="File extension mismatch detected",
            benign_explanations=["Renamed file", "MIME detection error"],
        )

        db_finding = record_integrity_finding(session=session, file=file_obj, finding=finding_model)

        assert db_finding.file_id == file_obj.id
        assert db_finding.anomaly_kind == AnomalyKind.EXTENSION_CONTENT_MISMATCH.value
        assert db_finding.severity == AnomalySeverity.MEDIUM.value
        assert db_finding.confidence == 0.75
        assert db_finding.review_status == "pending"

        # Verify in database
        fetched = session.query(IntegrityFinding).filter(
            IntegrityFinding.id == db_finding.id
        ).one()
        assert fetched.file_id == file_obj.id
        assert fetched.tool == "file-inspector"

    def test_benign_explanations_stored_as_json(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Verify benign explanations are stored as JSON."""
        collection, files, session = collection_with_files
        file_obj = files[0]

        explanations = ["Reason 1", "Reason 2", "Reason 3"]
        finding_model = FindingModel(
            file_identifier=file_obj.identifier,
            anomaly_kind=AnomalyKind.TIMESTAMP_MISMATCH,
            severity=AnomalySeverity.LOW,
            tool="metadata-checker",
            tool_version="1.0",
            confidence=0.6,
            description="Timestamp mismatch",
            benign_explanations=explanations,
        )

        db_finding = record_integrity_finding(session=session, file=file_obj, finding=finding_model)

        # Verify JSON storage
        assert db_finding.benign_explanations is not None
        stored_list = json.loads(db_finding.benign_explanations)
        assert stored_list == explanations

    def test_location_recorded(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Verify location (page/timestamp/frame) is recorded."""
        collection, files, session = collection_with_files
        file_obj = files[0]

        finding_model = FindingModel(
            file_identifier=file_obj.identifier,
            anomaly_kind=AnomalyKind.PDF_INCREMENTAL_UPDATE,
            severity=AnomalySeverity.MEDIUM,
            tool="pdf-analyzer",
            tool_version="1.0",
            confidence=0.8,
            description="Incremental update detected",
            location="page 5-7",
        )

        db_finding = record_integrity_finding(session=session, file=file_obj, finding=finding_model)

        assert db_finding.location == "page 5-7"

    def test_multiple_findings_per_file(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Record multiple findings for same file."""
        collection, files, session = collection_with_files
        file_obj = files[0]

        finding1 = FindingModel(
            file_identifier=file_obj.identifier,
            anomaly_kind=AnomalyKind.EXTENSION_CONTENT_MISMATCH,
            severity=AnomalySeverity.MEDIUM,
            tool="tool1",
            tool_version="1.0",
            confidence=0.7,
            description="Finding 1",
        )

        finding2 = FindingModel(
            file_identifier=file_obj.identifier,
            anomaly_kind=AnomalyKind.TIMESTAMP_MISMATCH,
            severity=AnomalySeverity.LOW,
            tool="tool2",
            tool_version="1.0",
            confidence=0.6,
            description="Finding 2",
        )

        db_f1 = record_integrity_finding(session=session, file=file_obj, finding=finding1)
        db_f2 = record_integrity_finding(session=session, file=file_obj, finding=finding2)

        findings = session.query(IntegrityFinding).filter(
            IntegrityFinding.file_id == file_obj.id
        ).all()

        assert len(findings) == 2
        assert db_f1.id != db_f2.id


class TestContradictionDetector:
    """Tests for ContradictionDetector.find_contradictions()."""

    def test_find_authored_vs_denied_authorship(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Detect contradiction between 'authored' and 'denied_authorship'."""
        collection, files, session = collection_with_files

        # Create person entity
        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Author"
        )

        # Create document entities
        doc1 = create_entity(
            session=session, collection=collection, kind=EntityKind.CLAIM, name="Document A"
        )
        doc2 = create_entity(
            session=session, collection=collection, kind=EntityKind.CLAIM, name="Document B"
        )

        # Add contradictory assertions
        a1 = add_assertion(
            session=session,
            subject=person,
            predicate="authored",
            object_entity=doc1,
            confidence=ConfidenceLevel.CONFIRMED,
        )

        a2 = add_assertion(
            session=session,
            subject=person,
            predicate="denied_authorship",
            object_entity=doc2,
            confidence=ConfidenceLevel.CONFIRMED,
        )

        # Find contradictions
        contradictions = ContradictionDetector.find_contradictions(session=session, collection_id=collection.id)

        # Note: Both assertions are about same subject but different objects
        # The detector checks if predicates conflict for same subject
        # In this case, we need assertions about the SAME object to trigger contradiction
        # Let's modify:

        # Actually, let's test with same object
        session.query(Assertion).filter(Assertion.id == a2.id).delete()
        session.commit()

        a3 = add_assertion(
            session=session,
            subject=person,
            predicate="denied_authorship",
            object_entity=doc1,  # Same document
            confidence=ConfidenceLevel.CONFIRMED,
        )

        contradictions = ContradictionDetector.find_contradictions(session=session, collection_id=collection.id)

        assert len(contradictions) > 0
        # At least one pair should involve the conflicting predicates
        found = any(
            (c[0].predicate in ["authored", "denied_authorship"] and c[1].predicate in ["authored", "denied_authorship"])
            for c in contradictions
        )
        assert found

    def test_find_present_absent_contradiction(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Detect 'present_at' vs 'absent_from' contradiction."""
        collection, files, session = collection_with_files

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Person"
        )
        location = create_entity(
            session=session, collection=collection, kind=EntityKind.LOCATION, name="Place"
        )

        a1 = add_assertion(
            session=session,
            subject=person,
            predicate="present_at",
            object_entity=location,
        )

        a2 = add_assertion(
            session=session,
            subject=person,
            predicate="absent_from",
            object_entity=location,
        )

        contradictions = ContradictionDetector.find_contradictions(session=session, collection_id=collection.id)

        assert len(contradictions) > 0

    def test_find_employed_contradiction(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Detect 'employed_by' vs 'not_employed_by' contradiction."""
        collection, files, session = collection_with_files

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Employee"
        )
        company = create_entity(
            session=session, collection=collection, kind=EntityKind.ORGANIZATION, name="Company"
        )

        a1 = add_assertion(
            session=session,
            subject=person,
            predicate="employed_by",
            object_entity=company,
        )

        a2 = add_assertion(
            session=session,
            subject=person,
            predicate="not_employed_by",
            object_entity=company,
        )

        contradictions = ContradictionDetector.find_contradictions(session=session, collection_id=collection.id)

        assert len(contradictions) > 0

    def test_no_contradictions_with_compatible_predicates(self, collection_with_files: tuple[Collection, list[File], Session]):
        """No contradiction for compatible predicates about same subject."""
        collection, files, session = collection_with_files

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Person"
        )

        org1 = create_entity(
            session=session, collection=collection, kind=EntityKind.ORGANIZATION, name="Org 1"
        )
        org2 = create_entity(
            session=session, collection=collection, kind=EntityKind.ORGANIZATION, name="Org 2"
        )

        # Person works at two different orgs (compatible)
        add_assertion(
            session=session,
            subject=person,
            predicate="works_at",
            object_entity=org1,
        )

        add_assertion(
            session=session,
            subject=person,
            predicate="works_at",
            object_entity=org2,
        )

        contradictions = ContradictionDetector.find_contradictions(session=session, collection_id=collection.id)

        # Should not find contradictions for compatible predicates
        assert len(contradictions) == 0


class TestRecordContradiction:
    """Tests for ContradictionDetector.record_contradiction()."""

    def test_record_contradiction(self, collection_with_files: tuple[Collection, list[File], Session]):
        """Record a contradiction for human review."""
        collection, files, session = collection_with_files

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Person"
        )
        location = create_entity(
            session=session, collection=collection, kind=EntityKind.LOCATION, name="Place"
        )

        a1 = add_assertion(
            session=session,
            subject=person,
            predicate="present_at",
            object_entity=location,
            confidence=ConfidenceLevel.CONFIRMED,
        )

        a2 = add_assertion(
            session=session,
            subject=person,
            predicate="absent_from",
            object_entity=location,
            confidence=ConfidenceLevel.CONFIRMED,
        )

        contradiction = ContradictionDetector.record_contradiction(
            session=session,
            assertion_1=a1,
            assertion_2=a2,
            conflict_type="temporal",
        )

        assert contradiction.assertion_1_id == a1.id
        assert contradiction.assertion_2_id == a2.id
        assert contradiction.conflict_type == "temporal"
        assert contradiction.confidence == 0.7
        assert contradiction.review_status == "pending"

        # Verify in database
        fetched = session.query(Contradiction).filter(
            Contradiction.id == contradiction.id
        ).one()
        assert fetched.assertion_1_id == a1.id
        assert fetched.assertion_2_id == a2.id
