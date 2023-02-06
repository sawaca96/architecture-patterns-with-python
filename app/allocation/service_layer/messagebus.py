from app.allocation.adapters import email
from app.allocation.domain import events


async def handle(event: events.Event) -> None:
    if isinstance(event, events.OutOfStock):
        await send_out_of_stock_notification(event)
    else:
        raise Exception(f"Unknown event {event}")


async def send_out_of_stock_notification(event: events.OutOfStock) -> None:
    email.send_mail("stock@made.com", f"Out of stock for {event.sku}")


HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
}
