import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("owner", "name", "branch", name="uq_repositories_owner_name_branch"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    clone_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
