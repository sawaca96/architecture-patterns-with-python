from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from app.allocation.domain import commands, events


@dataclass(unsafe_hash=True, kw_only=True)
class OrderLine:
    id: UUID = field(default_factory=uuid4)
    sku: str
    qty: int


@dataclass(kw_only=True)
class Batch:
    id: UUID = field(default_factory=uuid4)
    sku: str
    eta: date = None
    qty: int
    allocations: set[OrderLine] = field(default_factory=lambda: set())

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

    def allocate(self, line: OrderLine) -> None:
        if self.can_allocate(line):
            self.allocations.add(line)

    def deallocate_one(self) -> OrderLine:
        return self.allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self.allocations)

    @property
    def available_quantity(self) -> int:
        return self.qty - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return (
            self.sku == line.sku
            and self.available_quantity >= line.qty
            and line not in self.allocations
        )


@dataclass(kw_only=True)
class Product:
    sku: str
    batches: list[Batch]
    version_number: int = 0
    events: list[events.Event | commands.Command] = field(default_factory=lambda: [])

    def allocate(self, line: OrderLine) -> UUID:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            return batch.id
        except StopIteration:
            self.events.append(events.OutOfStock(sku=line.sku))
            return None

    def change_batch_quantity(self, id: UUID, qty: int) -> None:
        batch = next(b for b in self.batches if b.id == id)
        batch.qty = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(commands.Allocate(line.id, line.sku, line.qty))

    def __hash__(self) -> int:
        return hash(self.sku)
