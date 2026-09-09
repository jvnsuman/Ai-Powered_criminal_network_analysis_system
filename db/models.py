"""
db/models.py

SQLAlchemy ORM models — the persisted (table) shape of the domain
dataclasses defined in schema/user.py, schema/case.py, and
schema/entities.py. db/repository.py is the adapter that converts
between these ORM rows and those dataclasses; nothing outside db/
should import from this module directly.
"""

from sqlalchemy import Column, Float, ForeignKey, String, Table
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models below."""


# Many-to-many join table between cases and their assigned investigators.
case_investigators = Table(
    "case_investigators",
    Base.metadata,
    Column("case_id", String, ForeignKey("cases.id"), primary_key=True),
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
)


class AgencyORM(Base):
    """Table form of schema.user.Agency."""

    __tablename__ = "agencies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    agency_type = Column(String, nullable=False)
    parent_agency_id = Column(String, ForeignKey("agencies.id"), nullable=True)
    is_active = Column(String, default="true")  # "true"/"false" string, matched at the repository layer

    users = relationship("UserORM", back_populates="agency")
    cases = relationship("CaseORM", back_populates="agency")


class UserORM(Base):
    """Table form of schema.user.User."""

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    badge_id = Column(String, unique=True, nullable=False, index=True)
    agency_id = Column(String, ForeignKey("agencies.id"), nullable=False)
    role = Column(String, nullable=False)  # schema.user.Role value
    password_hash = Column(String, nullable=True)
    last_login = Column(String, nullable=True)

    agency = relationship("AgencyORM", back_populates="users")
    assigned_cases = relationship("CaseORM", secondary=case_investigators, back_populates="investigators")


class CaseORM(Base):
    """Table form of schema.case.Case."""

    __tablename__ = "cases"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    agency_id = Column(String, ForeignKey("agencies.id"), nullable=False)
    status = Column(String, nullable=False, default="open")  # schema.case.CaseStatus value
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    opened_at = Column(String, nullable=False)

    agency = relationship("AgencyORM", back_populates="cases")
    investigators = relationship("UserORM", secondary=case_investigators, back_populates="assigned_cases")
    documents = relationship("SourceDocumentORM", back_populates="case")


class SourceDocumentORM(Base):
    """Table form of schema.entities.SourceDocument."""

    __tablename__ = "source_documents"

    id = Column(String, primary_key=True)
    document_type = Column(String, nullable=False)  # one of schema.entities.VALID_DOCUMENT_TYPES
    raw_text = Column(String, nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)

    case = relationship("CaseORM", back_populates="documents")
    entities = relationship("EntityORM", back_populates="source_document")


class EntityORM(Base):
    """Table form of schema.entities.Entity. Not yet written to by any
    route — reserved for when nlp/extraction.py starts producing real
    entities to persist.
    """

    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)  # schema.entities.EntityType value
    raw_text = Column(String, nullable=False)
    normalized_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    source_document_id = Column(String, ForeignKey("source_documents.id"), nullable=True)

    source_document = relationship("SourceDocumentORM", back_populates="entities")


class RelationshipORM(Base):
    """Table form of schema.entities.Relationship. Not yet written to
    by any route — reserved for when graph/build.py starts persisting
    edges.
    """

    __tablename__ = "relationships"

    id = Column(String, primary_key=True)
    source_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    relationship_type = Column(String, nullable=False)  # schema.entities.RelationshipType value
    source_document_id = Column(String, ForeignKey("source_documents.id"), nullable=True)
    weight = Column(Float, nullable=False, default=1.0)
