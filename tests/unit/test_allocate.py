from datetime import date, timedelta

import pytest

from app.allocation.domain.models import Batch, OrderLine, OutOfStock, allocate


def test_perfers_current_stock_batches_to_allocate() -> None:
    # Given
    in_stock_batch = Batch(sku="RETRO-CLOCK", qty=100)
    shipment_batch = Batch(sku="RETRO-CLOCK", qty=100, eta=date.today() + timedelta(days=1))
    line = OrderLine(sku="RETRO-CLOCK", qty=10)

    # When
    allocate(line, [in_stock_batch, shipment_batch])

    # Then
    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    # Given
    earliest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today())
    medium = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=1))
    latest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=2))
    line = OrderLine(sku="MINIMALIST-SPOON", qty=10)

    # When
    allocate(line, [medium, earliest, latest])

    # Then
    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref() -> None:
    # Given
    in_stock_batch = Batch(sku="HIGHBROW-POSTER", qty=100)
    shipment_batch = Batch(sku="HIGHBROW-POSTER", qty=100, eta=date.today() + timedelta(days=1))
    line = OrderLine(sku="HIGHBROW-POSTER", qty=10)

    # When
    batch_id = allocate(line, [in_stock_batch, shipment_batch])

    # Then
    assert batch_id == in_stock_batch.id


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    # Given
    batch = Batch(sku="SMALL-FORK", qty=10)
    allocate(OrderLine(sku="SMALL-FORK", qty=10), [batch])

    # When & Then
    with pytest.raises(OutOfStock, match="SMALL-FORK"):
        allocate(OrderLine(sku="SMALL-FORK", qty=1), [batch])
