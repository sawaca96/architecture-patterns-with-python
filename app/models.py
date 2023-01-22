from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


class OutOfStock(Exception):
    pass


def allocate(line: OrderLine, batches: list[Batch]) -> UUID:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
        return batch.id
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")


@dataclass(unsafe_hash=True, kw_only=True)  # TODO: kw_only를 언제 써야 할까?
class OrderLine:
    id: UUID
    sku: str
    qty: int


class Batch:
    def __init__(self, id: UUID, sku: str, qty: int, eta: date | None) -> None:
        # TODO: id 값 업으면 기본 값 채우기
        self.id = id
        self.sku = sku
        self.eta = eta
        self.purchased_quantity = qty
        self.allocations: set[OrderLine] = set()

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
        return self.purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return (
            self.sku == line.sku
            and self.available_quantity >= line.qty
            and line not in self.allocations
        )
