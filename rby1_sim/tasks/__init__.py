"""Lab-assistant tasks built on RoboCasa kitchens (importing registers them with robosuite).

Lab objects are mapped to RoboCasa categories/fixtures until lab assets are added:
desk = dining counter, pen = straw, pen holder = mug, book = boxed_food, bookshelf = cabinet,
trash bin / snack basket = basket, cola = can, sofa side = dining counter.
"""
from rby1_sim.tasks.lab_assistant import FetchColaFromFridge, RefillSnackBasket, TidyDesk  # noqa: F401

TASKS = {
    "tidy_desk": "TidyDesk",
    "fetch_cola": "FetchColaFromFridge",
    "refill_snacks": "RefillSnackBasket",
}
