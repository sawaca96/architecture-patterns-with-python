import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import registry, relationship

from app import models

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
    sa.Column("sku", sa.String),
    sa.Column("purchased_quantity", sa.Integer),
    sa.Column("eta", sa.Date, nullable=True),
)

allocation_table = sa.Table(
    "allocation",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_line_id", sa.ForeignKey("order_line.id")),
    sa.Column("batch_id", sa.ForeignKey("batch.id")),
)


def start_mappers() -> None:
    line_mapper = mapper_registry.map_imperatively(models.OrderLine, order_line_table)
    mapper_registry.map_imperatively(
        models.Batch,
        batch_table,
        properties={
            "allocations": relationship(
                line_mapper, secondary=allocation_table, collection_class=set
            )
        },
    )
