from direct.showbase.ShowBase import ShowBase

from p3dopenvr.p3dopenvr import P3DOpenVR

import openvr
import os

class MinimalOpenVR(P3DOpenVR):
    classes_map = { openvr.TrackedDeviceClass_Invalid: 'Invalid',
                    openvr.TrackedDeviceClass_HMD: 'HMD',
                    openvr.TrackedDeviceClass_Controller: 'Controller',
                    openvr.TrackedDeviceClass_GenericTracker: 'Generic tracker',
                    openvr.TrackedDeviceClass_TrackingReference: 'Tracking reference',
                    openvr.TrackedDeviceClass_DisplayRedirect: 'Display redirect',
                  }

    roles_map = { openvr.TrackedControllerRole_Invalid: 'Invalid',
                  openvr.TrackedControllerRole_LeftHand: 'Left',
                  openvr.TrackedControllerRole_RightHand: 'Right',
                  openvr.TrackedControllerRole_OptOut: 'Opt out',
                  openvr.TrackedControllerRole_Treadmill: 'Treadmill',
                  openvr.TrackedControllerRole_Stylus: 'Stylus',
                }

    buttons_map = { openvr.k_EButton_System: 'System',
                    openvr.k_EButton_ApplicationMenu: 'Application Menu',
                    openvr.k_EButton_Grip: 'Grip',
                    openvr.k_EButton_DPad_Left: 'Pad left',
                    openvr.k_EButton_DPad_Up: 'Pad up',
                    openvr.k_EButton_DPad_Right: 'Pad right',
                    openvr.k_EButton_DPad_Down: 'Pad down',
                    openvr.k_EButton_A: 'A',
                    openvr.k_EButton_ProximitySensor: 'Proximity sensor',
                    openvr.k_EButton_Axis0: 'Axis 0',
                    openvr.k_EButton_Axis1: 'Axis 1',
                    openvr.k_EButton_Axis2: 'Axis 2',
                    openvr.k_EButton_Axis3: 'Axis 3',
                    openvr.k_EButton_Axis4: 'Axis 4',
                    #openvr.k_EButton_SteamVR_Touchpad: 'Touchpad',
                    #openvr.k_EButton_SteamVR_Trigger: 'Trigger',
                    #openvr.k_EButton_Dashboard_Back: 'Dashboard back',
                    #openvr.k_EButton_IndexController_A: 'Controller A',
                    #openvr.k_EButton_IndexController_B: 'Controller B',
                    #openvr.k_EButton_IndexController_JoyStick: 'Controller joystick',
                  }

    button_events_map = { openvr.VREvent_ButtonPress: 'Press',
                          openvr.VREvent_ButtonUnpress: 'Unpress',
                          openvr.VREvent_ButtonTouch: 'Touch',
                          openvr.VREvent_ButtonUntouch: 'Untouch'
                        }

    def button_event(self, event):
        device_index = event.trackedDeviceIndex
        device_class = self.vr_system.getTrackedDeviceClass(device_index)
        if device_class != openvr.TrackedDeviceClass_Controller:
            return
        button_id = event.data.controller.button
        button_name = self.buttons_map.get(button_id)
        if button_name is None:
            button_name = 'Unknown button ({})'.format(button_id)
        role = self.vr_system.getControllerRoleForTrackedDeviceIndex(device_index)
        role_name = self.roles_map.get(role)
        if role_name is None:
            role_name = 'Unknown role ({})'.format(role)
        event_name = self.button_events_map.get(event.eventType)
        if event_name is None:
            event_name = 'Unknown event ({})'.format(event.eventType)
        print(role_name, button_name, event_name)

    def device_event(self, event, action):
        device_index = event.trackedDeviceIndex
        device_class = self.vr_system.getTrackedDeviceClass(device_index)
        class_name = self.classes_map.get(device_class)
        if class_name is None:
            class_name = 'Unknown class ({})'.format(class_name)
        print('Device {} {} ({})'.format(event.trackedDeviceIndex, action, class_name))

    def process_vr_event(self, event):
        if event.eventType == openvr.VREvent_TrackedDeviceActivated:
            self.device_event(event, 'attached')
        if event.eventType == openvr.VREvent_TrackedDeviceDeactivated:
            self.device_event(event, 'deactivated')
        elif event.eventType == openvr.VREvent_TrackedDeviceUpdated:
            self.device_event(event, 'updated')
        elif event.eventType in (openvr.VREvent_ButtonPress,
                                 openvr.VREvent_ButtonUnpress,
                                 openvr.VREvent_ButtonTouch,
                                 openvr.VREvent_ButtonUntouch):
            self.button_event(event)

    def new_tracked_device(self, device_index, device_anchor):
        print("Adding new device", device_anchor.name)
        device_class = self.vr_system.getTrackedDeviceClass(device_index)
        if device_class == openvr.TrackedDeviceClass_Controller:
            model = loader.loadModel("box")
            model.reparent_to(device_anchor)
            model.set_scale(0.1)
        else:
            print(device_class)
            model = loader.loadModel("camera")
            model.reparent_to(device_anchor)
            model.set_scale(0.1)

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
