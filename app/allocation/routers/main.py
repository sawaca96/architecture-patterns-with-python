from datetime import date
from uuid import UUID

from fastapi import Body, Depends, FastAPI, HTTPException

from app.allocation.adapters.repository import AbstractProductRepository
from app.allocation.domain import events
from app.allocation.routers.dependencies import batch_uow
from app.allocation.service_layer import messagebus
from app.allocation.service_layer.handlers import InvalidSku
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
    uow: AbstractUnitOfWork[AbstractProductRepository] = Depends(batch_uow),
) -> dict[str, str]:
    event = events.BatchCreated(batch_id, sku, quantity, eta)
    await messagebus.handle(event, uow)
    return {"message": "success"}


@app.post("/allocate", response_model=dict[str, str], status_code=201)
async def allocate(
    line_id: UUID = Body(),
    sku: str = Body(),
    quantity: int = Body(),
    uow: AbstractUnitOfWork[AbstractProductRepository] = Depends(batch_uow),
) -> dict[str, str]:
    try:
        event = events.AllocationRequired(line_id, sku, quantity)
        results = await messagebus.handle(event, uow)
        batch_id = results[0]
    except InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": str(batch_id)}
