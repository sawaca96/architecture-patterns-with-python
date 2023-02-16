from datetime import date, timedelta
from uuid import UUID

from app.allocation.domain import events
from app.allocation.domain.events import OutOfStock
from app.allocation.domain.models import Batch, OrderLine, Product


def test_perfers_none_eta_batches_to_allocate() -> None:
    # Given
    in_stock_batch = Batch(sku="RETRO-CLOCK", qty=100)
    shipment_batch = Batch(sku="RETRO-CLOCK", qty=100, eta=date.today() + timedelta(days=1))
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine(sku="RETRO-CLOCK", qty=10)

    # When
    product.allocate(line)

    # Then
    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    # Given
    earliest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today())
    medium = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=1))
    latest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=2))
    product = Product(sku="MINIMALIST-SPOON", batches=[earliest, medium, latest])
    line = OrderLine(sku="MINIMALIST-SPOON", qty=10)

    # When
    product.allocate(line)

    # Then
    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_allocate_returns_allocated_batch_id() -> None:
    # Given
    in_stock_batch = Batch(sku="HIGHBROW-POSTER", qty=100)
    shipment_batch = Batch(sku="HIGHBROW-POSTER", qty=100, eta=date.today() + timedelta(days=1))
    product = Product(sku="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch])
    line = OrderLine(sku="HIGHBROW-POSTER", qty=10)

    # When
    batch_id = product.allocate(line)

    # Then
    assert batch_id == in_stock_batch.id


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    # Given
    batch = Batch(sku="SMALL-FORK", qty=10)
    product = Product(sku="SMALL-FORK", batches=[batch])
    product.allocate(OrderLine(sku="SMALL-FORK", qty=10))

    # When & Then
    allocation = product.allocate(OrderLine(sku="SMALL-FORK", qty=1))
    assert product.events[-1] == OutOfStock(sku="SMALL-FORK")
    assert allocation is None


def test_increment_version_number() -> None:
    # Given
    line = OrderLine(sku="HIGHBROW-POSTER", qty=10)
    batch = Batch(sku="HIGHBROW-POSTER", qty=100)
    product = Product(sku="HIGHBROW-POSTER", batches=[batch])
    product.version_number = 7

    # When
    product.allocate(line)

    # Then
    assert product.version_number == 8


def test_outputs_allocated_event() -> None:
    # Given
    batch = Batch(id=UUID("77ff6655-1a8d-477d-9daf-dfd339d309c5"), sku="RETRO-LAMPSHADE", qty=100)
    line = OrderLine(id=UUID("60f44705-15f6-44e7-947f-302109d8cd99"), sku="RETRO-LAMPSHADE", qty=10)
    product = Product(sku="RETRO-LAMPSHADE", batches=[batch])

    # When
    product.allocate(line)

    # Then
    expected = events.Allocated(
        order_id=UUID("60f44705-15f6-44e7-947f-302109d8cd99"),
        sku="RETRO-LAMPSHADE",
        qty=10,
        batch_id=UUID("77ff6655-1a8d-477d-9daf-dfd339d309c5"),
    )
    assert product.events[-1] == expected
