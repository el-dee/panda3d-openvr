from panda3d.core import load_prc_file_data, NodePath, CardMaker, LQuaternion, compose_matrix
from panda3d.core import GeomVertexData, GeomVertexFormat, GeomVertexWriter, GeomTriangles, GeomNode, Geom, InternalName
from panda3d.core import CullFaceAttrib, Shader, BitMask32
from panda3d.core import LMatrix3, LMatrix4, LVector2, LVector3, LVector4, CS_yup_right, CS_default
from panda3d.core import WindowProperties, FrameBufferProperties, GraphicsPipe, GraphicsOutput, GraphicsEngine, Texture, PythonCallbackObject
from panda3d.core import Camera, MatrixLens, OrthographicLens

import atexit
import openvr
import os

# HMD screens are never a power of 2 size
load_prc_file_data("", "textures-power-2 none")

# Disable v-sync, it will be managed by waitGetPoses()
load_prc_file_data("", "sync-video 0")
# NVidia driver requires this env variable to be set to 0 to disable v-sync
os.environ['__GL_SYNC_TO_VBLANK'] = "0"
# MESA OpenGL drivers requires this env variable to be set to 0 to disable v-sync
os.environ['vblank_mode'] = "0"

@atexit.register
def exitfunc():
    openvr.shutdown()

