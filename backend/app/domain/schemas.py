from typing import Optional

from pydantic import BaseModel, Field


class ShoppingListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ManualItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    barcode: Optional[str] = None
    quantity: int = Field(default=1, ge=1)


class ItemPatch(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=1)
    purchased: Optional[bool] = None
    brand: Optional[str] = None
    imageUrl: Optional[str] = None
    userEditedName: Optional[bool] = None


class EventMessage(BaseModel):
    type: str
    listId: str
    item: dict


class ScanIngestRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=512)
    listId: Optional[str] = None
