from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (PrimaryKeyConstraint("telegram_id", "bot_token"),)

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bot_token: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} username={self.username}>"
