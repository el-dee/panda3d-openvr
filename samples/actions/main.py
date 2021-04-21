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

        # Setup the application manifest, it will identify and configure the app
        # We force it in case it has changed.
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        ovr.identify_application(os.path.join(main_dir, "actions.vrmanifest"), "p3dopenvr.demo.actions", force=True)

        # Load the actions manifest, it must be the same as the manifest referenced in the application manifest
        ovr.load_action_manifest(os.path.join(main_dir, "../manifest/actions.json"))

        # Use the '/actions/default' action set. This action set will be updated each frame
        ovr.add_action_set("/actions/default")

        # Get the handle of the action '/actions/default/out/Haptic'. This hande will be used to trigger the haptic vibration.
        self.action_haptic = ovr.vr_input.getActionHandle('/actions/default/out/Haptic')

        # Get the handle of the action '/actions/default/in/Pose'. This hande will be used to update the position of the hands.
        hands_pose = ovr.vr_input.getActionHandle('/actions/default/in/Pose')

        # Get the handle of the action '/actions/default/in/GrabGrip'. This hande will be used to retrieve the data of the action.
        self.action_grip = ovr.vr_input.getActionHandle('/actions/default/in/GrabGrip')

        # Create the representation of the left hand and attach a simple box on it
        self.left_hand = LeftHand(ovr, "box", hands_pose)
        self.left_hand.model.set_scale(0.1)

        # Create the representation of the right hand and attach a simple box on it
        self.right_hand = RightHand(ovr, "box", hands_pose)
        self.right_hand.model.set_scale(0.1)

        # Register the update task with the correct sort number
        taskMgr.add(self.update, sort=ovr.get_update_task_sort())

    def update(self, task):
        # Retrieve the state of the Grip action and the device that has triggered it
        grip_state, device = self.ovr.get_digital_action_rising_edge(self.action_grip, device_path=True)
        if grip_state:
            # If the grip is active, activate the haptic vibration on the same device
            self.ovr.vr_input.triggerHapticVibrationAction(self.action_haptic, 0, 1, 4, 1, device)

        # Update the position and orientation of the hands
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

demo = ActionsDemo(ovr)

base.accept('escape', base.userExit)
base.accept('d', ovr.list_devices)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
