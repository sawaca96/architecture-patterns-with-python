from typing import Any

from app.allocation.domain import commands
from app.allocation.service_layer import handlers, unit_of_work


async def handle(
    message: commands.Command,
    uow: unit_of_work.AbstractUnitOfWork[unit_of_work.AbstractProductRepository],
) -> list[Any]:
    results: list[Any] = []
    messages = [message]
    while messages:
        message = messages.pop(0)
        if isinstance(message, commands.CreateBatch):
            results.append(await handlers.CreateBatchCmdHandler(uow).handle(message))
        elif isinstance(message, commands.Allocate):
            results.append(await handlers.AllocateCmdHandler(uow).handle(message))
        elif isinstance(message, commands.ChangeBatchQuantity):
            messages.extend(await handlers.ChangeBatchQuantityCmdHandler(uow).handle(message))
        else:
            raise Exception(f"Unknown message {message}")
    return results
