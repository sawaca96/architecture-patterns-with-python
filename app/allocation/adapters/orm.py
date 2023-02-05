import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.event import listens_for
from sqlalchemy.orm import QueryContext, registry, relationship

from app.allocation.domain import models

mapper_registry = registry()
metadata = mapper_registry.metadata

order_line_table = sa.Table(
    "order_line",
    metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("sku", sa.String),
    sa.Column("qty", sa.Integer),
)

batch_table = sa.Table(
    "batch",
    metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("sku", sa.ForeignKey("products.sku")),
    sa.Column("qty", sa.Integer),
    sa.Column("eta", sa.Date, nullable=True),
)

allocation_table = sa.Table(
    "allocation",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_line_id", sa.ForeignKey("order_line.id")),
    sa.Column("batch_id", sa.ForeignKey("batch.id")),
)

products = sa.Table(
    "products",
    metadata,
    sa.Column("sku", sa.String, primary_key=True),
    sa.Column("version_number", sa.Integer, nullable=False, server_default="0"),
)


def start_mappers() -> None:
    line_mapper = mapper_registry.map_imperatively(models.OrderLine, order_line_table)
    batches_mapper = mapper_registry.map_imperatively(
        models.Batch,
        batch_table,
        properties={
            "allocations": relationship(
                line_mapper, secondary=allocation_table, collection_class=set
            )
        },
    )
    mapper_registry.map_imperatively(
        models.Product,
        products,
        properties={"batches": relationship(batches_mapper)},
        version_id_col=products.c.version_number,
    )


@listens_for(models.Product, "load")  # type: ignore
def receive_load(product: models.Product, context: QueryContext) -> None:
    product.events = list()
