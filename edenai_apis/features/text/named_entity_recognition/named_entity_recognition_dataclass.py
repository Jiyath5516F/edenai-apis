from typing import Optional, Sequence

from pydantic import BaseModel, Field, StrictStr


class InfosNamedEntityRecognitionDataClass(BaseModel):
    entity: StrictStr
    category: StrictStr
    importance: Optional[float]
    url: Optional[StrictStr]


class NamedEntityRecognitionDataClass(BaseModel):
    items: Sequence[InfosNamedEntityRecognitionDataClass] = Field(default_factory=list)
