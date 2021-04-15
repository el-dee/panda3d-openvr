#!/usr/bin/env python3

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR
from p3dopenvr.hand import LeftHand, RightHand

import os
from direct.task.TaskManagerGlobal import taskMgr

class ActionsDemo:
    def __init__(self, ovr):
        self.ovr = ovr
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        ovr.identify_application(os.path.join(main_dir, "actions.vrmanifest"), "p3dopenvr.demo.actions", force=True)
        ovr.load_action_manifest(os.path.join(main_dir, "../manifest/actions.json"))
        ovr.add_action_set("/actions/default")
        self.action_haptic = ovr.vr_input.getActionHandle('/actions/default/out/Haptic')
        hands_pose = ovr.vr_input.getActionHandle('/actions/default/in/Pose')
        self.action_grip = ovr.vr_input.getActionHandle('/actions/default/in/GrabGrip')
        self.left_hand = LeftHand(ovr, "box", hands_pose)
        self.left_hand.model.set_scale(0.1)
        self.right_hand = RightHand(ovr, "box", hands_pose)
        self.right_hand.model.set_scale(0.1)
        taskMgr.add(self.update, sort=ovr.get_update_task_sort())

    def update(self, task):
        grip_state, device = self.ovr.get_digital_action_rising_edge(self.action_grip, device_path=True)
        if grip_state:
            self.ovr.vr_input.triggerHapticVibrationAction(self.action_haptic, 0, 1, 4, 1, device)
        self.left_hand.update()
        self.right_hand.update()
        return task.cont

base = ShowBase()
base.setFrameRateMeter(True)

ovr = P3DOpenVR()
ovr.init()

model = loader.loadModel("panda")
model.reparentTo(render)
min_bounds, max_bounds = model.get_tight_bounds()
height = max_bounds.get_z() - min_bounds.get_z()
model.set_scale(1.5 / height)
model.set_pos(0, 1, -min_bounds.get_z() / height * 1.5)

demo = ActionsDemo(ovr)

base.accept('escape', base.userExit)
base.accept('d', ovr.list_devices)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
