from direct.showbase.ShowBase import ShowBase
from panda3d.core import ExecutionEnvironment

from p3dopenvr.p3dopenvr import P3DOpenVR

import openvr
import os

class MinimalOpenVR(P3DOpenVR):
    def __init__(self):
        P3DOpenVR.__init__(self)
        self.left_hand = None
        self.right_hand = None

    def init_action(self):
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        filename = os.path.join(main_dir, "demo_actions.json")
        self.load_action_manifest(filename, "/actions/demo")
        self.action_haptic_left = self.vr_input.getActionHandle('/actions/demo/out/Haptic_Left')
        self.source_left = self.vr_input.getInputSourceHandle('/user/hand/left')
        self.action_pose_left = self.vr_input.getActionHandle('/actions/demo/in/Hand_Left')
        self.action_haptic_right = self.vr_input.getActionHandle('/actions/demo/out/Haptic_Right')
        self.source_right = self.vr_input.getInputSourceHandle('/user/hand/right')
        self.action_pose_right = self.vr_input.getActionHandle('/actions/demo/in/Hand_Right')
        self.action_left_trigger = self.vr_input.getActionHandle('/actions/demo/in/left_trigger')
        self.action_right_trigger = self.vr_input.getActionHandle('/actions/demo/in/right_trigger')

    def update_action(self):
        left_trigger_state, device = self.get_digital_action_rising_edge(self.action_left_trigger)
        if left_trigger_state:
            print("LEFT")
            self.vr_input.triggerHapticVibrationAction(self.action_haptic_left, 0, 1, 4, 1, openvr.k_ulInvalidInputValueHandle)
        right_trigger_state, device = self.get_digital_action_rising_edge(self.action_right_trigger)
        if right_trigger_state:
            print("RIGHT")
            self.vr_input.triggerHapticVibrationAction(self.action_haptic_right, 0, 1, 4, 1, openvr.k_ulInvalidInputValueHandle)
        left_pose = self.get_action_pose(self.action_pose_left)
        if  left_pose.pose.bPoseIsValid:
            left_matrix = self.get_pose_modelview(left_pose.pose)
            if self.left_hand is None:
                self.left_hand = self.tracking_space.attach_new_node('left-hand')
                model = loader.loadModel("box")
                model.reparent_to(self.left_hand)
                model.set_scale(0.1)
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
                model = loader.loadModel("box")
                model.reparent_to(self.right_hand)
                model.set_scale(0.1)
            self.right_hand.show()
            self.right_hand.set_mat(right_matrix)
        else:
            if self.right_hand is not None:
                self.right_hand.hide()

base = ShowBase()
base.setFrameRateMeter(True)

myvr = MinimalOpenVR()
myvr.init()

model = loader.loadModel("panda")
model.reparentTo(render)
model.setPos(0, 10, -5)

base.accept('d', myvr.list_devices)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
