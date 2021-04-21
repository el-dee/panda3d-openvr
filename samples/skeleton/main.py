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
        self.ovr = ovr

        # Setup the application manifest, it will identify and configure the app
        # We force it in case it has changed.
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        ovr.identify_application(os.path.join(main_dir, "skeleton.vrmanifest"), "p3dopenvr.demo.skeleton", force=True)

        # Load the actions manifest, it must be the same as the manifest referenced in the application manifest
        ovr.load_action_manifest(os.path.join(main_dir, "../manifest/actions.json"))

        # Use the '/actions/default' action set. This action set will be updated each frame
        ovr.add_action_set("/actions/default")

        # Get the handle of the action '/actions/default/in/Pose'. This hande will be used to update the position of the hands.
        hands_pose = ovr.vr_input.getActionHandle('/actions/default/in/Pose')

        # Get the handle of the skeleton actions. These handle will be used to update the
        # animation of the hands
        left_hand_skeleton_input = ovr.vr_input.getActionHandle('/actions/default/in/SkeletonLeftHand')
        right_hand_skeleton_input = ovr.vr_input.getActionHandle('/actions/default/in/SkeletonRightHand')

        # Create the representation of the left hand and attach a skinned hand model to it
        self.left_hand = LeftHand(ovr, "models/vr_glove_left_model.glb", hands_pose)
        self.left_hand.set_skeleton(DefaultLeftHandSkeleton(ovr, left_hand_skeleton_input))

        # Create the representation of the left hand and attach a skinned hand model to it
        self.right_hand = RightHand(ovr, "models/vr_glove_right_model.glb", hands_pose)
        self.right_hand.set_skeleton(DefaultRightHandSkeleton(ovr, right_hand_skeleton_input))

        # Register the update task with the correct sort number
        taskMgr.add(self.update, sort=ovr.get_update_task_sort())

    def update(self, task):
        # Update the position and orientation of the hands and their skeletons
        self.left_hand.update()
        self.right_hand.update()
        return task.cont

# Set up the window, camera, etc.
base = ShowBase()
base.setFrameRateMeter(True)

# Create and configure the VR environment

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
