# database/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True)

    title = Column(String(500))
    content = Column(Text)

    source_type = Column(String(50))
    source_name = Column(String(200))
    source_id = Column(String(200))
    source_url = Column(Text)

    evidence_class = Column(String(30))

    asset = Column(String(200))
    indication = Column(String(200))
    biomarker = Column(String(200))

    publication_date = Column(String(50))
    retrieved_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    verified = Column(Integer, default=0)


class FieldInsight(Base):
    __tablename__ = "field_insights"

    id = Column(Integer, primary_key=True)

    text = Column(Text)
    theme = Column(String(100))

    asset = Column(String(200))
    indication = Column(String(200))

    source_status = Column(
        String(30),
        default="FIELD_SIGNAL"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class PatientSignal(Base):
    __tablename__ = "patient_signals"

    id = Column(Integer, primary_key=True)

    text = Column(Text)
    theme = Column(String(100))

    source = Column(String(100))
    source_url = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class EvidenceGap(Base):
    __tablename__ = "evidence_gaps"

    id = Column(Integer, primary_key=True)

    topic = Column(String(200))

    evidence_signal = Column(Text)
    hcp_signal = Column(Text)
    patient_signal = Column(Text)

    hypothesis = Column(Text)

    confidence = Column(Float)

    status = Column(
        String(30),
        default="AI_DERIVED"
    )