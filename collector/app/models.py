from datetime import datetime
from typing import Any, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TraceModel(Base):
    __tablename__ = "traces"

    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OK")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    spans: Mapped[list["SpanModel"]] = relationship(
        "SpanModel", back_populates="trace", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["EvaluationModel"]] = relationship(
        "EvaluationModel", back_populates="trace", cascade="all, delete-orphan"
    )


class SpanModel(Base):
    __tablename__ = "spans"

    span_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    trace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("traces.trace_id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    span_type: Mapped[str] = mapped_column(String(64), nullable=False, default="agent")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OK")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    trace: Mapped["TraceModel"] = relationship("TraceModel", back_populates="spans")


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    eval_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    trace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("traces.trace_id", ondelete="CASCADE"), index=True, nullable=False
    )
    eval_type: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PASS")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    trace: Mapped["TraceModel"] = relationship("TraceModel", back_populates="evaluations")



__table_args__ = (
    Index("idx_spans_trace_parent", "trace_id", "parent_span_id"),
)
