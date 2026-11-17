"""Three lab-assistant demo tasks (261117 scenario deck) as RoboCasa Kitchen environments.

Every task exposes `subtasks`: the ordered decomposition used by the skill layer
(base: navigate, torso: posture, arm: pick/place/open), so scripted demos, CaP plans and
learned skills share one structure.
"""
import numpy as np

from robocasa.environments.kitchen.kitchen import Kitchen, FixtureType
import robocasa.utils.object_utils as OU


class _LabTask(Kitchen):
    """Common helpers. Subclasses define `subtasks()` and `_check_success()`."""

    def subtasks(self):
        raise NotImplementedError

    def _all_far(self, names, th=0.15):
        return all(OU.gripper_obj_far(self, obj_name=n, th=th) for n in names)

    def _in(self, obj, receptacle):
        return OU.check_obj_in_receptacle(self, obj, receptacle)


class TidyDesk(_LabTask):
    """"책상 좀 치워줘": pen into the pen holder, book onto the shelf, snack bag into the bin.

    desk = dining counter, pen = straw, pen holder = mug, book = boxed_food,
    bookshelf = cabinet next to the desk (door opened at reset), trash bin = basket.
    """

    EXCLUDE_LAYOUTS = Kitchen.DINING_COUNTER_EXCLUDED_LAYOUTS

    def _setup_kitchen_references(self):
        super()._setup_kitchen_references()
        self.desk = self.register_fixture_ref("desk", dict(id=FixtureType.DINING_COUNTER))
        self.shelf = self.register_fixture_ref("shelf", dict(id=FixtureType.CABINET_WITH_DOOR))
        self.shelf_counter = self.register_fixture_ref("shelf_counter", dict(id=FixtureType.COUNTER, ref=self.shelf))
        self.init_robot_base_ref = self.desk

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = (
            "Tidy the desk: put the pen in the pen holder, put the book on the shelf, "
            "and throw the snack bag in the bin."
        )
        return ep_meta

    def _setup_scene(self):
        super()._setup_scene()
        self.shelf.open_door(min=1.0, max=1.0, env=self)

    def _get_obj_cfgs(self):
        desk = lambda pos, size=(0.35, 0.3): dict(fixture=self.desk, size=size, pos=pos)
        return [
            dict(name="pen", obj_groups="straw", graspable=True, placement=desk((-0.5, -0.6))),
            dict(name="pen_holder", obj_groups="mug", placement=desk((0.5, -0.6))),
            dict(name="book", obj_groups="boxed_food", graspable=True, placement=desk((0.0, -0.6))),
            dict(name="snack_bag", obj_groups="chips", graspable=True, placement=desk((-0.2, -0.3))),
            dict(name="bin", obj_groups="basket", placement=desk((0.9, -0.3), (0.3, 0.4))),
        ]

    def subtasks(self):
        return [
            ("navigate", "desk"), ("posture", "counter"),
            ("pick", "pen"), ("place_in", "pen_holder"),
            ("pick", "snack_bag"), ("place_in", "bin"),
            ("pick", "book"), ("navigate", "shelf"), ("posture", "cabinet"), ("place_in_fixture", "shelf"),
        ]

    def _check_success(self):
        return (
            self._in("pen", "pen_holder")
            and self._in("snack_bag", "bin")
            and OU.obj_inside_of(self, "book", self.shelf)
            and self._all_far(["pen", "snack_bag", "book"])
        )


