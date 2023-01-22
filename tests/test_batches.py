from uuid import uuid4

from app.models import Batch, OrderLine


def test_allocating_to_a_batch_reduces_available_quantity() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=10)

    # When
    batch.allocate(line)

    # Then
    assert batch.available_quantity == 0


def test_can_allocate_if_available_greater_than_required() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=1)

    # When
    can_allocate = batch.can_allocate(line)

    # Then
    assert can_allocate


def test_cannot_allocate_if_available_smaller_than_required() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 1, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=10)

    # When
    can_allocate = batch.can_allocate(line)

    # Then
    assert can_allocate is False


def test_can_allocate_if_available_equal_to_required() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 1, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=1)

    # When
    can_allocate = batch.can_allocate(line)

    # Then
    assert can_allocate


def test_cannot_allocate_if_skus_do_not_match() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="LARGE-FORK", qty=10)

    # When
    can_allocate = batch.can_allocate(line)

    # Then
    assert can_allocate is False


def test_allocation_is_idempotent() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=10)

    # When
    batch.allocate(line)
    # Then
    assert batch.available_quantity == 0

    # When
    batch.allocate(line)
    # Then
    assert batch.available_quantity == 0


def test_deallocate() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=10)

    # When
    batch.allocate(line)
    batch.deallocate(line)

    # Then
    assert batch.available_quantity == 10


def test_can_only_deallocate_allocated_lines() -> None:
    # Given
    batch = Batch(uuid4(), "SMALL-FORK", 10, eta=None)
    line = OrderLine(id=uuid4(), sku="SMALL-FORK", qty=10)

    # When
    batch.deallocate(line)

    # Then
    assert batch.available_quantity == 10
