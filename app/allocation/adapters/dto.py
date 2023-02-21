from uuid import UUID

from pydantic import BaseModel


class Allocation(BaseModel):
    order_id: UUID
    sku: str
    qty: int
    batch_id: UUID
