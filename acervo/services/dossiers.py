"""Dossier and cross-reference services (Phase 6).

Entity creation, relationship linking, assertion tracking, and chronology.
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.identifiers import next_identifier, IdKind
from acervo.db.models import (
    Assertion,
    Chronology,
    Collection,
    Entity,
    File,
    Relationship,
)
from acervo.domain.entities import ConfidenceLevel, EntityKind
from acervo.services.audit import record_event


# Map EntityKind to IdKind for identifier allocation
_ENTITY_KIND_TO_ID_KIND = {
    EntityKind.PERSON: IdKind.PERSON,
    EntityKind.LAWYER: IdKind.LAWYER,
    EntityKind.LAW_FIRM: IdKind.LAW_FIRM,
    EntityKind.ORGANIZATION: IdKind.ORGANIZATION,
    EntityKind.JUDICIAL_PROCEEDING: IdKind.JUDICIAL_PROCEEDING,
    EntityKind.POLICE_RECORD: IdKind.POLICE_ADMIN_RECORD,
    EntityKind.CONTRACT: IdKind.DOCUMENT,
    EntityKind.TRANSACTION: IdKind.DOCUMENT,
    EntityKind.PROPERTY: IdKind.LOCATION,
    EntityKind.LOCATION: IdKind.LOCATION,
    EntityKind.VEHICLE: IdKind.DEVICE,
    EntityKind.DEVICE: IdKind.DEVICE,
    EntityKind.EVENT: IdKind.EVENT,
    EntityKind.COMMUNICATION: IdKind.DOCUMENT,
    EntityKind.CLAIM: IdKind.DOCUMENT,
}


def create_entity(
    session: Session,
    collection: Collection,
    kind: EntityKind,
    name: str,
    description: str | None = None,
) -> Entity:
    """Create a new entity (person, lawyer, proceeding, etc.)."""
    id_kind = _ENTITY_KIND_TO_ID_KIND.get(kind, IdKind.DOCUMENT)
    ident = next_identifier(session, id_kind)
    entity = Entity(
        identifier=ident,
        collection_id=collection.id,
        kind=kind.value,
        name=name,
        display_name=name,
        description=description,
    )
    session.add(entity)
    session.flush()
    record_event(
        session,
        action="entity.created",
        subject_type="entity",
        subject_identifier=ident,
        detail={"kind": kind.value, "name": name},
    )
    return entity


def add_assertion(
    session: Session,
    subject: Entity,
    predicate: str,
    source_file: File | None = None,
    object_entity: Entity | None = None,
    literal_value: str | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED,
    extraction_method: str = "manual",
) -> Assertion:
    """Record a fact about an entity (subject-predicate-object model)."""
    assertion = Assertion(
        subject_id=subject.id,
        predicate=predicate,
        object_entity_id=object_entity.id if object_entity else None,
        literal_value=literal_value,
        source_file_id=source_file.id if source_file else None,
        extraction_method=extraction_method,
        confidence=confidence.value,
        review_status="pending",
    )
    session.add(assertion)
    session.flush()
    record_event(
        session,
        action="assertion.created",
        subject_type="assertion",
        detail={
            "subject": subject.identifier,
            "predicate": predicate,
            "confidence": confidence.value,
        },
    )
    return assertion


def link_entities(
    session: Session,
    source: Entity,
    target: Entity,
    relationship_type: str,
    role: str | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED,
) -> Relationship:
    """Create a relationship between two entities."""
    rel = Relationship(
        source_id=source.id,
        target_id=target.id,
        relationship_type=relationship_type,
        role=role,
        confidence=confidence.value,
    )
    session.add(rel)
    session.flush()
    record_event(
        session,
        action="relationship.created",
        subject_type="relationship",
        detail={
            "source": source.identifier,
            "target": target.identifier,
            "type": relationship_type,
        },
    )
    return rel


def add_chronology_event(
    session: Session,
    collection: Collection,
    event_date: str,
    event_type: str,
    description: str,
    entity: Entity | None = None,
    source_file: File | None = None,
) -> Chronology:
    """Add an event to master or entity chronology."""
    event = Chronology(
        collection_id=collection.id,
        entity_id=entity.id if entity else None,
        event_date=event_date,
        event_type=event_type,
        description=description,
        source_file_id=source_file.id if source_file else None,
        confidence="unverified",
    )
    session.add(event)
    session.flush()
    return event


def find_possible_duplicates(
    session: Session, collection: Collection, entity_name: str, kind: str | None = None
) -> list[Entity]:
    """Find entities with similar names (for manual review, DOS-005)."""
    query = select(Entity).where(
        Entity.collection_id == collection.id,
        Entity.name.ilike(f"%{entity_name}%"),
    )
    if kind:
        query = query.where(Entity.kind == kind)
    return session.execute(query).scalars().all()


def get_entity_dossier(session: Session, entity: Entity) -> dict:
    """Retrieve all assertions, relationships, and chronology for an entity."""
    # Assertions where this entity is the subject
    assertions = session.execute(
        select(Assertion).where(Assertion.subject_id == entity.id)
    ).scalars().all()

    # Relationships
    rels = session.execute(
        select(Relationship).where(
            (Relationship.source_id == entity.id) | (Relationship.target_id == entity.id)
        )
    ).scalars().all()

    # Entity chronology
    events = session.execute(
        select(Chronology).where(Chronology.entity_id == entity.id).order_by(Chronology.event_date)
    ).scalars().all()

    return {
        "entity": entity,
        "assertions": assertions,
        "relationships": rels,
        "chronology": events,
    }
