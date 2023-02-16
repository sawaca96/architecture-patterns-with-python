from dataclasses import dataclass
from uuid import UUID


class Event:
    pass


@dataclass
class Allocated(Event):
    order_id: UUID
    sku: str
    qty: int
    batch_id: UUID


@dataclass
class OutOfStock(Event):
    sku: str
