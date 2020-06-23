from panda3d.core import load_prc_file_data, NodePath, CardMaker
from panda3d.core import LMatrix3, LMatrix4, CS_yup_right, CS_default
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
    def __init__(self):
        self.vr_system = None
        self.vr_input = None
        self.compositor = None
        self.poses = None
        self.action_url = None
        self.action_path = None
        self.action_set_handle = None
        self.buffers = []
        self.nextsort = base.win.getSort() - 1000
        self.tracking_space = None
        self.hmd_anchor = None
        self.left_eye_anchor = None
        self.right_eye_anchor = None
        self.left_cam = None
        self.right_cam = None
        self.tracked_devices_anchors = {}
        self.empty_world = None
        self.coord_mat = LMatrix4.convert_mat(CS_yup_right, CS_default)
        self.coord_mat_inv = LMatrix4.convert_mat(CS_default, CS_yup_right)

    def create_buffer(self, name, texture, width, height, fbprops):
        winprops = WindowProperties()
        winprops.set_size(width, height)
        props = FrameBufferProperties(FrameBufferProperties.get_default())
        props.set_back_buffers(0)
        props.set_rgb_color(1)
        if fbprops is not None:
            props.add_properties(fbprops)

        buffer = base.win.make_texture_buffer(name, width, height, to_ram=False, fbp=props)
        if buffer is not None:
            buffer.clear_render_textures()
            buffer.set_sort(self.nextsort)
            self.nextsort += 1
            buffer.add_render_texture(texture, GraphicsOutput.RTMBindOrCopy, GraphicsOutput.RTPColor)
        else:
            print("COULD NOT CREATE BUFFER")
        return buffer

    def create_renderer(self, name, camera, width, height, callback, cc=None):
        texture = Texture()
        texture.set_wrap_u(Texture.WMClamp)
        texture.set_wrap_v(Texture.WMClamp)
        texture.set_minfilter(Texture.FT_linear)
        texture.set_magfilter(Texture.FT_linear)
        fbprops = FrameBufferProperties()
        fbprops.setRgbaBits(1, 1, 1, 1)
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
        cam_node = Camera(name)
        lens = MatrixLens()
        lens.set_user_mat(projection_mat)
        cam_node.set_lens(lens)
        return cam_node

    def convert_mat(self, mat):
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

    def disable_main_cam(self):
        self.empty_world = NodePath()
        base.camera.reparent_to(self.empty_world)

    def replicate(self, texture):
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
        base.cam.node().set_lens(lens)
        base.cam.reparent_to(self.quad)

    def init(self, near=0.2, far=500.0, root=None):
        poses_t = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        self.poses = poses_t()
        self.vr_system = openvr.init(openvr.VRApplication_Scene)
        width, height = self.vr_system.getRecommendedRenderTargetSize()
        self.compositor = openvr.VRCompositor()
        self.vr_input = openvr.VRInput()
        if self.compositor is None:
            raise Exception("Unable to create compositor") 

        if root is None:
            root = render
        self.tracking_space = root.attach_new_node('tracking-space')
        self.hmd_anchor = self.tracking_space.attach_new_node('hmd-anchor')
        self.left_eye_anchor = self.hmd_anchor.attach_new_node('left-eye')
        self.right_eye_anchor = self.hmd_anchor.attach_new_node('right-eye')

        self.projection_left = self.coord_mat_inv * self.convert_mat(self.vr_system.getProjectionMatrix(openvr.Eye_Left, near, far))
        self.projection_right = self.coord_mat_inv * self.convert_mat(self.vr_system.getProjectionMatrix(openvr.Eye_Right, near, far))

        left_cam_node = self.create_camera('left-cam', self.projection_left)
        right_cam_node = self.create_camera('right-cam', self.projection_right)

        self.left_cam = self.left_eye_anchor.attach_new_node(left_cam_node)
        self.right_cam = self.right_eye_anchor.attach_new_node(right_cam_node)

        self.left_texture = self.create_renderer('left-buffer', self.left_cam, width, height, self.left_cb)
        self.right_texture = self.create_renderer('right-buffer', self.right_cam, width, height, self.right_cb)

        self.disable_main_cam()
        self.replicate(self.left_texture)

        self.init_action()

        taskMgr.add(self.update_poses_task, "openvr-update-poses", sort=-1000)

    def init_action(self):
        pass

    def load_action_manifest(self, action_filename, action_path):
        print("Loading", action_filename)
        self.vr_input.setActionManifestPath(action_filename)
        self.action_path = action_path
        self.action_set_handle = self.vr_input.getActionSetHandle(self.action_path)

    def update_hmd(self, pose):
        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        self.hmd_anchor.set_mat(self.coord_mat_inv * modelview * self.coord_mat)
        view_left = self.convert_mat(self.vr_system.getEyeToHeadTransform(openvr.Eye_Left))
        self.left_eye_anchor.set_mat(self.coord_mat_inv * view_left * self.coord_mat)
        view_right = self.convert_mat(self.vr_system.getEyeToHeadTransform(openvr.Eye_Right))
        self.right_eye_anchor.set_mat(self.coord_mat_inv * view_right * self.coord_mat)

    def new_tracked_device(self, device_index, device_anchor):
        pass

    def update_tracked_device(self, device_index, pose):
        if not device_index in self.tracked_devices_anchors:
            model_name = self.vr_system.getStringTrackedDeviceProperty(device_index, openvr.Prop_RenderModelName_String)
            np_name = str(device_index) + ':' + model_name
            device_anchor = self.tracking_space.attach_new_node(np_name)
            self.tracked_devices_anchors[device_index] = device_anchor
            self.new_tracked_device(device_index, device_anchor)
        else:
            device_anchor = self.tracked_devices_anchors[device_index]
        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        modelview = self.coord_mat_inv * modelview * self.coord_mat
        device_anchor.set_mat(modelview)

    def update_tracked_devices(self):
        for i in range(1, len(self.poses)):
            pose = self.poses[i]
            if not pose.bPoseIsValid:
                continue
            self.update_tracked_device(i, pose)

    def process_vr_event(self, event):
        pass

    def poll_events(self):
        event = openvr.VREvent_t()
        has_events = self.vr_system.pollNextEvent(event)
        while has_events:
            self.process_vr_event(event)
            has_events = self.vr_system.pollNextEvent(event)

    def update_action(self):
        pass

    def update_action_state(self):
        if self.action_set_handle is None: return
        action_sets = (openvr.VRActiveActionSet_t * 1)()
        action_set = action_sets[0]
        action_set.ulActionSet = self.action_set_handle
        self.vr_input.updateActionState(action_sets)
        self.update_action()

    def update_poses_task(self, task):
        if self.compositor is None:
            return task.cont
        self.compositor.waitGetPoses(self.poses, None)
        self.poll_events()
        hmd_pose = self.poses[openvr.k_unTrackedDeviceIndex_Hmd]
        if not hmd_pose.bPoseIsValid:
            print("HMD pose is not valid")
            return task.cont
        self.update_hmd(hmd_pose)
        self.update_tracked_devices()
        self.update_action_state()
        return task.cont

    def submit_texture(self, eye, texture):
        texture_context = texture.prepare_now(0, base.win.gsg.prepared_objects, base.win.gsg)
        handle = texture_context.get_native_id()
        if handle != 0:
            ovr_texture = openvr.Texture_t()
            ovr_texture.handle = texture_context.get_native_id()
            ovr_texture.eType = openvr.TextureType_OpenGL
            ovr_texture.eColorSpace = openvr.ColorSpace_Gamma
            self.compositor.submit(eye, ovr_texture)

    def left_cb(self, cbdata):
        cbdata.upcall()
        self.submit_texture(openvr.Eye_Right, self.right_texture)

    def right_cb(self, cbdata):
        cbdata.upcall()
        self.submit_texture(openvr.Eye_Left, self.left_texture)

    def get_pose_modelview(self, pose):
        modelview = self.convert_mat(pose.mDeviceToAbsoluteTracking)
        return self.coord_mat_inv * modelview * self.coord_mat

    def get_action_pose(self, action):
        pose_data = self.vr_input.getPoseActionDataForNextFrame(
            action,
            openvr.TrackingUniverseStanding,
            openvr.k_ulInvalidInputValueHandle,
        )
        return pose_data

    def get_digital_action_rising_edge(self, action, device_path=None):
        """
        Returns true if the action is active and had a rising edge
        """
        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path is not None:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
        return action_data.bActive and action_data.bChanged and action_data.bState, device_path

    def get_digital_action_falling_edge(self, action, device_path=None):
        """
        Returns true if the action is active and had a falling edge
        """
        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path is not None:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
        return action_data.bActive and action_data.bChanged and not action_data.bState, device_path

    def get_digital_action_state(self, action, device_path=None):
        """
        Returns true if the action is active and its state is true
        """
        action_data = self.vr_input.getDigitalActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path is not None:
            if action_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(action_data.activeOrigin)
                device_path = origin_info.devicePath
        return action_data.bActive and action_data.bState, device_path

    def get_analog_action_value(self, action, device_path=None):
        """
        Returns the analog value of the action, if it is active, else None
        """
        analog_data = self.vr_input.getAnalogActionData(action, openvr.k_ulInvalidInputValueHandle)
        if device_path is not None:
            if analog_data.bActive:
                origin_info = self.vr_input.getOriginTrackedDeviceInfo(analog_data.activeOrigin)
                device_path = origin_info.devicePath
        if analog_data.bActive:
            return analog_data, device_path
        else:
            return None, None

    def list_devices(self):
        if self.poses is None: return 
        for i in range(1, len(self.poses)):
            pose = self.poses[i]
            if not pose.bPoseIsValid:
                continue
            model_name = openvr.VRSystem().getStringTrackedDeviceProperty(i, openvr.Prop_RenderModelName_String)
            model_serial = openvr.VRSystem().getStringTrackedDeviceProperty(i, openvr.Prop_SerialNumber_String)
            print(i, model_name, model_serial)
