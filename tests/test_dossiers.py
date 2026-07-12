"""Tests for Phase 6: Dossiers, Entities, Assertions, Relationships, Chronology."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.base import get_session_factory
from acervo.db.models import Collection, Entity, Assertion, Relationship, Chronology, File, CatalogingSession, SourceMedia
from acervo.domain.entities import EntityKind, ConfidenceLevel
from acervo.services.dossiers import (
    create_entity,
    add_assertion,
    link_entities,
    add_chronology_event,
    find_possible_duplicates,
    get_entity_dossier,
)
from acervo.services.sessions import create_collection


@pytest.fixture
def collection_with_file(isolated_env: dict) -> tuple[Collection, File, Session]:
    """Create a test collection, session, and file for entity linking."""
    session = get_session_factory()()
    try:
        collection = create_collection(
            session=session,
            name="Test Collection",
            description="For entity tests",
        )

        # Create a source media and cataloging session
        media = SourceMedia(
            identifier="MED-2024-0001",
            collection_id=collection.id,
            label="Test Media",
            source_root="/tmp/test_source",
        )
        session.add(media)
        session.flush()

        cs = CatalogingSession(
            identifier="CS-2024-0001",
            collection_id=collection.id,
            source_media_id=media.id,
            source_root="/tmp/test_source",
            destination_root="/tmp/test_dest",
            software_version="0.2.0",
        )
        session.add(cs)
        session.flush()

        # Create a test file
        file_obj = File(
            identifier="FILE-2024-0001",
            collection_id=collection.id,
            source_media_id=media.id,
            session_id=cs.id,
            original_filename="test.pdf",
            source_path="/tmp/test_source/test.pdf",
            size_bytes=12345,
            mime_type="application/pdf",
        )
        session.add(file_obj)
        session.commit()

        yield collection, file_obj, session
    finally:
        session.close()


class TestCreateEntity:
    """Tests for create_entity()."""

    def test_create_person_entity(self, collection_with_file: tuple[Collection, File, Session]):
        """Create a person entity and verify fields."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session,
            collection=collection,
            kind=EntityKind.PERSON,
            name="João da Silva",
            description="Witness in Case XYZ",
        )

        assert person.identifier.startswith("PER-")
        assert person.kind == EntityKind.PERSON.value
        assert person.name == "João da Silva"
        assert person.description == "Witness in Case XYZ"
        assert person.collection_id == collection.id

        # Verify it was persisted
        fetched = session.execute(
            select(Entity).where(Entity.identifier == person.identifier)
        ).scalar_one()
        assert fetched.name == "João da Silva"

    def test_create_lawyer_entity(self, collection_with_file: tuple[Collection, File, Session]):
        """Create a lawyer entity."""
        collection, _, session = collection_with_file

        lawyer = create_entity(
            session=session,
            collection=collection,
            kind=EntityKind.LAWYER,
            name="Dr. Maria Santos",
        )

        assert lawyer.identifier.startswith("LAW-")
        assert lawyer.kind == EntityKind.LAWYER.value

    def test_create_judicial_proceeding(self, collection_with_file: tuple[Collection, File, Session]):
        """Create a judicial proceeding entity."""
        collection, _, session = collection_with_file

        proceeding = create_entity(
            session=session,
            collection=collection,
            kind=EntityKind.JUDICIAL_PROCEEDING,
            name="Processo 1234567-89.2024.8.26.0100",
            description="Civil action for damages",
        )

        assert proceeding.identifier.startswith("CASE-")
        assert proceeding.kind == EntityKind.JUDICIAL_PROCEEDING.value

    def test_entity_identifiers_are_unique(self, collection_with_file: tuple[Collection, File, Session]):
        """Verify identifiers are unique."""
        collection, _, session = collection_with_file

        person1 = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Alice"
        )
        person2 = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Bob"
        )

        assert person1.identifier != person2.identifier


