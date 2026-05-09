from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


JSONDict = dict
JSONList = list
MaybeUUID = UUID | None
MaybeDateTime = datetime | None
MaybeDate = date | None
MaybeDecimal = Decimal | None
