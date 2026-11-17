"""Lab-assistant tasks: thin subclasses of RoboCasa tasks (importing registers them).

Lab objects map to RoboCasa categories until lab assets are added:
desk = counter, bookshelf = cabinet, book = boxed_food, pen = straw, pen holder = mug,
snack wrapper = bar, snacks = bar/donut/cupcake,
trash bin / snack basket = basket, cola = can, hand-over spot = plate on the counter.
"""
from rby1_sim.tasks.lab_assistant import FetchColaFromFridge, RefillSnackBasket, TidyDesk  # noqa: F401

TASKS = {
    "tidy_desk": "TidyDesk",
    "fetch_cola": "FetchColaFromFridge",
    "refill_snacks": "RefillSnackBasket",
}
