from direct.actor.Actor import Actor

from .definitions import HandSkeletonBone

class HandSkeleton:
    """
    Helper class that will map the skeleton received from OpenVR onto the bones of the model of the hand.
    """
    def __init__(self, ovr, action, joint_map, part_name="modelRoot"):
        """
        * ovr : Reference to the instance of P3DOpenVR.

        * action : Handler of the action holding the bone transforms of the hand

        * joint_map : Dictionary that maps the joints of the model onto the bones of the OpenVR skeleton

        * part_name : Name of the root node in the model that contains the joints.
        """

        self.ovr = ovr
        self.action = action
        self.joint_map = joint_map
        self.part_name = part_name
        self.control_map = {}
        self.model = None

    def set_model(self, model):
        """
        Attach the given model to the skeleton.

        * model : Instance of the model of the hand.
        """

        if not isinstance(model, Actor):
            model = Actor(model, copy=False)
        self.model = model
        self.build_control_map()

    def build_control_map(self):
        """
        Retrieve the control joints in the model of the hand and map them onto the bones of the skeleton.
        """

        self.control_map = {}
        for (joint_name, bone_index) in self.joint_map.items():
            joint_control = self.model.control_joint(None, self.part_name, joint_name)
            if joint_control is not None:
                self.control_map[bone_index] = joint_control
            else:
                print("Joint '{}' not found or found multiple times".format(joint_name))

    def set_default_pose(self, pose):
        pass

    def update(self):
        """
        Retrieve the transforms for all the bone and update the linked control joints.
        This method should be called each frame after the main pose update task.
        """

        bone_transform_array, device_path = self.ovr.get_skeletal_bone_data(self.action)
        if bone_transform_array is not None:
            for (bone_index, joint_control) in self.control_map.items():
                transform_mat = self.ovr.get_bone_transform_mat(bone_transform_array, bone_index)
                joint_control.set_mat(transform_mat)

class DefaultLeftHandSkeleton(HandSkeleton):
    """
    Helper class that will map the default model of the left hand from Valve to the bones of the skeleton.
    """

    default_joint_map = {
        'wrist_l': HandSkeletonBone.Wrist,
        'finger_thumb_0_l': HandSkeletonBone.Thumb0,
        'finger_thumb_1_l': HandSkeletonBone.Thumb1,
        'finger_thumb_2_l': HandSkeletonBone.Thumb2,
        'finger_thumb_l_end': HandSkeletonBone.Thumb3,
        'finger_index_meta_l': HandSkeletonBone.IndexFinger0,
        'finger_index_0_l': HandSkeletonBone.IndexFinger1,
        'finger_index_1_l': HandSkeletonBone.IndexFinger2,
        'finger_index_2_l': HandSkeletonBone.IndexFinger3,
        'finger_index_l_end': HandSkeletonBone.IndexFinger4,
        'finger_middle_meta_l': HandSkeletonBone.MiddleFinger0,
        'finger_middle_0_l': HandSkeletonBone.MiddleFinger1,
        'finger_middle_1_l': HandSkeletonBone.MiddleFinger2,
        'finger_middle_2_l': HandSkeletonBone.MiddleFinger3,
        'finger_middle_l_end': HandSkeletonBone.MiddleFinger4,
        'finger_ring_meta_l': HandSkeletonBone.RingFinger0,
        'finger_ring_0_l': HandSkeletonBone.RingFinger1,
        'finger_ring_1_l': HandSkeletonBone.RingFinger2,
        'finger_ring_2_l': HandSkeletonBone.RingFinger3,
        'finger_ring_l_end': HandSkeletonBone.RingFinger4,
        'finger_pinky_meta_l': HandSkeletonBone.PinkyFinger0,
        'finger_pinky_0_l': HandSkeletonBone.PinkyFinger1,
        'finger_pinky_1_l': HandSkeletonBone.PinkyFinger2,
        'finger_pinky_2_l': HandSkeletonBone.PinkyFinger3,
        'finger_pinky_l_end': HandSkeletonBone.PinkyFinger4
    }

    def __init__(self, ovr, action):
        HandSkeleton.__init__(self, ovr, action, self.default_joint_map)

class DefaultRightHandSkeleton(HandSkeleton):
    """
    Helper class that will map the default model of the right hand from Valve to the bones of the skeleton.
    """

    default_joint_map = {
        'wrist_r': HandSkeletonBone.Wrist,
        'finger_thumb_0_r': HandSkeletonBone.Thumb0,
        'finger_thumb_1_r': HandSkeletonBone.Thumb1,
        'finger_thumb_2_r': HandSkeletonBone.Thumb2,
        'finger_thumb_r_end': HandSkeletonBone.Thumb3,
        'finger_index_meta_r': HandSkeletonBone.IndexFinger0,
        'finger_index_0_r': HandSkeletonBone.IndexFinger1,
        'finger_index_1_r': HandSkeletonBone.IndexFinger2,
        'finger_index_2_r': HandSkeletonBone.IndexFinger3,
        'finger_index_r_end': HandSkeletonBone.IndexFinger4,
        'finger_middle_meta_r': HandSkeletonBone.MiddleFinger0,
        'finger_middle_0_r': HandSkeletonBone.MiddleFinger1,
        'finger_middle_1_r': HandSkeletonBone.MiddleFinger2,
        'finger_middle_2_r': HandSkeletonBone.MiddleFinger3,
        'finger_middle_r_end': HandSkeletonBone.MiddleFinger4,
        'finger_ring_meta_r': HandSkeletonBone.RingFinger0,
        'finger_ring_0_r': HandSkeletonBone.RingFinger1,
        'finger_ring_1_r': HandSkeletonBone.RingFinger2,
        'finger_ring_2_r': HandSkeletonBone.RingFinger3,
        'finger_ring_r_end': HandSkeletonBone.RingFinger4,
        'finger_pinky_meta_r': HandSkeletonBone.PinkyFinger0,
        'finger_pinky_0_r': HandSkeletonBone.PinkyFinger1,
        'finger_pinky_1_r': HandSkeletonBone.PinkyFinger2,
        'finger_pinky_2_r': HandSkeletonBone.PinkyFinger3,
        'finger_pinky_r_end': HandSkeletonBone.PinkyFinger4
    }

    def __init__(self, ovr, action):
        HandSkeleton.__init__(self, ovr, action, self.default_joint_map)
