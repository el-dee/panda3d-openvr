#!/usr/bin/env python

from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import  TextNode
from panda3d.core import CollideMask, LVector3
from panda3d.core import ExecutionEnvironment
from direct.gui.OnscreenText import OnscreenText
from p3dopenvr.p3dopenvr import P3DOpenVR
import sys
import os

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

class RoamingRalphDemo(ShowBase):
    def __init__(self):
        # Set up the window, camera, etc.
        ShowBase.__init__(self)

        # Create and configure the VR environment

        self.ovr = P3DOpenVR()
        self.ovr.init(msaa=4)
        main_dir = ExecutionEnvironment.getEnvironmentVariable("MAIN_DIR")
        # Setup the application manifest, it will identify and configure the app
        # We force it in case it has changed.
        self.ovr.identify_application(os.path.join(main_dir, "ralph.vrmanifest"), "p3dopenvr.demo.ralph", force=True)
        # Load the actions manifest, it must be the same as the manifest referenced in the application manifest
        self.ovr.load_action_manifest(os.path.join(main_dir, "manifest/actions.json"))
        # Use the '/actions/platformer' action set. This action set will be updated each frame
        self.ovr.add_action_set("/actions/platformer")
        # Get the handle of the action '/actions/platformer/in/Move'. This hande will be used to retrieve the data of the action.
        self.action_move = self.ovr.vr_input.getActionHandle('/actions/platformer/in/Move')

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

        self.ralph = render.attachNewNode('ralph')
        self.ralphStartPos = self.environ.find("**/start_point").getPos()
        self.ovr.tracking_space.setPos(self.ralphStartPos)
        self.ralph.setPos(self.ovr.hmd_anchor.getPos(render))

        self.accept("escape", sys.exit)

        taskMgr.add(self.move, "moveTask")
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

    # Move camera according to user's input
    def move(self, task):
        # Get the time that elapsed since last frame.  We multiply this with
        # the desired speed in order to find out with which distance to move
        # in order to achieve that desired speed.
        dt = globalClock.getDt()

        # If a move-button is touched, move in the specified direction.
        move_data, device_path = self.ovr.get_analog_action_value(self.action_move)
        if move_data is not None:
            x, y = move_data.x,move_data.y
            # The x coordinate is used to turn the camera
            self.ovr.tracking_space.setH(self.ovr.tracking_space.getH() - x * 60 * dt)
            # The y coordinate is used to move the camera along the view vector
            # We retrieve the orientation of the headset and we generate a 2D direction
            orientation = self.ovr.hmd_anchor.get_quat(render)
            vector = orientation.xform(LVector3(0, 1, 0))
            vector[2] = 0
            vector.normalize()
            # Use the vector and the x value to move the camera relative to itself
            self.ovr.tracking_space.setPos(self.ovr.tracking_space.getPos() + vector * (y * 5 * dt))

        return task.cont

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
            self.ovr.tracking_space.setZ(entries[0].getSurfacePoint(render).getZ())
        else:
            self.ovr.tracking_space.setPos(self.ralphStartPos)
        self.ralph.setPos(self.ovr.hmd_anchor.getPos(render))

        # save ralph's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        self.ralphStartPos = self.ovr.tracking_space.getPos()

        return task.cont


demo = RoamingRalphDemo()
demo.run()
