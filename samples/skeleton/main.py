#!/usr/bin/env python3

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR
from p3dopenvr.skeleton import DefaultLeftHandSkeleton, DefaultRightHandSkeleton
from p3dopenvr.hand import LeftHand, RightHand

import os

#load_prc_file_data("", "coordinate-system yup_right")

class MinimalOpenVR(P3DOpenVR):
    def __init__(self):
        P3DOpenVR.__init__(self)
        self.left_hand = None
        self.right_hand = None

    def load_vrmanifest(self):
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        filename = os.path.join(main_dir, "skeleton.vrmanifest")
        self.identify_application(filename, "p3dopenvr.demo.skeleton")

    def load_actions(self):
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        filename = os.path.join(main_dir, "demo_skeleton.json")
        self.load_action_manifest(filename)

    def load_models(self):
        self.left_hand = LeftHand(self, "models/vr_glove_left_model.glb", self.action_pose_left)
        self.left_hand.set_skeleton(DefaultLeftHandSkeleton(self, self.action_left_hand_skeleton))
        self.right_hand = RightHand(self, "models/vr_glove_right_model.glb", self.action_pose_right)
        self.right_hand.set_skeleton(DefaultRightHandSkeleton(self, self.action_right_hand_skeleton))

    def link_actions(self):
        self.add_action_set("/actions/demo")
        self.action_pose_left = self.vr_input.getActionHandle('/actions/demo/in/Hand_Left')
        self.action_pose_right = self.vr_input.getActionHandle('/actions/demo/in/Hand_Right')
        self.action_left_hand_skeleton = self.vr_input.getActionHandle('/actions/demo/in/left_hand_skeleton')
        self.action_right_hand_skeleton = self.vr_input.getActionHandle('/actions/demo/in/right_hand_skeleton')

    def update_action(self):
        self.left_hand.update()
        self.right_hand.update()

base = ShowBase()
base.setFrameRateMeter(True)

myvr = MinimalOpenVR()
myvr.init()

myvr.load_vrmanifest()
myvr.load_actions()
myvr.link_actions()
myvr.load_models()

model = loader.loadModel("panda")
model.reparentTo(render)
model.setPos(0, 10, -5)

base.accept('d', myvr.list_devices)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
