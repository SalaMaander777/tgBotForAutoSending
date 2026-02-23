from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Setting key={self.key}>"
