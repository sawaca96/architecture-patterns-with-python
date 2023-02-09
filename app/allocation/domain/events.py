from dataclasses import dataclass
from datetime import date
from uuid import UUID


class Event:
    pass


@dataclass
class BatchCreated(Event):
    id: UUID
    sku: str
    qty: int
    eta: date = None


@dataclass
class BatchQuantityChanged(Event):
    id: UUID
    qty: int


@dataclass
class AllocationRequired(Event):
    order_id: UUID
    sku: str
    qty: int


@dataclass
class OutOfStock(Event):
    sku: str
