#!/usr/bin/env python3

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR
from p3dopenvr.hand import LeftHand, RightHand

import openvr
import os
from direct.task.TaskManagerGlobal import taskMgr

class ActionsDemo:
    def __init__(self, ovr):
        self.ovr = ovr
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        ovr.identify_application(os.path.join(main_dir, "actions.vrmanifest"), "p3dopenvr.demo.actions")
        ovr.load_action_manifest(os.path.join(main_dir, "demo_actions.json"))
        ovr.add_action_set("/actions/demo")
        self.action_haptic_left = ovr.vr_input.getActionHandle('/actions/demo/out/Haptic_Left')
        action_pose_left = ovr.vr_input.getActionHandle('/actions/demo/in/Hand_Left')
        self.action_haptic_right = ovr.vr_input.getActionHandle('/actions/demo/out/Haptic_Right')
        action_pose_right = ovr.vr_input.getActionHandle('/actions/demo/in/Hand_Right')
        self.action_left_trigger = ovr.vr_input.getActionHandle('/actions/demo/in/left_trigger')
        self.action_right_trigger = ovr.vr_input.getActionHandle('/actions/demo/in/right_trigger')
        self.left_hand = LeftHand(ovr, "box", action_pose_left)
        self.left_hand.model.set_scale(0.1)
        self.right_hand = RightHand(ovr, "box", action_pose_right)
        self.right_hand.model.set_scale(0.1)
        taskMgr.add(self.update, sort=ovr.get_update_task_sort())

    def update(self, task):
        left_trigger_state, device = self.ovr.get_digital_action_rising_edge(self.action_left_trigger)
        if left_trigger_state:
            print("LEFT")
            self.ovr.vr_input.triggerHapticVibrationAction(self.action_haptic_left, 0, 1, 4, 1, openvr.k_ulInvalidInputValueHandle)
        right_trigger_state, device = self.ovr.get_digital_action_rising_edge(self.action_right_trigger)
        if right_trigger_state:
            print("RIGHT")
            self.ovr.vr_input.triggerHapticVibrationAction(self.action_haptic_right, 0, 1, 4, 1, openvr.k_ulInvalidInputValueHandle)
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
