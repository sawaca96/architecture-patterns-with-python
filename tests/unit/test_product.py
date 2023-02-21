from datetime import date, timedelta

from app.allocation.domain.models import Batch, Order, Product


def test_perfers_none_eta_batches_to_allocate() -> None:
    # Given
    in_stock_batch = Batch(sku="RETRO-CLOCK", qty=100)
    shipment_batch = Batch(sku="RETRO-CLOCK", qty=100, eta=date.today() + timedelta(days=1))
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    order = Order(sku="RETRO-CLOCK", qty=10)

    # When
    product.allocate(order)

    # Then
    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    # Given
    earliest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today())
    medium = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=1))
    latest = Batch(sku="MINIMALIST-SPOON", qty=100, eta=date.today() + timedelta(days=2))
    product = Product(sku="MINIMALIST-SPOON", batches=[earliest, medium, latest])
    order = Order(sku="MINIMALIST-SPOON", qty=10)

    # When
    product.allocate(order)

    # Then
    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_allocate_returns_allocated_batch_id() -> None:
    # Given
    in_stock_batch = Batch(sku="HIGHBROW-POSTER", qty=100)
    shipment_batch = Batch(sku="HIGHBROW-POSTER", qty=100, eta=date.today() + timedelta(days=1))
    product = Product(sku="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch])
    order = Order(sku="HIGHBROW-POSTER", qty=10)

    # When
    batch_id = product.allocate(order)

    # Then
    assert batch_id == in_stock_batch.id


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    # Given
    batch = Batch(sku="SMALL-FORK", qty=10)
    product = Product(sku="SMALL-FORK", batches=[batch])
    product.allocate(Order(sku="SMALL-FORK", qty=10))

    # When & Then
    allocation = product.allocate(Order(sku="SMALL-FORK", qty=1))
    assert allocation is None


def test_increment_version_number() -> None:
    # Given
    order = Order(sku="HIGHBROW-POSTER", qty=10)
    batch = Batch(sku="HIGHBROW-POSTER", qty=100)
    product = Product(sku="HIGHBROW-POSTER", batches=[batch])
    product.version_number = 7

    # When
    product.allocate(order)

    # Then
    assert product.version_number == 8
