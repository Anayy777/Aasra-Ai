from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import BigInteger, Date, DateTime, Integer, Text, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "whatsapp-service"))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from database import Base, SessionLocal, engine  # noqa: E402

DEFAULT_DATASET = Path(
    r"C:\Users\YUGAM AHUJA\Downloads\Qualifications 04-09-2026 09_46_59.xlsx"
)
SHEET_NAME = "Worksheet"
HEADER_ROW = 2

SOURCE_COLUMNS = [
    "S No.",
    "Title",
    "Code",
    "Description",
    "Sector Name",
    "Level",
    "Maximum Notational Hours",
    "Minimum Notational Hours",
    "Version",
    "Originally Approved",
    "Valid Till",
    "Awarding Body",
    "Certifying Bodies",
    "Proposed Occupation",
    "Progression Pathway",
    "Qualifcation Type",
    "Adopted Qualifcation",
    "Training Delivery Hours",
]

class NQRQualification(Base):
    __tablename__ = "nqr_qualifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    s_no: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sector_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    maximum_notational_hours: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_notational_hours: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    originally_approved: Mapped[date] = mapped_column(Date, nullable=False)
    valid_till: Mapped[date] = mapped_column(Date, nullable=False)
    awarding_body: Mapped[str] = mapped_column(Text, nullable=False)
    certifying_bodies: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_occupation: Mapped[str | None] = mapped_column(Text, nullable=True)
    progression_pathway: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualifcation_type: Mapped[str] = mapped_column(Text, nullable=False)
    adopted_qualifcation: Mapped[str] = mapped_column(Text, nullable=False)
    training_delivery_hours: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def _nullable_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return str(value)


def _required_text(value: Any, column: str) -> str:
    result = _nullable_text(value)
    if result is None or not result.strip():
        raise ValueError(f"{column} is required")
    return result


def _date_value(value: Any, column: str) -> date:
    if pd.isna(value):
        raise ValueError(f"{column} is required")
    parsed = pd.to_datetime(value, dayfirst=True, errors="raise")
    return parsed.date()


def _prepare_row(row: pd.Series) -> dict[str, Any]:
    return {
        "s_no": int(row["S No."]),
        "title": _required_text(row["Title"], "Title"),
        "code": _nullable_text(row["Code"]),
        "description": _required_text(row["Description"], "Description"),
        "sector_name": _nullable_text(row["Sector Name"]),
        "level": _required_text(row["Level"], "Level"),
        "maximum_notational_hours": _required_text(
            row["Maximum Notational Hours"], "Maximum Notational Hours"
        ),
        "minimum_notational_hours": _required_text(
            row["Minimum Notational Hours"], "Minimum Notational Hours"
        ),
        "version": _required_text(row["Version"], "Version"),
        "originally_approved": _date_value(
            row["Originally Approved"], "Originally Approved"
        ),
        "valid_till": _date_value(row["Valid Till"], "Valid Till"),
        "awarding_body": _required_text(row["Awarding Body"], "Awarding Body"),
        "certifying_bodies": _nullable_text(row["Certifying Bodies"]),
        "proposed_occupation": _nullable_text(row["Proposed Occupation"]),
        "progression_pathway": _nullable_text(row["Progression Pathway"]),
        "qualifcation_type": _required_text(
            row["Qualifcation Type"], "Qualifcation Type"
        ),
        "adopted_qualifcation": _required_text(
            row["Adopted Qualifcation"], "Adopted Qualifcation"
        ),
        "training_delivery_hours": _required_text(
            row["Training Delivery Hours"], "Training Delivery Hours"
        ),
    }


def load_source(path: Path) -> pd.DataFrame:
    dataframe = pd.read_excel(path, sheet_name=SHEET_NAME, header=HEADER_ROW)
    missing = set(SOURCE_COLUMNS) - set(dataframe.columns)
    if missing:
        raise ValueError(
            "Missing expected source columns: " + ", ".join(sorted(missing))
        )
    return dataframe[SOURCE_COLUMNS]


def import_nqr(path: Path = DEFAULT_DATASET) -> dict[str, int]:
    dataframe = load_source(path)
    source_rows = len(dataframe)
    rows: list[dict[str, Any]] = []
    failed_rows = 0

    for row_number, (_, row) in enumerate(dataframe.iterrows(), start=HEADER_ROW + 2):
        try:
            rows.append(_prepare_row(row))
        except (TypeError, ValueError, OverflowError):
            failed_rows += 1
            print(f"Failed source row: {row_number}")

    Base.metadata.create_all(bind=engine, tables=[NQRQualification.__table__])

    inserted_rows = 0
    with SessionLocal.begin() as db:
        if rows:
            statement = insert(NQRQualification).values(rows)
            statement = statement.on_conflict_do_nothing(
                index_elements=[NQRQualification.s_no]
            )
            result = db.execute(statement.returning(NQRQualification.s_no))
            inserted_rows = len(result.fetchall())

        final_count = db.scalar(select(func.count()).select_from(NQRQualification))

    skipped_rows = source_rows - failed_rows - inserted_rows
    return {
        "source_rows": source_rows,
        "inserted_rows": inserted_rows,
        "skipped_rows": skipped_rows,
        "failed_rows": failed_rows,
        "final_count": final_count or 0,
    }


def main() -> None:
    dataset = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    statistics = import_nqr(dataset)
    print(f"Source rows: {statistics['source_rows']}")
    print(f"Inserted rows: {statistics['inserted_rows']}")
    print(f"Skipped/already-existing rows: {statistics['skipped_rows']}")
    print(f"Failed rows: {statistics['failed_rows']}")
    print(f"Final row count: {statistics['final_count']}")


if __name__ == "__main__":
    main()
