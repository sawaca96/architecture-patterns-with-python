from datetime import date
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters import dao
from app.allocation.adapters.dto import Allocation
from app.allocation.adapters.orm import start_mappers
from app.allocation.domain import commands
from app.allocation.entrypoints.dependencies import batch_uow, session
from app.allocation.service_layer import handlers
from app.allocation.service_layer.handlers import InvalidSku
from app.allocation.service_layer.unit_of_work import AbstractUnitOfWork

app = FastAPI()
start_mappers()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.post("/batches", status_code=201)
async def add_batch(
    sku: str = Body(),
    quantity: int = Body(),
    eta: date = Body(default=None),
    uow: AbstractUnitOfWork = Depends(batch_uow),
) -> dict[str, str]:
    cmd = commands.CreateBatch(uuid4(), sku, quantity, eta)
    await handlers.CreateBatchCmdHandler(uow).handle(cmd)
    return {"batch_id": str(cmd.id)}


@app.post("/allocate", response_model=dict[str, str], status_code=201)
async def allocate(
    sku: str = Body(),
    quantity: int = Body(),
    uow: AbstractUnitOfWork = Depends(batch_uow),
) -> dict[str, str]:
    try:
        cmd = commands.Allocate(uuid4(), sku, quantity)
        batch_id = await handlers.AllocateCmdHandler(uow).handle(cmd)
    except InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": str(batch_id)}


@app.get("/allocations/{sku}", status_code=200)
async def allocations_view_endpoint(sku: str, session: AsyncSession = Depends(session)) -> list[Allocation]:
    result = await dao.allocations(sku, session)
    if not result:
        raise HTTPException(status_code=404, detail="not found")
    return result