class P3DOpenVR():
    def __init__(self, base=None, verbose=True):
        """
        Wrapper around pyopenvr to allow it to work with Panda3D.
        See the init() method below for the actual initialization.

        * verbose specifies if the library prints status information when running.
        """

        if base is None:
            base = __builtins__.get('base')
        self.base = base
        self.verbose = verbose
        self.vr_system = None
        self.vr_applications = None
        self.vr_input = None
        self.compositor = None
        self.poses = None
        self.action_set_handles = []
        self.buffers = []
        self.nextsort = self.base.win.getSort() - 1000
        self.tracking_space = None
        self.hmd_anchor = None
        self.left_eye_anchor = None
        self.right_eye_anchor = None
        self.left_cam = None
        self.right_cam = None
        self.ham_shader = None
        self.tracked_devices_anchors = {}
        self.empty_world = None
        self.coord_mat = LMatrix4.convert_mat(CS_yup_right, CS_default)
        self.coord_mat_inv = LMatrix4.convert_mat(CS_default, CS_yup_right)
        self.submit_together = True
        self.event_handlers = []
        self.submit_error_handler = None
        self.new_tracked_device_handler = None
        self.has_focus = False

        #Deprecation flags to avoid spamming
        self.process_vr_event_notified = False
        self.new_tracked_device_notified = False
        self.update_action_notified = False
        self.on_texture_submit_error_notified = False

    def create_buffer(self, name, texture, width, height, fbprops):
        """
        Create a render buffer with the given properties.
        """

        winprops = WindowProperties()
        winprops.set_size(width, height)
        props = FrameBufferProperties(FrameBufferProperties.get_default())
        props.set_back_buffers(0)
        props.set_rgb_color(1)
        if fbprops is not None:
            props.add_properties(fbprops)

        buffer = self.base.win.make_texture_buffer(name, width, height, to_ram=False, fbp=props)
        if buffer is not None:
            buffer.clear_render_textures()
            buffer.set_sort(self.nextsort)
            self.nextsort += 1
            buffer.add_render_texture(texture, GraphicsOutput.RTMBindOrCopy, GraphicsOutput.RTPColor)
        else:
            print("COULD NOT CREATE BUFFER")
        return buffer

    def create_renderer(self, name, camera, width, height, msaa, callback, cc=None):
        """
        Create and configure a render to texture pipeline and attach it the given camera and draw callback.
        """

        texture = Texture()
        texture.set_wrap_u(Texture.WMClamp)
        texture.set_wrap_v(Texture.WMClamp)
        texture.set_minfilter(Texture.FT_linear)
        texture.set_magfilter(Texture.FT_linear)
        fbprops = FrameBufferProperties()
        fbprops.setRgbaBits(1, 1, 1, 1)
        if msaa > 0:
            fbprops.setMultisamples(msaa)
        buffer = self.create_buffer(name, texture, width, height, fbprops=fbprops)
        dr = buffer.make_display_region()
        dr.set_camera(camera)
        dr.set_active(1)
        self.buffers.append(buffer)
        if callback is not None:
            dr.set_draw_callback(PythonCallbackObject(callback))
        if cc is not None:
            dr.setClearColorActive(1)
            dr.setClearColor(cc)
        return texture

    def create_camera(self, name, projection_mat):
        """
        Create a camera with the given projection matrix.
        """

        cam_node = Camera(name)
        lens = MatrixLens()
        lens.set_user_mat(projection_mat)
        cam_node.set_lens(lens)
        return cam_node

    def convert_mat(self, mat):
        """
        Convert a OpenVR Matrix into a Panda3D Matrix. No coordinate system conversion is performed.
        Note that 3x4 matrices are converted into 4x4 matrices.
        """

        if len(mat.m) == 4:
            result = LMatrix4(
                    mat.m[0][0], mat.m[1][0], mat.m[2][0], mat.m[3][0],
                    mat.m[0][1], mat.m[1][1], mat.m[2][1], mat.m[3][1], 
                    mat.m[0][2], mat.m[1][2], mat.m[2][2], mat.m[3][2], 
                    mat.m[0][3], mat.m[1][3], mat.m[2][3], mat.m[3][3])
        elif len(mat.m) == 3:
            result = LMatrix4(
                    mat.m[0][0], mat.m[1][0], mat.m[2][0], 0.0,
                    mat.m[0][1], mat.m[1][1], mat.m[2][1], 0.0, 
                    mat.m[0][2], mat.m[1][2], mat.m[2][2], 0.0, 
                    mat.m[0][3], mat.m[1][3], mat.m[2][3], 1.0)
        return result

    def convert_vector(self, vector):
        """
        Convert a OpenVR vector into a Panda3D vector. No coordinate system conversion is performed.
        """

        if len(vector.v) == 4:
            result = LVector4(vector.v[0], vector.v[1], vector.v[2], vector.v[3])
        elif len(vector.v) == 3:
            result = LVector3(vector.v[0], vector.v[1], vector.v[2])
        elif len(vector.v) == 2:
            result = LVector2(vector.v[0], vector.v[1])
        return result

    def convert_quaternion(self, quaternion):
        """
        Convert a OpenVR quaternion into a Panda3D quaternion. No coordinate system conversion is performed.
        """

        return LQuaternion(quaternion.w, quaternion.x, quaternion.y, quaternion.z)

    def disable_main_cam(self):
        """
        Disable the default camera (but not remove it).
        """

        self.empty_world = NodePath()
        self.base.camera.reparent_to(self.empty_world)

    def replicate(self, texture):
        """
        Attach the given texture to a full window quad.
        """

        cm = CardMaker("replicate-quad")
        cm.set_frame_fullscreen_quad()
        self.quad = NodePath(cm.generate())
        self.quad.set_depth_test(0)
        self.quad.set_depth_write(0)
        self.quad.set_texture(texture)

        lens = OrthographicLens()
        lens.set_film_size(2, 2)
        lens.set_film_offset(0, 0)
        lens.set_near_far(-1000, 1000)
        self.base.cam.node().set_lens(lens)
        self.base.cam.reparent_to(self.quad)

    def get_ham_shader(self):
        """
        Return a trivial shader that will directly place the mesh in the clip space
        """

        if self.ham_shader is None:
            self.ham_shader = Shader.make(Shader.SL_GLSL,
                vertex="""#version 330
in vec4 p3d_Vertex;
void main() {
    gl_Position = p3d_Vertex;
}
""",
       fragment="""#version 330
out vec4 frag_color;
void main() {
    frag_color = vec4(0, 0, 0, 1);
}
""")
        return self.ham_shader

    def create_hidden_area_mesh(self, mask):
        """
        Using the provided mask configuration, create the mesh that will cover the area not visible from the HMD
        """

        gvf = GeomVertexFormat.get_v3()
        gvd = GeomVertexData('gvd', gvf, Geom.UH_static)
        geom = Geom(gvd)
        gvw = GeomVertexWriter(gvd, InternalName.get_vertex())
        for i in range(mask.unTriangleCount * 3):
            vertex = mask.pVertexData[i]
            # The clip space in Panda3D has [-1, 1] coordinates, the received coordinates are in [0, 1]
            gvw.add_data3(vertex[0] * 2 - 1, vertex[1] * 2 - 1, -1)
        prim = GeomTriangles(Geom.UH_static)
        for i in range(mask.unTriangleCount):
            prim.add_vertices(i * 3, i *3 + 1, i * 3 + 2)
        geom.add_primitive(prim)
        node = GeomNode('hidden-area-mesh')
        node.add_geom(geom)
        return node

    def attach_hidden_area_mesh(self, eye, anchor, camera_mask):
        """
        Create and attach the two meshes that will hide the areas not visible from the HMD.
        """

        left_eye_mask = self.vr_system.getHiddenAreaMesh(eye, type_=openvr.k_eHiddenAreaMesh_Standard)
        left_mesh = self.create_hidden_area_mesh(left_eye_mask)
        np = anchor.attach_new_node(left_mesh)
        # The winding order is not specified, it is recommended to disable backface culling
        np.set_attrib(CullFaceAttrib.make(CullFaceAttrib.M_cull_none))
        np.set_shader(self.get_ham_shader(), 10000)
        # Make sure that the mesh is rendered first to allow early-z optimization
        np.set_bin("background", 0)
        # Hide this mesh from the opposite camera
        np.hide(BitMask32.bit(camera_mask))

    def init(self, near=0.2, far=500.0, root=None, submit_together=True, msaa=0, replicate=1, srgb=None, hidden_area_mesh=True):
        """
        Initialize OpenVR. This method will create the rendering buffers, the cameras associated with each eyes
        and the various anchors in the tracked space. It will also start the tasks responsible for the correct
        scheduling. This method should be called only once.

        * near and far parameters can be used to specify the near and far planes of the cameras.

        * root parameter, when not None, is used as the root node to which the tracked space will attached.
          Otherwise the tracked space is attached to render.

        * submit_together specifies if each eye buffer is submitted just after being rendered or both at once.

        * msaa specifies the multisampling anti-aliasing level to use, set to 0 to disable.

        * replicate specifies which eye is replicated on the application window.
          0: No replication, 1: left eye, 2: right eye.

        * srgb : If None, OpenVR will detect the color space from the texture format. If set to True, sRGB color
          space will be enforced; if set to False, linear color space will be enforced.

        * hidden_area_mesh : If True, a mask will be applied on each camera to cover the area not seen from the HMD
          This will trigger the early-z optimization on the GPU and avoid rendering unseen pixels.
        """

        self.submit_together = submit_together
        if srgb is None:
            self.color_space = openvr.ColorSpace_Auto
        else:
            if srgb:
                self.color_space = openvr.ColorSpace_Gamma
            else:
                self.color_space = openvr.ColorSpace_Linear

        # Create a OpenVR array that will store the pose of all the tracked devices.
        poses_t = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        self.poses = poses_t()

        # Initialise OpenVR and retrieve the main components
        self.vr_system = openvr.init(openvr.VRApplication_Scene)
        self.vr_applications = openvr.VRApplications()
        width, height = self.vr_system.getRecommendedRenderTargetSize()
        self.compositor = openvr.VRCompositor()
        self.vr_input = openvr.VRInput()
        if self.compositor is None:
            raise Exception("Unable to create compositor") 

        # Create the tracking space anchors
        if root is None:
            root = self.base.render
        self.tracking_space = root.attach_new_node('tracking-space')
        self.hmd_anchor = self.tracking_space.attach_new_node('hmd-anchor')
        self.left_eye_anchor = self.hmd_anchor.attach_new_node('left-eye')
        self.right_eye_anchor = self.hmd_anchor.attach_new_node('right-eye')

        # Create the projection matrices for the left and right camera.
        # TODO: This should be updated in the update task in the case the user update the IOD
        self.projection_left = self.coord_mat_inv * self.convert_mat(self.vr_system.getProjectionMatrix(openvr.Eye_Left, near, far))
        self.projection_right = self.coord_mat_inv * self.convert_mat(self.vr_system.getProjectionMatrix(openvr.Eye_Right, near, far))

        # Create the cameras and attach them in the tracking space
        left_cam_node = self.create_camera('left-cam', self.projection_left)
        right_cam_node = self.create_camera('right-cam', self.projection_right)

        self.left_cam = self.left_eye_anchor.attach_new_node(left_cam_node)
        self.right_cam = self.right_eye_anchor.attach_new_node(right_cam_node)

        # Create the renderer linked to each camera
        self.left_texture = self.create_renderer('left-buffer', self.left_cam, width, height, msaa, self.left_cb)
        self.right_texture = self.create_renderer('right-buffer', self.right_cam, width, height, msaa, self.right_cb)

        # The main camera is useless, so we disable it
        self.disable_main_cam()

        if hidden_area_mesh:
            # If the hidden area mesh is used, assign a mask on each camera to hide the opposite mesh
            left_cam_node.set_camera_mask(BitMask32.bit(0))
            right_cam_node.set_camera_mask(BitMask32.bit(1))
            self.attach_hidden_area_mesh(openvr.Eye_Left, self.left_eye_anchor, 1)
            self.attach_hidden_area_mesh(openvr.Eye_Right, self.right_eye_anchor, 0)

        if replicate == 1:
            if self.verbose:
                print("Replicating left eye")
            self.replicate(self.left_texture)
        elif replicate == 2:
            if self.verbose:
                print("Replicating right eye")
            self.replicate(self.right_texture)
        else:
            if self.verbose:
                print("Eye replication disabled")

        if hasattr(self, 'init_action'):
            print("WARNING: init_action() is deprecated and will be removed in a future release")
            self.init_action()

        # Launch the main task that will synchronize Panda3D with OpenVR
        # TODO: The sort number should be configurable and by default be placed after the gc tasks.
        self.task = taskMgr.add(self.update_poses_task, "openvr-update-poses", sort=-1000)

    def get_update_task_sort(self):
        """
        Return the correct sort number to use for any update task. They must always be run after the task updating
        the poses.
        """

        return self.task.get_sort() + 1

    def identify_application(self, application_filename, app_key, temporary=True, force=False):
        """
        Register the application in OpenVR, this will allow any custom configuration made in the OpenVR implementation
        e.g. SteamVR, to be associated with this application and restored when the app is launched again.

        * application_filename : Path to the application manifest that contains all the data describing the application

        * app_key : Unique identifier for this application.

        * temporary : Set to True if the OpenVR implementation should not store the information related to this
          application.

        * force : Set to true is any previous registration related to this application should be removed.
        """

        identified = False
        app_installed = self.vr_applications.isApplicationInstalled(app_key)
        if not app_installed or force:
            if self.verbose:
                print("Installing manifest for application '{}'".format(app_key))
            if os.path.exists(application_filename):
                if app_installed and force:
                    try:
                        self.vr_applications.removeApplicationManifest(application_filename)
                    except openvr.error_code.ApplicationError:
                        pass
                self.load_application_manifest(application_filename, temporary)
            else:
                print("ERROR: Manifest file '{}' not found".format(application_filename))
        else:
            if self.verbose:
                print("Application manifest already registered for '{}'".format(app_key))
        try:
            self.vr_applications.identifyApplication(os.getpid(), app_key)
            identified = True
        except openvr.error_code.ApplicationError_UnknownApplication:
            print("ERROR: Could not identify application '{}', manifest information is probably wrong".format(app_key))
        return identified

    def load_application_manifest(self, manifest_filename, temporary):
        """
        Load the given application manifest. This is a low-level method, use identify_application() instead.
        """

        if self.verbose:
            print("Loading", manifest_filename)
        self.vr_applications.addApplicationManifest(manifest_filename, temporary)

    def load_action_manifest(self, action_filename, action_path=None):
        """
        Load the action manifest given in parameter.

        action_filename : Path to the action manifest main configuration file.

        action_path : Deprecated parameter, do not use.
        """

        if self.verbose:
            print("Loading", action_filename)
        self.vr_input.setActionManifestPath(action_filename)
        if action_path is not None:
            print("WARNING: 'action_path' parameter of load_action_manifest() is deprecated and will be removed in a next release")
            self.add_action_set(action_path)

    def add_action_set(self, action_set_path):
        """
        Add the given action set to the list of action sets to update each frame.

        action_set_path : Full path of the action set
        """

        self.action_set_handles.append(self.vr_input.getActionSetHandle(action_set_path))

    def update_hmd(self, pose):
        """
        Update the anchors linked to the headset and the eyes in the tracking space
        """

        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        self.hmd_anchor.set_mat(self.coord_mat_inv * modelview * self.coord_mat)
        view_left = self.convert_mat(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left))
        self.left_eye_anchor.set_mat(self.coord_mat_inv * view_left * self.coord_mat)
        view_right = self.convert_mat(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right))
        self.right_eye_anchor.set_mat(self.coord_mat_inv * view_right * self.coord_mat)

    def set_new_tracked_device_handler(self, event_handler):
        """
        Register a handler to be called when a new tracked device has been detected.
        The handler will receive these two parameters :
        * device_index : the index of the device to be used as parameter when using OpenVR API.
        * device_anchor : the node path created in the tracked space for the device.
        """

        self.new_tracked_device_handler = event_handler

    def update_tracked_device(self, device_index, pose):
        """
        Update the anchor linked to the tracked device in the tracking space. If the device is not yet in the list of
        tracked devices, the new_tracked_device handler will be called.
        """

        if not device_index in self.tracked_devices_anchors:
            model_name = self.vr_system.getStringTrackedDeviceProperty(device_index, openvr.Prop_RenderModelName_String)
            np_name = str(device_index) + ':' + model_name
            device_anchor = self.tracking_space.attach_new_node(np_name)
            self.tracked_devices_anchors[device_index] = device_anchor
            if hasattr(self, 'new_tracked_device'):
                if not self.new_tracked_device_notified:
                    print("WARNING: new_tracked_device() is deprecated and will be removed in a future release")
                    self.new_tracked_device_notified = True
                self.new_tracked_device(device_index, device_anchor)
            else:
                if self.new_tracked_device_handler is not None:
                    self.new_tracked_device_handler(device_index, device_anchor)
        else:
            device_anchor = self.tracked_devices_anchors[device_index]
        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        modelview = self.coord_mat_inv * modelview * self.coord_mat
        device_anchor.set_mat(modelview)

    def update_tracked_devices(self):
        """
        Update all the tracked devices linked with the observed poses
        """

        for i in range(1, len(self.poses)):
            pose = self.poses[i]
            if not pose.bPoseIsValid:
                continue
            self.update_tracked_device(i, pose)

    def register_event_handler(self, event_handler):
        """
        Register an event handler called to process all the pending events received from OpenVR.
        The handler will receive one parameter :
        * event : the OpenVR event to process.
        """

        self.event_handlers.append(event_handler)

    def remove_event_handler(self, event_handler):
        """
        Remove a previously registered event handler
        """

        try:
            self.event_handlers.remove(event_handler)
        except ValueError:
            pass

    def poll_events(self):
        """
        Retrieve and forward all the events pending in the VR system to the registered event handlers.
        """

        event = openvr.VREvent_t()
        has_events = self.vr_system.pollNextEvent(event)
        while has_events:
            if event.eventType == openvr.VREvent_InputFocusCaptured:
                if self.verbose:
                    print("Application captured the input focus")
                self.has_focus = True
            elif event.eventType == openvr.VREvent_InputFocusReleased:
                if self.verbose:
                    print("Application released the input focus")
                self.has_focus = False
            if hasattr(self, 'process_vr_event'):
                if not self.process_vr_event_notified:
                    print("WARNING: 'update_action()' method is deprecated and will be removed in a next release")
                    self.process_vr_event_notified = True
                self.process_vr_event(event)
            else:
                for event_handler in self.event_handlers:
                    event_handler(event)
            has_events = self.vr_system.pollNextEvent(event)

    def update_action_state(self):
        """
        Update the state of all the registered action sets.
        """

        nb_of_action_sets = len(self.action_set_handles)
        if nb_of_action_sets > 0:
            action_sets = (openvr.VRActiveActionSet_t * nb_of_action_sets)()
            for i in range(nb_of_action_sets):
                action_set = action_sets[i]
                action_set.ulActionSet = self.action_set_handles[i]
            self.vr_input.updateActionState(action_sets)
        if hasattr(self, 'update_action'):
            if not self.update_action_notified:
                print("WARNING: 'update_action()' method is deprecated and will be removed in a next release")
                self.update_action_notified = True
            self.update_action()

    def update_poses_task(self, task):
        """
        Main task of the VR system, this method will synchronize Panda3D with the OpenVR renderer to allow providing
        the rendered scene in time.
        It will also poll the pending events, update the hmd pose and all the registered action sets.
        """

        if self.compositor is None:
            return task.cont
        # waitGetPoses() is a blocking call, it will returns only when OpenVR allow us to start rendering the next
        # frame.
        self.compositor.waitGetPoses(self.poses, None)

        # Poll and forward all the pending events
        self.poll_events()

        # Retrieve the HMD pose, or bail out if it is not available.
        hmd_pose = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose.bPoseIsValid:
            if self.verbose:
                print("HMD pose is not valid")
            return task.cont
        self.update_hmd(hmd_pose)

        # Update any explicitly tracked devices
        self.update_tracked_devices()

        # Update all the action sets
        self.update_action_state()

        return task.cont

    def set_submit_error_handler(self, error_handler):
        """
        Register a handler called when submit_texture() fails. If no handler is registered, the catched
        exception is directly reraised.
        The handler will receive one parameter :
        * exception : the exception raised during the texture submit.
        """

        self.submit_error_handler = error_handler

    def submit_texture(self, eye, texture):
        """
        Submit to OpenVR the rendered frame for the given eye.
        Note that this method must be called from within the Draw context in order to have the texture bound.
        """

        try:
            # Retrieve the texture OpenGL binding
            texture_context = texture.prepare_now(0, self.base.win.gsg.prepared_objects, self.base.win.gsg)
            handle = texture_context.get_native_id()
            if handle != 0:
                ovr_texture = openvr.Texture_t()
                ovr_texture.handle = texture_context.get_native_id()
                ovr_texture.eType = openvr.TextureType_OpenGL
                ovr_texture.eColorSpace = self.color_space
                self.compositor.submit(eye, ovr_texture)
        except Exception as e:
            if hasattr(self, 'on_texture_submit_error'):
                if not self.on_texture_submit_error_notified:
                    print("WARNING: 'on_texture_submit_error()' is deprecated and will be removed in a future release")
                    self.on_texture_submit_error_notified = True
                self.on_texture_submit_error(e)
            else:
                if self.submit_error_handler is not None:
                    self.submit_error_handler(e)
                else:
                    # by default, just reraise the exception
                    raise e

    def left_cb(self, cbdata):
        """
        Draw callback that is linked with the left eye camera. Once the frame rendering is done, it will submit
        the result to OpenVR, if the eyes are submitted separately.
        """

        # Perform the actual Draw job
        cbdata.upcall()
        if not self.submit_together:
            # Submit the left eye texture if we are not submitting left and right textures at the same time
            self.submit_texture(openvr.Eye_Left, self.left_texture)

    def right_cb(self, cbdata):
        """
        Draw callback that is linked with the right eye camera. Once the frame rendering is done, it will submit
        the result to OpenVR.
        """

        # Perform the actual Draw job
        cbdata.upcall()
        if self.submit_together:
            # Submit the left eye texture if we are submitting left and right textures at the same time
            self.submit_texture(openvr.Eye_Left, self.left_texture)
        # In any case, submit the right eye texture
        self.submit_texture(openvr.Eye_Right, self.right_texture)

    def get_pose_modelview(self, pose):
        """
        Return the transform matrix corresponding to the given pose in the tracked space reference frame
        """

        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        return self.coord_mat_inv * modelview * self.coord_mat

    def get_action_pose(self, action, device=openvr.k_ulInvalidInputValueHandle):
        """
        Return the pose associated with the given action. The action must be a pose action.

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device : Handle of a device. If specified, restrict the pose to the linked device.
        """

        pose_data = self.vr_input.getPoseActionDataForNextFrame(
            action,
            openvr.TrackingUniverseStanding,
            device,
        )
        return pose_data

    def get_digital_action_rising_edge(self, action, device_path=False):
        """
        Returns true if the action is active and had a rising edge

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path is not None:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        return action_data.bActive and action_data.bChanged and action_data.bState, device_path

    def get_digital_action_falling_edge(self, action, device_path=False):
        """
        Returns true if the action is active and had a falling edge

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        return action_data.bActive and action_data.bChanged and not action_data.bState, device_path

    def get_digital_action_state(self, action, device_path=False):
        """
        Returns true if the action is active and its state is true

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        return action_data.bActive and action_data.bState, device_path

    def get_analog_action_value(self, action, device_path=False):
        """
        Returns the analog value of the action, if it is active, else None

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        analog_data = self.vr_input.getAnalogActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path:
            if analog_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(analog_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        if analog_data.bActive:
            return analog_data, device_path
        else:
            return None, None

    def get_bone_transform(self, bone_transform_array, bone_index):
        """
        Returns the transform related to the given bone. The transform is returned as a translation vector and
        a quaternion rotation.

        bone_transform_array : Array containing all the bones transformations

        bone_index : Index of the bone transformation to retrieve.
        """

        if bone_index < len(bone_transform_array):
            bone_transform = bone_transform_array[bone_index]
            if bone_transform is not None:
                position = bone_transform.position
                orientation = bone_transform.orientation
                return self.coord_mat.xform(self.convert_vector(position)), self.coord_mat.xform(self.convert_quaternion(orientation))
            else:
                print("ERROR: No transform data for bone {}".format(bone_index))
        else:
            print("ERROR: Invalid bone index {}".format(bone_index))
        return LVector4(), LQuaternion()

    def get_bone_transform_mat(self, bone_transform_array, bone_index):
        """
        Returns the transform related to the given bone. The transform is returned as a 4-dimensions transform matrix.

        bone_transform_array : Array containing all the bones transformations

        bone_index : Index of the bone transformation to retrieve.
        """

        if bone_index < len(bone_transform_array):
            bone_transform = bone_transform_array[bone_index]
            if bone_transform is not None:
                position = bone_transform.position
                orientation = bone_transform.orientation
                transform_mat = LMatrix4()
                compose_matrix(transform_mat, LVector3(1), LVector3(0), self.convert_quaternion(orientation).get_hpr(), self.convert_vector(position).get_xyz())
                return self.coord_mat_inv * transform_mat * self.coord_mat
            else:
                print("ERROR: No transform data for bone {}".format(bone_index))
        else:
            print("ERROR: Invalid bone index {}".format(bone_index))
        return LMatrix4.ident_mat()

    def get_skeletal_bone_data(self, action, device_path=False):
        """
        Returns the skeleton bone data provided by the given action. The individual bone transform must be extracted
        using either get_bone_transform() or get_bone_transform_mat()

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        # Retrieve the data of the action, this will gives the active status and the device.
        skeleton_data = self.vr_input.getSkeletalActionData(action)
        if skeleton_data.bActive == 0:
            return None, None

        # Retrieve the bones data from the action. The bone transforms are all defined in their parent's reference frame,
        # and the default range is as if there is no controller.
        boneCount = self.vr_input.getBoneCount(action)
        bone_transform_arr = [openvr.VRBoneTransform_t()] * boneCount
        arr = (openvr.VRBoneTransform_t * len(bone_transform_arr))(*bone_transform_arr)
        self.vr_input.getSkeletalBoneData(action, openvr.VRSkeletalTransformSpace_Parent, openvr.VRSkeletalMotionRange_WithoutController, arr)

        if device_path:
            if skeleton_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(skeleton_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        return arr, device_path

    def get_skeletal_reference_transform(self, action, pose, device_path=False):
        """
        Returns the skeleton bone reference data provided by the given action. The individual bone transform must be
        extracted using either get_bone_transform() or get_bone_transform_mat()

        action : OpenVR handle of the action, can be retrieved using vr_input.getActionHandle()

        pose : Reference pose to return.

        device_path : If true, returns also the handle of the device that triggered the action.
        """

        skeleton_data = self.vr_input.getSkeletalActionData(action)
        if skeleton_data.bActive == 0:
            if device_path:
                return None, openvr.k_ulInvalidInputValueHandle
            else:
                return None, None

        boneCount = self.vr_input.getBoneCount(action)
        bone_transform_arr = [openvr.VRBoneTransform_t()] * boneCount
        arr = (openvr.VRBoneTransform_t * len(bone_transform_arr))(*bone_transform_arr)
        self.vr_input.getSkeletalReferenceTransforms(action, openvr.VRSkeletalTransformSpace_Parent, pose, arr)

        if device_path:
            if skeleton_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(skeleton_data.activeOrigin)
                device_path = origin_info.devicePath
            else:
                device_path = openvr.k_ulInvalidInputValueHandle
        return arr, device_path

    def list_devices(self):
        """
        Debug method printing the detected tracked devices
        """

        if self.poses is None: return 
        for i in range(1, len(self.poses)):
            pose = self.poses[i]
            if not pose.bPoseIsValid:
                continue
            model_name = openvr.VRSystem().getStringTrackedDeviceProperty(i, openvr.Prop_RenderModelName_String)
            model_serial = openvr.VRSystem().getStringTrackedDeviceProperty(i, openvr.Prop_SerialNumber_String)
            print(i, model_name, model_serial)
