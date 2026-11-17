"""Generate robosuite-compatible RB-Y1 Model M MJCF files from the official rby1-sdk model.

Source: RainbowRobotics/rby1-sdk models/rby1m/mujoco/rby1_v1.2.xml (Apache 2.0).
Output (generated, not tracked): robot.xml (body + torso + arms + head, no gripper) and
gripper.xml (EE body + two slide fingers), with absolute mesh paths into the sdk checkout.

Changes from the source model
- the free joint and the four mecanum wheel joints are removed; robosuite's NullMobileBase
  adds holonomic x/y/yaw joints (the real base is mecanum, i.e. holonomic)
- per-link <include> files are inlined; class="visual"/"collision" become explicit attributes
  (robosuite convention: visual group 1, collision group 0)
- invisible "in-model-collision" primitives are dropped
- motors get finite torque limits and lighter armature/damping (source uses PD-sim values)
- EE_BODY and fingers move to gripper.xml; right_hand/left_hand mount bodies are added
- head and wrist cameras are added
"""
import argparse
import copy
import os
from pathlib import Path
import xml.etree.ElementTree as ET

SDK_DIR = Path(os.environ.get("RBY1_SDK_MODEL_DIR", "/ext/rby1-sdk/models/rby1m/mujoco"))
OUT_DIR = Path(os.environ.get("RBY1_GEN_DIR", Path(__file__).resolve().parent / "generated"))
SOURCE = "rby1_v1.2.xml"

# joint dynamics and torque limits (approximate; tune against the real robot)
JOINT_DYN = {"torso": (1.0, 20.0), "arm": (0.1, 2.0), "head": (0.05, 1.0)}
TORQUE = {"torso": 2000.0, "arm_lo": 150.0, "arm_hi": 40.0, "head": 20.0}

# camera frame: MuJoCo cameras look along -z with +y up; this quat makes them look along +x, z up
CAM_FWD_QUAT = "0.5 0.5 -0.5 -0.5"


def _group(joint_name):
    if joint_name.startswith("torso"):
        return "torso"
    if joint_name.startswith("head"):
        return "head"
    return "arm"


class Inliner:
    def __init__(self, sdk_dir):
        self.sdk_dir = sdk_dir
        self.meshes = {}  # name -> mesh element
        self.materials = {}

    def _resolve(self, fname, base_dir):
        for d in (base_dir, self.sdk_dir):
            p = (d / fname).resolve()
            if p.is_file():
                return p
        hits = list(self.sdk_dir.rglob(Path(fname).name))
        if len(hits) == 1:
            return hits[0]
        raise FileNotFoundError(fname)

    def load_assets(self, inc_file):
        root = ET.parse(inc_file).getroot()
        for el in root.iter():
            if el.tag == "mesh":
                p = self._resolve(el.get("file"), inc_file.parent)
                name = el.get("name") or p.stem
                m = ET.Element("mesh", {"name": name, "file": str(p)})
                for k in ("scale",):
                    if el.get(k):
                        m.set(k, el.get(k))
                self.meshes.setdefault(name, m)
            elif el.tag == "material":
                self.materials.setdefault(el.get("name"), copy.deepcopy(el))

    def geoms(self, inc_file):
        out = []
        for g in ET.parse(inc_file).getroot().iter("geom"):
            g = copy.deepcopy(g)
            cls = g.attrib.pop("class", None)
            if cls == "visual":
                g.attrib.update({"type": "mesh", "group": "1", "contype": "0", "conaffinity": "0"})
            elif cls == "collision":
                g.attrib.update({"type": "mesh", "group": "0", "contype": "1", "conaffinity": "1", "rgba": "0.5 0.5 0.5 1"})
            out.append(g)
        return out


def _expand_includes(body, inl, src_dir):
    for child in list(body):
        if child.tag == "include":
            idx = list(body).index(child)
            body.remove(child)
            for k, g in enumerate(inl.geoms(src_dir / child.get("file"))):
                body.insert(idx + k, g)
        elif child.tag == "geom" and child.get("class") == "in-model-collision":
            body.remove(child)
        elif child.tag == "body":
            _expand_includes(child, inl, src_dir)


