from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4


@dataclass(unsafe_hash=True, kw_only=True)
class Order:
    id: UUID = field(default_factory=uuid4)
    sku: str
    qty: int


@dataclass(kw_only=True)
class Batch:
    id: UUID = field(default_factory=uuid4)
    sku: str
    eta: date = None
    qty: int
    allocations: set[Order] = field(default_factory=lambda: set())

    def __repr__(self) -> str:
        return f"<Batch {self.id}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Batch):
            return False
        return other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __gt__(self, other: Batch) -> bool:
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def allocate(self, order: Order) -> None:
        if self.can_allocate(order):
            self.allocations.add(order)

    def deallocate_one(self) -> Order:
        return self.allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(order.qty for order in self.allocations)

    @property
    def available_quantity(self) -> int:
        return self.qty - self.allocated_quantity

    def can_allocate(self, order: Order) -> bool:
        return self.sku == order.sku and self.available_quantity >= order.qty and order not in self.allocations


@dataclass(kw_only=True)
class Product:
    sku: str
    batches: list[Batch]
    version_number: int = 0

    def allocate(self, order: Order) -> UUID:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(order))
            batch.allocate(order)
            self.version_number += 1
            return batch.id
        except StopIteration:
            return None

    def change_batch_quantity(self, id: UUID, qty: int) -> list[Order]:
        batch = next(b for b in self.batches if b.id == id)
        batch.qty = qty
        deallocated_orders = []
        while batch.available_quantity < 0:
            order = batch.deallocate_one()
            deallocated_orders.append(order)
        return deallocated_orders

    def __hash__(self) -> int:
        return hash(self.sku)