class TestAddAssertion:
    """Tests for add_assertion()."""

    def test_add_assertion_with_literal_value(self, collection_with_file: tuple[Collection, File, Session]):
        """Add an assertion with a literal string value."""
        collection, file_obj, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="John Doe"
        )

        assertion = add_assertion(
            session=session,
            subject=person,
            predicate="birth_date",
            literal_value="1990-05-15",
            source_file=file_obj,
            confidence=ConfidenceLevel.CONFIRMED,
            extraction_method="manual",
        )

        assert assertion.subject_id == person.id
        assert assertion.predicate == "birth_date"
        assert assertion.literal_value == "1990-05-15"
        assert assertion.source_file_id == file_obj.id
        assert assertion.confidence == "confirmed"
        assert assertion.review_status == "pending"

    def test_add_assertion_linking_entities(self, collection_with_file: tuple[Collection, File, Session]):
        """Add an assertion linking two entities (subject-predicate-object)."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Alice"
        )
        org = create_entity(
            session=session, collection=collection, kind=EntityKind.ORGANIZATION, name="Legal Corp"
        )

        assertion = add_assertion(
            session=session,
            subject=person,
            predicate="works_at",
            object_entity=org,
            confidence=ConfidenceLevel.USER_CONFIRMED,
        )

        assert assertion.subject_id == person.id
        assert assertion.object_entity_id == org.id
        assert assertion.predicate == "works_at"
        assert assertion.literal_value is None
        assert assertion.confidence == "user_confirmed"

    def test_assertion_with_extraction_method(self, collection_with_file: tuple[Collection, File, Session]):
        """Verify extraction_method is recorded."""
        collection, file_obj, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Test"
        )

        assertion = add_assertion(
            session=session,
            subject=person,
            predicate="name",
            literal_value="Test Person",
            extraction_method="ocr",
        )

        assert assertion.extraction_method == "ocr"

        # Try with NLP
        assertion2 = add_assertion(
            session=session,
            subject=person,
            predicate="role",
            literal_value="Defendant",
            extraction_method="nlp",
        )

        assert assertion2.extraction_method == "nlp"

    def test_assertion_default_values(self, collection_with_file: tuple[Collection, File, Session]):
        """Verify default values for assertion creation."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Bob"
        )

        assertion = add_assertion(
            session=session,
            subject=person,
            predicate="residence",
            literal_value="São Paulo, SP",
        )

        assert assertion.source_file_id is None
        assert assertion.object_entity_id is None
        assert assertion.confidence == "unverified"
        assert assertion.extraction_method == "manual"
        assert assertion.review_status == "pending"


