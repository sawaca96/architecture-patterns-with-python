from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4


class OutOfStock(Exception):
    pass


def allocate(line: OrderLine, batches: list[Batch]) -> UUID:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
        return batch.id
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")


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

    def deallocate(self, line: OrderLine) -> None:
        if line in self.allocations:
            self.allocations.remove(line)

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