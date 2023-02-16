from typing import Any

from app.allocation.domain import commands, events
from app.allocation.service_layer import handlers, unit_of_work

Message = commands.Command | events.Event


async def handle(
    message: Message,
    uow: unit_of_work.AbstractUnitOfWork[unit_of_work.AbstractProductRepository],
) -> list[Any]:
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        result = None
        if isinstance(message, events.Event):
            await handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            result = await handle_command(message, queue, uow)
            results.append(result)
        else:
            raise Exception(f"Unknown message {message}")
    return results


async def handle_event(
    event: events.Event,
    queue: list[Message],
    uow: unit_of_work.AbstractUnitOfWork[unit_of_work.AbstractProductRepository],
) -> None:
    try:
        if isinstance(event, events.OutOfStock):
            handlers.send_out_of_stock_notification(event)
        elif isinstance(event, events.Allocated):
            await handlers.publish_allocated_event(event)
        queue.extend(uow.collect_new_events())
    except Exception:
        return


async def handle_command(
    command: commands.Command,
    queue: list[Message],
    uow: unit_of_work.AbstractUnitOfWork[unit_of_work.AbstractProductRepository],
) -> Any:
    try:
        result = None
        if isinstance(command, commands.CreateBatch):
            await handlers.add_batch(command, uow)
        elif isinstance(command, commands.ChangeBatchQuantity):
            await handlers.change_batch_quantity(command, uow)
        elif isinstance(command, commands.Allocate):
            result = await handlers.allocate(command, uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        raise
