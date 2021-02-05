#!/usr/bin/env python3

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR
from p3dopenvr.skeleton import DefaultLeftHandSkeleton, DefaultRightHandSkeleton
from p3dopenvr.hand import LeftHand, RightHand

import os
from direct.task.TaskManagerGlobal import taskMgr

class SkeletonDemo:
    def __init__(self, ovr):
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        ovr.identify_application(os.path.join(main_dir, "skeleton.vrmanifest"), "p3dopenvr.demo.skeleton")
        ovr.load_action_manifest(os.path.join(main_dir, "demo_skeleton.json"))
        ovr.add_action_set("/actions/demo")
        action_pose_left = ovr.vr_input.getActionHandle('/actions/demo/in/Hand_Left')
        action_pose_right = ovr.vr_input.getActionHandle('/actions/demo/in/Hand_Right')
        action_left_hand_skeleton = ovr.vr_input.getActionHandle('/actions/demo/in/left_hand_skeleton')
        action_right_hand_skeleton = ovr.vr_input.getActionHandle('/actions/demo/in/right_hand_skeleton')
        self.left_hand = LeftHand(ovr, "models/vr_glove_left_model.glb", action_pose_left)
        self.left_hand.set_skeleton(DefaultLeftHandSkeleton(ovr, action_left_hand_skeleton))
        self.right_hand = RightHand(ovr, "models/vr_glove_right_model.glb", action_pose_right)
        self.right_hand.set_skeleton(DefaultRightHandSkeleton(ovr, action_right_hand_skeleton))
        taskMgr.add(self.update, sort=ovr.get_update_task_sort())

    def update(self, task):
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
demo = SkeletonDemo(ovr)

base.accept('escape', base.userExit)
base.accept('d', ovr.list_devices)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
