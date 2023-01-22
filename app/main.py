from uuid import UUID

from fastapi import Body, Depends, FastAPI, HTTPException

from app import models, services
from app.dependencies import repository
from app.repository import BatchAbstractRepository

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.post("/allocate", response_model=dict[str, str], status_code=201)
async def allocate(
    order_id: UUID = Body(),
    sku: str = Body(),
    quantity: int = Body(),
    repo: BatchAbstractRepository = Depends(repository),
) -> dict[str, str]:
    line = models.OrderLine(id=order_id, sku=sku, qty=quantity)
    try:
        batch_id = await services.allocate(line, repo)
    except (models.OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": str(batch_id)}
