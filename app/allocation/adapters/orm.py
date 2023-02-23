import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import registry, relationship

from app.allocation.domain import models

mapper_registry = registry()
metadata = mapper_registry.metadata

order_table = sa.Table(
    "order",
    metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("sku", sa.String),
    sa.Column("qty", sa.Integer),
)

batch_table = sa.Table(
    "batch",
    metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("sku", sa.ForeignKey("product.sku")),
    sa.Column("qty", sa.Integer),
    sa.Column("eta", sa.Date, nullable=True),
)

allocation_table = sa.Table(
    "allocation",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_id", sa.ForeignKey("order.id")),
    sa.Column("batch_id", sa.ForeignKey("batch.id")),
    sa.UniqueConstraint("order_id", "batch_id"),
)

product_table = sa.Table(
    "product",
    metadata,
    sa.Column("sku", sa.String, primary_key=True),
    sa.Column("version_number", sa.Integer, nullable=False, server_default="0"),
)

allocations_view = sa.Table(
    "allocations_view",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_id", UUID),
    sa.Column("sku", sa.String(255)),
    sa.Column("batch_id", UUID),
    sa.UniqueConstraint("order_id", "batch_id"),
)


def start_mappers() -> None:
    order_mapper = mapper_registry.map_imperatively(models.Order, order_table)
    batches_mapper = mapper_registry.map_imperatively(
        models.Batch,
        batch_table,
        properties={"allocations": relationship(order_mapper, secondary=allocation_table, collection_class=set)},
    )
    mapper_registry.map_imperatively(
        models.Product,
        product_table,
        properties={"batches": relationship(batches_mapper)},
        version_id_col=product_table.c.version_number,
    )