class FetchColaFromFridge(_LabTask):
    """"냉장고에서 콜라 하나 갖다줘": go to the fridge, open it, take the can, bring it to the sofa side.

    sofa side = dining counter (start and goal). `fridge_open=True` starts with the door open
    (for training the pick sub-skill separately from door opening).
    """

    EXCLUDE_LAYOUTS = Kitchen.DINING_COUNTER_EXCLUDED_LAYOUTS

    def __init__(self, *args, fridge_open=False, **kwargs):
        self.fridge_open = fridge_open
        super().__init__(*args, **kwargs)

    def _setup_kitchen_references(self):
        super()._setup_kitchen_references()
        self.fridge = self.register_fixture_ref("fridge", dict(id=FixtureType.FRIDGE))
        self.sofa_side = self.register_fixture_ref("sofa_side", dict(id=FixtureType.DINING_COUNTER))
        self.init_robot_base_ref = self.sofa_side
        if "refs" in self._ep_meta:
            self.rack_index = self._ep_meta["refs"]["rack_index"]
        else:
            self.rack_index = -1 if self.rng.random() < 0.5 else -2

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = "Bring me a can of cola from the fridge."
        ep_meta["refs"] = ep_meta.get("refs", {})
        ep_meta["refs"]["rack_index"] = self.rack_index
        return ep_meta

    def _setup_scene(self):
        if self.fridge_open:
            self.fridge.open_door(self, min=1.0, max=1.0)
        else:
            self.fridge.close_door(self)
        super()._setup_scene()

    def _get_obj_cfgs(self):
        return [
            dict(
                name="cola", obj_groups="can", graspable=True, fridgable=True,
                placement=dict(fixture=self.fridge, sample_region_kwargs=dict(compartment="fridge", reg_type="shelf", rack_index=self.rack_index),
                               size=(0.30, 0.15), pos=(0.0, -1.0)),
            ),
            dict(
                name="distr", obj_groups="yogurt", fridgable=True,
                placement=dict(fixture=self.fridge, sample_region_kwargs=dict(compartment="fridge", reg_type="shelf"),
                               size=(0.40, 0.15), pos=(0.0, -0.5)),
            ),
        ]

    def subtasks(self):
        return [
            ("navigate", "fridge"), ("posture", "fridge"),
            ("open_door", "fridge"), ("pick", "cola"),
            ("navigate", "sofa_side"), ("posture", "counter"), ("place_on", "sofa_side"),
        ]

    def _check_success(self):
        on_goal = OU.check_obj_fixture_contact(self, "cola", self.sofa_side)
        return on_goal and OU.check_obj_upright(self, "cola") and self._all_far(["cola"])


class RefillSnackBasket(_LabTask):
    """"간식 바구니 채워줘": see which snacks the basket is missing and refill it from the snack box.

    basket = basket on a counter holding one snack (object snack_in_basket_container); snack box = snacks on the
    counter by a cabinet.
    Success: two more snacks inside the basket.
    """

    def _setup_kitchen_references(self):
        super()._setup_kitchen_references()
        self.pantry = self.register_fixture_ref("pantry", dict(id=FixtureType.CABINET))
        self.counter = self.register_fixture_ref("counter", dict(id=FixtureType.COUNTER, ref=self.pantry))
        self.init_robot_base_ref = self.pantry

    def get_ep_meta(self):
        ep_meta = super().get_ep_meta()
        ep_meta["lang"] = "Refill the snack basket with the snacks from the snack box."
        return ep_meta

    def _get_obj_cfgs(self):
        here = lambda pos, size=(0.3, 0.3): dict(fixture=self.counter, sample_region_kwargs=dict(ref=self.pantry), size=size, pos=pos)
        return [
            # the snack already in the basket; RoboCasa spawns the basket as "<name>_container"
            dict(name="snack_in_basket", obj_groups=("chips", "chocolate", "candy"), graspable=True,
                 placement=dict(fixture=self.counter, sample_region_kwargs=dict(ref=self.pantry), size=(0.35, 0.35),
                                pos=(1.0, -0.8), try_to_place_in="basket")),
            dict(name="snack1", obj_groups=("chips", "chocolate", "candy"), graspable=True, placement=here((-0.6, -0.8))),
            dict(name="snack2", obj_groups=("chips", "chocolate", "candy"), graspable=True, placement=here((-0.2, -0.8))),
        ]

    BASKET = "snack_in_basket_container"

    def subtasks(self):
        return [
            ("navigate", "counter"), ("posture", "counter"),
            ("pick", "snack1"), ("place_in", self.BASKET),
            ("pick", "snack2"), ("place_in", self.BASKET),
        ]

    def _check_success(self):
        return (
            self._in("snack1", self.BASKET)
            and self._in("snack2", self.BASKET)
            and self._all_far(["snack1", "snack2"])
        )
