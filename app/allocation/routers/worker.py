import asyncio
from uuid import UUID

import orjson

from app.allocation.adapters.orm import start_mappers
from app.allocation.adapters.redis import redis
from app.allocation.constants import BATCH_QUANTITY_CHANGED_CHANNEL
from app.allocation.domain import commands
from app.allocation.service_layer import messagebus, unit_of_work

start_mappers()


async def main() -> None:
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(BATCH_QUANTITY_CHANGED_CHANNEL)

    async for m in pubsub.listen():
        channel = m["channel"].decode("utf-8")
        data = orjson.loads(m["data"])
        if channel == BATCH_QUANTITY_CHANGED_CHANNEL:
            await messagebus.handle(
                commands.ChangeBatchQuantity(id=UUID(data["id"]), qty=data["qty"]),
                uow=unit_of_work.ProductUnitOfWork(),
            )


if __name__ == "__main__":
    asyncio.run(main())