def build(sdk_dir=SDK_DIR, out_dir=OUT_DIR):
    src_dir = Path(sdk_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = ET.parse(src_dir / SOURCE).getroot()
    inl = Inliner(src_dir)
    for inc in src.find("asset").findall("include"):
        inl.load_assets(src_dir / inc.get("file"))

    base = copy.deepcopy(src.find("worldbody").find("body[@name='base']"))
    _expand_includes(base, inl, src_dir)
    # drop free joint and wheel joints
    for b in base.iter("body"):
        for j in list(b.findall("joint")):
            if j.get("type") == "free" or j.get("name", "").startswith("wheel"):
                b.remove(j)
    # the base is driven kinematically by the holonomic slide joints, so the wheels need no
    # floor contact; RoboCasa's spawn check treats any robot contact (even with the floor) as a
    # collision and would push the robot out of the kitchen
    for b in base.iter("body"):
        if b.get("name", "").startswith("wheel"):
            for g in b.findall("geom"):
                if g.get("group") == "0":
                    b.remove(g)

    def find_body(root, name):
        return next(b for b in root.iter("body") if b.get("name") == name)

    # split grippers off; add hand mount + wrist camera
    grippers = {}
    for side, s in (("right", "r"), ("left", "l")):
        link6 = find_body(base, f"link_{side}_arm_6")
        parts = [c for c in list(link6) if c.tag == "body" and c.get("name") in (f"EE_BODY_{s.upper()}", f"ee_finger_{s}1", f"ee_finger_{s}2")]
        for p in parts:
            link6.remove(p)
        grippers[side] = parts
        ET.SubElement(link6, "body", {"name": f"{side}_hand", "pos": "0 0 0"})
        # wrist camera looking along the approach direction (-z of link 6)
        ET.SubElement(link6, "camera", {"name": f"{side}_wrist_camera", "mode": "fixed", "pos": "0.07 0 -0.12", "quat": "1 0 0 0", "fovy": "75"})

    # controller reference frames: arm OSC commands are expressed in link_torso_5, the same
    # frame the real robot's teleop/policy streams use (robo-synapse CONTROL_API.md)
    torso5 = find_body(base, "link_torso_5")
    for nm in ("right_center", "left_center", "torso_center", "head_center"):
        ET.SubElement(torso5, "site", {"name": nm, "pos": "0 0 0", "size": "0.01", "rgba": "1 0.3 0.3 0", "group": "2"})

    head2 = find_body(base, "link_head_2")
    ET.SubElement(head2, "camera", {"name": "head_camera", "mode": "fixed", "pos": "0.08 0 0.06", "quat": CAM_FWD_QUAT, "fovy": "58"})

    # joint dynamics + actuators
    actuators = ET.Element("actuator")
    for j in base.iter("joint"):
        name = j.get("name")
        grp = _group(name)
        arm, damp = JOINT_DYN[grp]
        j.set("armature", str(arm))
        j.set("damping", str(damp))
        if grp == "arm":
            idx = int(name.rsplit("_", 1)[1])
            lim = TORQUE["arm_lo"] if idx <= 3 else TORQUE["arm_hi"]
        else:
            lim = TORQUE[grp]
        ET.SubElement(actuators, "motor", {"name": f"torq_{name}", "joint": name, "ctrllimited": "true", "ctrlrange": f"{-lim} {lim}"})

    def asset_el(mesh_names=None):
        a = ET.Element("asset")
        for m in inl.materials.values():
            a.append(copy.deepcopy(m))
        for n, m in inl.meshes.items():
            if mesh_names is None or n in mesh_names:
                a.append(copy.deepcopy(m))
        return a

    def used_meshes(el):
        return {g.get("mesh") for g in el.iter("geom") if g.get("mesh")}

    robot = ET.Element("mujoco", {"model": "rby1"})
    ET.SubElement(robot, "compiler", {"angle": "radian", "autolimits": "true"})
    robot.append(asset_el(used_meshes(base)))
    wb = ET.SubElement(robot, "worldbody")
    wb.append(base)
    robot.append(actuators)
    ET.indent(robot)
    ET.ElementTree(robot).write(out_dir / "robot.xml")

    # gripper (same geometry for both sides; the left fingers are mirrored by joint axes)
    parts = grippers["right"]
    g_root = ET.Element("mujoco", {"model": "rby1_gripper"})
    holder = ET.Element("body", {"name": "gripper_body", "pos": "0 0 0"})
    for p in parts:
        p = copy.deepcopy(p)
        nm = p.get("name")
        p.set("name", {"EE_BODY_R": "ee_body", "ee_finger_r1": "finger1", "ee_finger_r2": "finger2"}[nm])
        for j in p.iter("joint"):
            j.set("name", {"gripper_finger_r1": "finger_joint1", "gripper_finger_r2": "finger_joint2"}[j.get("name")])
            j.attrib.update({"damping": "10", "armature": "0.01", "frictionloss": "1"})
        for k, gm in enumerate(p.iter("geom")):
            if gm.get("group") == "0":
                gm.set("name", f"{p.get('name')}_collision{k}")
                gm.attrib.update({"friction": "1.5 0.005 0.0001", "condim": "4", "solref": "0.01 1"})
            else:
                gm.set("name", f"{p.get('name')}_visual{k}")
        holder.append(p)
    # finger pads: small boxes at the inner fingertip faces, used for grasp checks
    for fb, sgn in (("finger1", 1), ("finger2", 1)):
        fbody = next(b for b in holder.iter("body") if b.get("name") == fb)
        ET.SubElement(fbody, "geom", {"name": f"{fb}_pad", "type": "box", "size": "0.004 0.012 0.012", "pos": f"{-0.006*sgn} 0 -0.035",
                                       "group": "0", "contype": "1", "conaffinity": "1", "friction": "2 0.05 0.0001", "condim": "4", "solref": "0.01 1", "rgba": "0.2 0.2 0.2 1"})
    # eef frame at the fingertip centre, z pointing along the approach direction (-z of link 6)
    eef = ET.SubElement(holder, "body", {"name": "eef", "pos": "0 0 -0.235", "quat": "0 1 0 0"})
    ET.SubElement(eef, "site", {"name": "grip_site", "pos": "0 0 0", "size": "0.01 0.01 0.01", "rgba": "1 0 0 0.5", "type": "sphere", "group": "1"})
    ET.SubElement(eef, "site", {"name": "grip_site_cylinder", "pos": "0 0 0", "size": "0.005 10", "rgba": "0 1 0 0.3", "type": "cylinder", "group": "1"})
    for ax, pos, quat, rgba in (("x", "0.1 0 0", "0.707105 0 0.707108 0", "1 0 0 0"), ("y", "0 0.1 0", "0.707105 0.707108 0 0", "0 1 0 0"), ("z", "0 0 0.1", "1 0 0 0", "0 0 1 0")):
        ET.SubElement(eef, "site", {"name": f"ee_{ax}", "pos": pos, "size": "0.005 .1", "quat": quat, "rgba": rgba, "type": "cylinder", "group": "1"})
    ET.SubElement(holder, "site", {"name": "ft_frame", "pos": "0 0 0", "size": "0.01 0.01 0.01", "rgba": "1 0 0 1", "type": "sphere", "group": "1"})
    g_root.append(asset_el(used_meshes(holder)))
    act = ET.SubElement(g_root, "actuator")
    # finger_joint1: axis -x, range [-0.05, 0]; finger_joint2: axis +x, range [0, 0.05]; 0 = closed
    ET.SubElement(act, "position", {"name": "gripper_finger_joint1", "joint": "finger_joint1", "ctrllimited": "true", "ctrlrange": "-0.05 0", "kp": "1000", "forcelimited": "true", "forcerange": "-40 40"})
    ET.SubElement(act, "position", {"name": "gripper_finger_joint2", "joint": "finger_joint2", "ctrllimited": "true", "ctrlrange": "0 0.05", "kp": "1000", "forcelimited": "true", "forcerange": "-40 40"})
    gwb = ET.SubElement(g_root, "worldbody")
    gwb.append(holder)
    sens = ET.SubElement(g_root, "sensor")
    ET.SubElement(sens, "force", {"name": "force_ee", "site": "ft_frame"})
    ET.SubElement(sens, "torque", {"name": "torque_ee", "site": "ft_frame"})
    ET.indent(g_root)
    ET.ElementTree(g_root).write(out_dir / "gripper.xml")
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdk-dir", default=str(SDK_DIR))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    a = ap.parse_args()
    print(build(a.sdk_dir, a.out_dir))
