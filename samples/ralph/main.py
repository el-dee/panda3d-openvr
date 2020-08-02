#!/usr/bin/env python

from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import Filename, AmbientLight, DirectionalLight
from panda3d.core import PandaNode, NodePath, Camera, TextNode
from panda3d.core import CollideMask, LVector3
from panda3d.core import ExecutionEnvironment
from direct.gui.OnscreenText import OnscreenText
from p3dopenvr.p3dopenvr import P3DOpenVR
import random
import sys
import os
import math

# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                        shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                        pos=(0.08, -pos - 0.04), align=TextNode.ALeft)

# Function to put title on the screen.
def addTitle(text):
    return OnscreenText(text=text, style=1, fg=(1, 1, 1, 1), scale=.07,
                        parent=base.a2dBottomRight, align=TextNode.ARight,
                        pos=(-0.1, 0.09), shadow=(0, 0, 0, 1))

class RoamingRalphVR(P3DOpenVR):
    def init_action(self):
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        filename = os.path.join(main_dir, "ralph_actions.json")
        self.load_action_manifest(filename, "/actions/ralph")
        self.action_haptic_left = self.vr_input.getActionHandle('/actions/ralph/out/Haptic_Left')
        self.source_left = self.vr_input.getInputSourceHandle('/user/hand/left')
        self.action_pose_left = self.vr_input.getActionHandle('/actions/ralph/in/Hand_Left')
        self.action_haptic_right = self.vr_input.getActionHandle('/actions/ralph/out/Haptic_Right')
        self.source_right = self.vr_input.getInputSourceHandle('/user/hand/right')
        self.action_pose_right = self.vr_input.getActionHandle('/actions/ralph/in/Hand_Right')
        self.action_trackpad_click = self.vr_input.getActionHandle('/actions/ralph/in/trackpadclick')
        self.action_trackpad_pos = self.vr_input.getActionHandle('/actions/ralph/in/trackpadpos')

    def update_action(self):
        # Get the time that elapsed since last frame.  We multiply this with
        # the desired speed in order to find out with which distance to move
        # in order to achieve that desired speed.
        dt = globalClock.getDt()

        # If a move-button is pressed, move in the specified direction.
        click_data, device_path = self.get_digital_action_state(self.action_trackpad_click)
        analog_data, device_path = self.get_analog_action_value(self.action_trackpad_pos)
        if click_data and analog_data is not None:
            x, y = analog_data.x,analog_data.y
            if x < -0.4:
                self.tracking_space.setH(self.tracking_space.getH() + 60 * dt)
            if x > 0.4:
                self.tracking_space.setH(self.tracking_space.getH() - 60 * dt)
            if y > 0.1:
                orientation = self.hmd_anchor.get_quat(render)
                vector = orientation.xform(LVector3(0, 1, 0))
                vector[2] = 0
                vector.normalize()
                self.tracking_space.setPos(self.tracking_space.getPos() + vector * (5 * dt))
            if y < -0.1:
                orientation = self.hmd_anchor.get_quat()
                vector = orientation.xform(LVector3(0, 1, 0))
                vector[2] = 0
                vector.normalize()
                self.tracking_space.setPos(self.tracking_space, vector * (-5 * dt))

class RoamingRalphDemo(ShowBase):
    def __init__(self):
        # Set up the window, camera, etc.
        ShowBase.__init__(self)

        # Set the background color to black
        self.win.setClearColor((0, 0, 0, 1))

        # Post the instructions
        self.title = addTitle(
            "Panda3D Tutorial: Roaming Ralph (Walking on Uneven Terrain)")
        self.inst1 = addInstructions(0.06, "[ESC]: Quit")
        self.inst2 = addInstructions(0.12, "[Left trackpad]: Rotate Left")
        self.inst3 = addInstructions(0.18, "[Right trackpad]: Rotate Right")
        self.inst4 = addInstructions(0.24, "[Up trackpad]: Walk Forward")
        self.inst4 = addInstructions(0.30, "[Down trackpad]: Walk Backward")

        # Set up the environment
        #
        # This environment model contains collision meshes.  If you look
        # in the egg file, you will see the following:
        #
        #    <Collide> { Polyset keep descend }
        #
        # This tag causes the following mesh to be converted to a collision
        # mesh -- a mesh which is optimized for collision, not rendering.
        # It also keeps the original mesh, so there are now two copies ---
        # one optimized for rendering, one for collisions.

        self.environ = loader.loadModel("models/world")
        self.environ.reparentTo(render)

        # Create the main character, Ralph

        self.vr = RoamingRalphVR()
        self.vr.init()

        self.ralph = render.attachNewNode('ralph')
        self.ralphStartPos = self.environ.find("**/start_point").getPos()
        self.vr.tracking_space.setPos(self.ralphStartPos)
        self.ralph.setPos(self.vr.hmd_anchor.getPos(render))

        self.accept("escape", sys.exit)

        taskMgr.add(self.collision, "collisionTask")

        # Set up the camera
        self.disableMouse()

        # We will detect the height of the terrain by creating a collision
        # ray and casting it downward toward the terrain.  One ray will
        # start above ralph's head, and the other will start above the camera.
        # A ray may hit the terrain, or it may hit a rock or a tree.  If it
        # hits the terrain, we can detect the height.  If it hits anything
        # else, we rule that the move is illegal.
        self.cTrav = CollisionTraverser()

        self.ralphGroundRay = CollisionRay()
        self.ralphGroundRay.setOrigin(0, 0, 9)
        self.ralphGroundRay.setDirection(0, 0, -1)
        self.ralphGroundCol = CollisionNode('ralphRay')
        self.ralphGroundCol.addSolid(self.ralphGroundRay)
        self.ralphGroundCol.setFromCollideMask(CollideMask.bit(0))
        self.ralphGroundCol.setIntoCollideMask(CollideMask.allOff())
        self.ralphGroundColNp = self.ralph.attachNewNode(self.ralphGroundCol)
        self.ralphGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.ralphGroundColNp, self.ralphGroundHandler)

        # Uncomment this line to see the collision rays
        #self.ralphGroundColNp.show()

        # Uncomment this line to show a visual representation of the
        # collisions occuring
        #self.cTrav.showCollisions(render)

        # Create some lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection((-5, -5, -5))
        directionalLight.setColor((1, 1, 1, 1))
        directionalLight.setSpecularColor((1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

    # Grid checking and collision detection
    def collision(self, task):

        # Normally, we would have to call traverse() to check for collisions.
        # However, the class ShowBase that we inherit from has a task to do
        # this for us, if we assign a CollisionTraverser to self.cTrav.
        #self.cTrav.traverse(render)

        # Adjust ralph's Z coordinate.  If ralph's ray hit terrain,
        # update his Z. If it hit anything else, or didn't hit anything, put
        # him back where he was last frame.

        entries = list(self.ralphGroundHandler.getEntries())
        entries.sort(key=lambda x: x.getSurfacePoint(render).getZ())

        if len(entries) > 0 and entries[0].getIntoNode().getName() == "terrain":
            self.vr.tracking_space.setZ(entries[0].getSurfacePoint(render).getZ())
        else:
            self.vr.tracking_space.setPos(self.ralphStartPos)
        self.ralph.setPos(self.vr.hmd_anchor.getPos(render))

        # save ralph's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        self.ralphStartPos = self.vr.tracking_space.getPos()

        return task.cont


demo = RoamingRalphDemo()
demo.run()
