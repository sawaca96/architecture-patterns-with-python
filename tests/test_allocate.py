from datetime import date, timedelta

import pytest

from app.model import Batch, OrderLine, OutOfStock, allocate


def test_perfers_current_stock_batches_to_shipments() -> None:
    # Given
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch(
        "shipment-batch", "RETRO-CLOCK", 100, eta=date.today() + timedelta(days=1)
    )
    line = OrderLine("order1", "RETRO-CLOCK", 10)

    # When
    allocate(line, [in_stock_batch, shipment_batch])

    # Then
    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    # Given
    earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=date.today())
    medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=date.today() + timedelta(days=1))
    latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=date.today() + timedelta(days=2))
    line = OrderLine("order1", "MINIMALIST-SPOON", 10)

    # When
    allocate(line, [medium, earliest, latest])

    # Then
    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref() -> None:
    # Given
    in_stock_batch = Batch("in-stock-batch-ref", "HIGHBROW-POSTER", 100, eta=None)
    shipment_batch = Batch(
        "shipment-batch-ref", "HIGHBROW-POSTER", 100, eta=date.today() + timedelta(days=1)
    )
    line = OrderLine("order1", "HIGHBROW-POSTER", 10)

    # When
    allocation = allocate(line, [in_stock_batch, shipment_batch])

    # Then
    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    # Given
    batch = Batch("batch1", "SMALL-FORK", 10, eta=None)
    allocate(OrderLine("order1", "SMALL-FORK", 10), [batch])

    # When & Then
    with pytest.raises(OutOfStock, match="SMALL-FORK"):
        allocate(OrderLine("order2", "SMALL-FORK", 1), [batch])
