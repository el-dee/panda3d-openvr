from direct.actor.Actor import Actor

class Hand:
    """
    This helper class manage a virtual hand in the tracking space.
    """
    def __init__(self, ovr, name, model, path, pose):
        """
        * ovr : Reference to the instance of P3DOpenVR.

        * name : Name of the hand, only used to name the anchor in the tracking space.

        * model : Path to the model to load or instance of a model or actor to use.

        * path : Path of the input source, usually either "/user/hand/left" or "/user/hand/right"

        * pose : Handler of the action pose holding the position and orientation of the hands.
        """
        self.ovr = ovr
        # Load the model if needed
        if isinstance(model, str):
            model = loader.loadModel(model)
        # Convert the model into an actor if needed
        if not isinstance(model, Actor):
            model = Actor(model)
        self.model = model
        self.path = path
        self.pose = pose
        self.hand_np = self.ovr.tracking_space.attach_new_node(name)
        self.model.reparent_to(self.hand_np)
        # Hide the hand until we get a valid pose for it
        self.hand_np.hide()
        self.skeleton = None

    def set_skeleton(self, skeleton):
        """
        Attach the given skeleton to the hand, once set the skeleton will be used to animate the hand

        * skeleton : An instance of HandSkeleton
        """
        self.skeleton = skeleton
        self.skeleton.set_model(self.model)

    def update(self):
        """
        Retrieve the hand position and orientation and update the model in the tracking space.
        """

        # Retrieve the actual device linked with this hand
        device = self.ovr.vr_input.getInputSourceHandle(self.path)

        # Retrieve the pose for that device
        hand_pose = self.ovr.get_action_pose(self.pose, device)

        if  hand_pose.pose.bPoseIsValid:
            # The pose is valid, show the hand and update it
            matrix = self.ovr.get_pose_modelview(hand_pose.pose)
            self.hand_np.show()
            self.hand_np.set_mat(matrix)
        else:
            # The pose is not valid, hide the hand
            self.hand_np.hide()

        # If there is a skeleton attached to this hand update it
        if self.skeleton is not None:
            self.skeleton.update()

class LeftHand(Hand):
    """
    Helper class representing a left hand
    """
    def __init__(self, ovr, model, pose):
        Hand.__init__(self, ovr, "left", model, "/user/hand/left", pose)

class RightHand(Hand):
    """
    Helper class representing a right hand
    """
    def __init__(self, ovr, model, pose):
        Hand.__init__(self, ovr, "right", model, "/user/hand/right", pose)
