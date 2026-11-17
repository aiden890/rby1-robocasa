"""Three lab-assistant demo tasks (261117 scenario deck) as thin subclasses of RoboCasa tasks.

Only object groups, language and the extra objects change; scene setup, placement and the
base success checks come from the RoboCasa parents.
"""
from robocasa.environments.kitchen.composite.clearing_table.food_cleanup import FoodCleanup
from robocasa.environments.kitchen.composite.defrosting_food.move_to_counter import MoveToCounter
from robocasa.environments.kitchen.composite.snack_preparation.make_fruit_bowl import MakeFruitBowl
import robocasa.utils.object_utils as OU

# graspable snack-like categories (RoboCasa marks chips bags and chocolate as not graspable)
SNACKS = ("bar", "donut", "cupcake")  # candy is aigen-only (not in the default registries)


class TidyDesk(FoodCleanup):
    """"책상 좀 치워줘" — FoodCleanup (counter items into the cabinet, then close it) with
    book = boxed_food -> shelf (cabinet), plus pen (straw) -> pen holder (mug) and
    snack bar wrapper (bar) -> bin (basket) on the same counter."""

    def _setup_kitchen_references(self):
        super()._setup_kitchen_references()
        self.num_food = 1  # the book

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = (
            "Tidy the desk: put the pen in the pen holder, throw the snack bag in the bin, "
            "and put the book on the shelf. Then close the shelf."
        )
        return ep_meta

    def _get_obj_cfgs(self):
        cfgs = super()._get_obj_cfgs()
        cfgs[0]["obj_groups"] = "boxed_food"
        near = lambda pos, size=(0.30, 0.30): dict(
            fixture=self.counter, sample_region_kwargs=dict(ref=self.cab), size=size, pos=pos)
        cfgs += [
            dict(name="pen", obj_groups="straw", graspable=True, placement=near(("ref", -1.0))),
            dict(name="pen_holder", obj_groups="mug", placement=near((-1.0, -1.0))),
            dict(name="snack_bag", obj_groups="bar", graspable=True, placement=near(("ref", -1.0))),
            dict(name="bin", obj_groups="basket", placement=near((1.0, -1.0), (0.35, 0.35))),
        ]
        return cfgs

    def _check_success(self):
        return (
            super()._check_success()
            and OU.check_obj_in_receptacle(self, "pen", "pen_holder")
            and OU.check_obj_in_receptacle(self, "snack_bag", "bin")
            and OU.gripper_obj_far(self, "pen")
            and OU.gripper_obj_far(self, "snack_bag")
        )


class FetchColaFromFridge(MoveToCounter):
    """"냉장고에서 콜라 하나 갖다줘" — MoveToCounter (fridge item onto a plate on the counter)
    with the item a can. The plate is the hand-over spot. fridge_open=False starts with the
    door closed so opening is part of the task."""

    def __init__(self, *args, fridge_open=True, **kwargs):
        self.fridge_open = fridge_open
        super().__init__(*args, **kwargs)

    def _setup_scene(self):
        super()._setup_scene()  # opens the door
        if not self.fridge_open:
            self.fridge.close_door(env=self)

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = "Bring me a can of cola from the fridge and put it on the plate."
        return ep_meta

    def _get_obj_cfgs(self):
        cfgs = super()._get_obj_cfgs()
        for c in cfgs:
            if c["name"] == "frosted_food":  # parent's name kept so its success check applies
                c["obj_groups"] = "can"
            elif c["name"] == "distractor_obj":
                c["obj_groups"] = ("yogurt", "boxed_drink")
                c.pop("exclude_obj_groups", None)
        return cfgs


class RefillSnackBasket(MakeFruitBowl):
    """"간식 바구니 채워줘" — MakeFruitBowl (cabinet items into a bowl, close the cabinet) with
    bowl = basket and fruit = snacks; the cabinet is the snack box."""

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = (
            "Open the cabinet, take the snacks out and put them in the snack basket. "
            "Then close the cabinet."
        )
        return ep_meta

    def _get_obj_cfgs(self):
        cfgs = super()._get_obj_cfgs()
        for c in cfgs:
            if c["name"] == "bowl":
                c["obj_groups"] = "basket"
                c.pop("graspable", None)  # baskets are not graspable in RoboCasa
            elif c["name"] in ("fruit1", "fruit2"):
                c["obj_groups"] = SNACKS
        return cfgs
