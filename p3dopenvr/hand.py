from direct.actor.Actor import Actor

class Hand:
    def __init__(self, ovr, name, model, path, pose):
        self.ovr = ovr
        if isinstance(model, str):
            model = loader.loadModel(model)
        if not isinstance(model, Actor):
            model = Actor(model)
        self.model = model
        self.path = path
        self.pose = pose
        self.hand_np = self.ovr.tracking_space.attach_new_node(name)
        self.model.reparent_to(self.hand_np)
        self.hand_np.hide()
        self.skeleton = None

    def set_skeleton(self, skeleton):
        self.skeleton = skeleton
        self.skeleton.set_model(self.model)

    def update(self):
        device = self.ovr.vr_input.getInputSourceHandle(self.path)
        hand_pose = self.ovr.get_action_pose(self.pose, device)
        if  hand_pose.pose.bPoseIsValid:
            matrix = self.ovr.get_pose_modelview(hand_pose.pose)
            self.hand_np.show()
            self.hand_np.set_mat(matrix)
        else:
            self.hand_np.hide()
        if self.skeleton is not None:
            self.skeleton.update()

class LeftHand(Hand):
    def __init__(self, ovr, model, pose):
        Hand.__init__(self, ovr, "left", model, "/user/hand/left", pose)

class RightHand(Hand):
    def __init__(self, ovr, model, pose):
        Hand.__init__(self, ovr, "right", model, "/user/hand/right", pose)
