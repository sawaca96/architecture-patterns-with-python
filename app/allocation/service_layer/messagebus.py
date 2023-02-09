from typing import Any

from app.allocation.domain import events
from app.allocation.service_layer import handlers, unit_of_work


# TODO: 이렇게 하는거 맞나?
async def handle(
    event: events.Event,
    uow: unit_of_work.AbstractUnitOfWork[unit_of_work.AbstractProductRepository],
) -> list[Any]:
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        result = None
        if isinstance(event, events.OutOfStock):
            handlers.send_out_of_stock_notification(event, uow)
        elif isinstance(event, events.BatchQuantityChanged):
            await handlers.change_batch_quantity(event, uow)
        elif isinstance(event, events.AllocationRequired):
            result = await handlers.allocate(event, uow)
        elif isinstance(event, events.BatchCreated):
            await handlers.add_batch(event, uow)
        else:
            raise Exception(f"Unknown event {event}")
        if result:
            results.append(result)
        queue.extend(uow.collect_new_events())
    return results
