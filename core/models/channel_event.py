from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class ChannelEvent(Base):
    __tablename__ = "channel_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(32))  # "subscribed" | "unsubscribed"
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="channel_events")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ChannelEvent user_id={self.user_id} type={self.event_type}>"