class TestLinkEntities:
    """Tests for link_entities()."""

    def test_link_lawyer_to_proceeding(self, collection_with_file: tuple[Collection, File, Session]):
        """Link a lawyer to a judicial proceeding."""
        collection, _, session = collection_with_file

        lawyer = create_entity(
            session=session, collection=collection, kind=EntityKind.LAWYER, name="Dr. Silva"
        )
        proceeding = create_entity(
            session=session,
            collection=collection,
            kind=EntityKind.JUDICIAL_PROCEEDING,
            name="Case 2024-0001",
        )

        rel = link_entities(
            session=session,
            source=lawyer,
            target=proceeding,
            relationship_type="represents",
            role="defense_counsel",
            confidence=ConfidenceLevel.CONFIRMED,
        )

        assert rel.source_id == lawyer.id
        assert rel.target_id == proceeding.id
        assert rel.relationship_type == "represents"
        assert rel.role == "defense_counsel"
        assert rel.confidence == "confirmed"
        assert rel.is_confirmed is False

    def test_link_person_to_person(self, collection_with_file: tuple[Collection, File, Session]):
        """Link two persons (e.g., family relationship)."""
        collection, _, session = collection_with_file

        parent = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Mother"
        )
        child = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Child"
        )

        rel = link_entities(
            session=session,
            source=child,
            target=parent,
            relationship_type="child_of",
            confidence=ConfidenceLevel.CONFIRMED,
        )

        assert rel.source_id == child.id
        assert rel.target_id == parent.id
        assert rel.relationship_type == "child_of"

    def test_relationship_with_dates(self, collection_with_file: tuple[Collection, File, Session]):
        """Link entities with start and end dates."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Employee"
        )
        company = create_entity(
            session=session, collection=collection, kind=EntityKind.ORGANIZATION, name="Company"
        )

        rel = link_entities(
            session=session,
            source=person,
            target=company,
            relationship_type="employed_by",
            role="engineer",
        )

        # Update with dates (simulating a scenario where dates might be added)
        session.query(Relationship).filter(Relationship.id == rel.id).update(
            {"start_date": "2020-01-15", "end_date": "2023-12-31"},
            synchronize_session=False,
        )
        session.commit()

        updated = session.query(Relationship).filter(Relationship.id == rel.id).one()
        assert updated.start_date == "2020-01-15"
        assert updated.end_date == "2023-12-31"

    def test_multiple_relationships(self, collection_with_file: tuple[Collection, File, Session]):
        """Create multiple relationships from one entity."""
        collection, _, session = collection_with_file

        lawyer = create_entity(
            session=session, collection=collection, kind=EntityKind.LAWYER, name="Dr. Silva"
        )
        case1 = create_entity(
            session=session, collection=collection, kind=EntityKind.JUDICIAL_PROCEEDING, name="Case 1"
        )
        case2 = create_entity(
            session=session, collection=collection, kind=EntityKind.JUDICIAL_PROCEEDING, name="Case 2"
        )

        rel1 = link_entities(
            session=session, source=lawyer, target=case1, relationship_type="represents"
        )
        rel2 = link_entities(
            session=session, source=lawyer, target=case2, relationship_type="represents"
        )

        assert rel1.source_id == lawyer.id
        assert rel2.source_id == lawyer.id
        assert rel1.target_id != rel2.target_id


class TestChronology:
    """Tests for add_chronology_event()."""

    def test_add_master_chronology_event(self, collection_with_file: tuple[Collection, File, Session]):
        """Add an event to master chronology (no entity)."""
        collection, file_obj, session = collection_with_file

        event = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-06-15",
            event_type="case_filed",
            description="Lawsuit filed in district court",
            source_file=file_obj,
        )

        assert event.collection_id == collection.id
        assert event.entity_id is None  # Master chronology
        assert event.event_date == "2024-06-15"
        assert event.event_type == "case_filed"
        assert event.source_file_id == file_obj.id
        assert event.confidence == "unverified"

    def test_add_entity_chronology_event(self, collection_with_file: tuple[Collection, File, Session]):
        """Add an event to an entity's chronology."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Witness"
        )

        event = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-05-20",
            event_type="testimony_given",
            description="Gave sworn testimony",
            entity=person,
        )

        assert event.entity_id == person.id
        assert event.event_type == "testimony_given"

    def test_chronology_ordering(self, collection_with_file: tuple[Collection, File, Session]):
        """Verify chronology can be retrieved in order."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Actor"
        )

        # Add events in reverse order
        event2 = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-06-01",
            event_type="event_b",
            description="Second event",
            entity=person,
        )

        event1 = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-05-01",
            event_type="event_a",
            description="First event",
            entity=person,
        )

        event3 = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-07-01",
            event_type="event_c",
            description="Third event",
            entity=person,
        )

        # Retrieve in order
        events = session.query(Chronology).filter(
            Chronology.entity_id == person.id
        ).order_by(Chronology.event_date).all()

        assert len(events) == 3
        assert events[0].event_date == "2024-05-01"
        assert events[1].event_date == "2024-06-01"
        assert events[2].event_date == "2024-07-01"


class TestFindDuplicates:
    """Tests for find_possible_duplicates()."""

    def test_find_duplicates_by_name_similarity(self, collection_with_file: tuple[Collection, File, Session]):
        """Find entities with similar names."""
        collection, _, session = collection_with_file

        # Create variants of the same name
        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="João Silva")
        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="João da Silva")
        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="John Silva")

        # Search for "Silva"
        duplicates = find_possible_duplicates(
            session=session, collection=collection, entity_name="Silva"
        )

        assert len(duplicates) == 3

    def test_find_duplicates_by_kind(self, collection_with_file: tuple[Collection, File, Session]):
        """Find duplicates filtered by entity kind."""
        collection, _, session = collection_with_file

        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="Silva")
        create_entity(session=session, collection=collection, kind=EntityKind.LAWYER, name="Silva")
        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="Silva Jr")

        # Find all "Silva" persons
        person_silvas = find_possible_duplicates(
            session=session, collection=collection, entity_name="Silva", kind="person"
        )

        # Should find at least 2 persons (not the lawyer)
        assert len(person_silvas) >= 2
        assert all(e.kind == "person" for e in person_silvas)

    def test_no_duplicates_found(self, collection_with_file: tuple[Collection, File, Session]):
        """Test when no duplicates are found."""
        collection, _, session = collection_with_file

        create_entity(session=session, collection=collection, kind=EntityKind.PERSON, name="Alice")

        duplicates = find_possible_duplicates(
            session=session, collection=collection, entity_name="Bob"
        )

        assert len(duplicates) == 0


class TestGetEntityDossier:
    """Tests for get_entity_dossier()."""

    def test_dossier_includes_assertions(self, collection_with_file: tuple[Collection, File, Session]):
        """Retrieve dossier with all assertions for an entity."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Test Person"
        )

        a1 = add_assertion(
            session=session,
            subject=person,
            predicate="birth_date",
            literal_value="1985-03-10",
        )
        a2 = add_assertion(
            session=session,
            subject=person,
            predicate="residence",
            literal_value="São Paulo",
        )

        dossier = get_entity_dossier(session=session, entity=person)

        assert dossier["entity"].id == person.id
        assert len(dossier["assertions"]) == 2
        assert a1.id in [a.id for a in dossier["assertions"]]
        assert a2.id in [a.id for a in dossier["assertions"]]

    def test_dossier_includes_relationships(self, collection_with_file: tuple[Collection, File, Session]):
        """Retrieve dossier with all relationships for an entity."""
        collection, _, session = collection_with_file

        lawyer = create_entity(
            session=session, collection=collection, kind=EntityKind.LAWYER, name="Dr. Silva"
        )
        case = create_entity(
            session=session, collection=collection, kind=EntityKind.JUDICIAL_PROCEEDING, name="Case 1"
        )

        rel = link_entities(
            session=session,
            source=lawyer,
            target=case,
            relationship_type="represents",
        )

        dossier = get_entity_dossier(session=session, entity=lawyer)

        assert len(dossier["relationships"]) == 1
        assert dossier["relationships"][0].id == rel.id

    def test_dossier_includes_chronology(self, collection_with_file: tuple[Collection, File, Session]):
        """Retrieve dossier with chronology events."""
        collection, _, session = collection_with_file

        person = create_entity(
            session=session, collection=collection, kind=EntityKind.PERSON, name="Witness"
        )

        event1 = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-05-01",
            event_type="interview",
            description="First interview",
            entity=person,
        )
        event2 = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-06-01",
            event_type="testimony",
            description="Gave testimony",
            entity=person,
        )

        dossier = get_entity_dossier(session=session, entity=person)

        assert len(dossier["chronology"]) == 2
        # Verify ordering
        assert dossier["chronology"][0].event_date <= dossier["chronology"][1].event_date

    def test_complete_dossier(self, collection_with_file: tuple[Collection, File, Session]):
        """Retrieve complete dossier with all components."""
        collection, file_obj, session = collection_with_file

        lawyer = create_entity(
            session=session, collection=collection, kind=EntityKind.LAWYER, name="Dr. Silva"
        )
        case = create_entity(
            session=session, collection=collection, kind=EntityKind.JUDICIAL_PROCEEDING, name="Case 1"
        )

        # Add assertion
        assertion = add_assertion(
            session=session,
            subject=lawyer,
            predicate="bar_id",
            literal_value="123456",
            source_file=file_obj,
        )

        # Add relationship
        relationship = link_entities(
            session=session,
            source=lawyer,
            target=case,
            relationship_type="represents",
        )

        # Add chronology
        event = add_chronology_event(
            session=session,
            collection=collection,
            event_date="2024-06-01",
            event_type="case_accepted",
            description="Dr. Silva accepted case",
            entity=lawyer,
        )

        dossier = get_entity_dossier(session=session, entity=lawyer)

        assert dossier["entity"].id == lawyer.id
        assert len(dossier["assertions"]) >= 1
        assert len(dossier["relationships"]) >= 1
        assert len(dossier["chronology"]) >= 1
