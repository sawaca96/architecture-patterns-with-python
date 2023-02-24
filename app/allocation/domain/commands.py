from dataclasses import dataclass
from datetime import date
from uuid import UUID


class Command:
    pass


@dataclass
class CreateBatch(Command):
    id: UUID
    sku: str
    qty: int
    eta: date = None


@dataclass
class ChangeBatchQuantity(Command):
    id: UUID
    qty: int


@dataclass
class Allocate(Command):
    order_id: UUID
    sku: str
    qty: int
