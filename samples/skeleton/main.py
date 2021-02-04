#!/usr/bin/env python3

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR
from p3dopenvr.skeleton import DefaultLeftHandSkeleton, DefaultRightHandSkeleton

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
        self.left_hand_model = loader.loadModel("models/vr_glove_left_model.glb")
        self.left_hand_model = Actor(self.left_hand_model)
        self.right_hand_model = loader.loadModel("models/vr_glove_right_model.glb")
        self.right_hand_model = Actor(self.right_hand_model)
        self.left_hand_skeleton = DefaultLeftHandSkeleton(self, self.action_left_hand_skeleton, self.left_hand_model)
        self.right_hand_skeleton = DefaultRightHandSkeleton(self, self.action_right_hand_skeleton, self.right_hand_model)

    def link_actions(self):
        self.add_action_set("/actions/demo")
        self.source_left = self.vr_input.getInputSourceHandle('/user/hand/left')
        self.source_right = self.vr_input.getInputSourceHandle('/user/hand/right')
        self.action_pose_left = self.vr_input.getActionHandle('/actions/demo/in/Hand_Left')
        self.action_pose_right = self.vr_input.getActionHandle('/actions/demo/in/Hand_Right')
        self.action_left_hand_skeleton = self.vr_input.getActionHandle('/actions/demo/in/left_hand_skeleton')
        self.action_right_hand_skeleton = self.vr_input.getActionHandle('/actions/demo/in/right_hand_skeleton')

    def update_action(self):
        left_pose = self.get_action_pose(self.action_pose_left)
        if  left_pose.pose.bPoseIsValid:
            left_matrix = self.get_pose_modelview(left_pose.pose)
            if self.left_hand is None:
                self.left_hand = self.tracking_space.attach_new_node('left-hand')
                self.left_hand_model.reparent_to(self.left_hand)
            self.left_hand.show()
            self.left_hand.set_mat(left_matrix)
        else:
            if self.left_hand is not None:
                self.left_hand.hide()
        right_pose = self.get_action_pose(self.action_pose_right)
        if  right_pose.pose.bPoseIsValid:
            right_matrix = self.get_pose_modelview(right_pose.pose)
            if self.right_hand is None:
                self.right_hand = self.tracking_space.attach_new_node('right-hand')
                self.right_hand_model.reparent_to(self.right_hand)
            self.right_hand.show()
            self.right_hand.set_mat(right_matrix)
        else:
            if self.right_hand is not None:
                self.right_hand.hide()
        self.left_hand_skeleton.update()
        self.right_hand_skeleton.update()

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
