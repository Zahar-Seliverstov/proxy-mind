from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Prompt(Base):
    """Системный промпт (инструкция) для локальной AI-модели.

    editable=True  — контентный промпт, пользователь может менять текст.
    editable=False — механический промпт, управляет форматом JSON-ответа модели.
    """

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format_hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    mode: Mapped["Mode | None"] = relationship(back_populates="prompt")


class Mode(Base):
    """Режим генерации. prompt_id ссылается на системный промпт (NULL у direct/manual)."""

    __tablename__ = "modes"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts.id"), nullable=True
    )

    prompt: Mapped["Prompt | None"] = relationship(back_populates="mode")


class Setting(Base):
    """Настройки приложения — ключ/значение."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
