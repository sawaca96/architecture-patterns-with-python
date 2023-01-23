from datetime import date
from uuid import UUID

from fastapi import Body, Depends, FastAPI, HTTPException

from app.allocation.adapters.repository import AbstractBatchRepository
from app.allocation.domain import models
from app.allocation.routers.dependencies import batch_uow
from app.allocation.service_layer import services
from app.allocation.service_layer.unit_of_work import AbstractUnitOfWork

app = FastAPI()
# start_mappers() # TODO: 운영환경에서는 실행되어야 함


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.post("/batches", status_code=201)
async def add_batch(
    batch_id: UUID = Body(),
    sku: str = Body(),
    quantity: int = Body(),
    eta: date = Body(default=None),
    uow: AbstractUnitOfWork[AbstractBatchRepository] = Depends(batch_uow),
) -> dict[str, str]:
    await services.add_batch(batch_id, sku, quantity, eta, uow)
    return {"message": "success"}


@app.post("/allocate", response_model=dict[str, str], status_code=201)
async def allocate(
    line_id: UUID = Body(),
    sku: str = Body(),
    quantity: int = Body(),
    uow: AbstractUnitOfWork[AbstractBatchRepository] = Depends(batch_uow),
) -> dict[str, str]:
    try:
        batch_id = await services.allocate(line_id, sku, quantity, uow)
    except (models.OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": str(batch_id)}