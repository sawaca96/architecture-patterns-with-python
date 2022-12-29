import sqlalchemy as sa
from sqlalchemy.orm import registry, relationship

from app import models

mapper_registry = registry()
metadata = mapper_registry.metadata

orderline_table = sa.Table(
    "orderline",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("sku", sa.String),
    sa.Column("qty", sa.Integer),
    sa.Column("reference", sa.String),
)

batch_table = sa.Table(
    "batch",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("reference", sa.String),
    sa.Column("sku", sa.String),
    sa.Column("purchased_quantity", sa.Integer),
    sa.Column("eta", sa.Date, nullable=True),
)

allocation_table = sa.Table(
    "allocation",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("orderline_id", sa.ForeignKey("orderline.id")),
    sa.Column("batch_id", sa.ForeignKey("batch.id")),
)


def start_mappers() -> None:
    line_mapper = mapper_registry.map_imperatively(models.Orderline, orderline_table)
    mapper_registry.map_imperatively(
        models.Batch,
        batch_table,
        properties={
            "_allocations": relationship(
                line_mapper, secondary=allocation_table, collection_class=set
            )
        },
    )
