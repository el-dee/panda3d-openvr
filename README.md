# panda3d-openvr

This module provides basic integration of [OpenVR](https://github.com/ValveSoftware/openvr) with [Panda3D](https://www.panda3d.org/) using [pyopenvr](https://github.com/cmbruns/pyopenvr)

## Requirements

This module requires Panda3D > 1.10, pyopenvr and a implementation of OpenVR (SteamVR or OpenComposite (not tested though...)). It supports Windows, Linux and macOS platforms.

## Installation

### From wheel

    pip install panda3d-openvr

### From source

    git clone https://github.com/el-dee/panda3d-openvr
    cd panda3d-openvr
    python3 setup.py install

## Usage

To use panda3d-openvr, first import the p3dopenvr module in your application :

    from p3dopenvr.p3dopenvr import *

Then, once an instance of ShowBase is created, instanciate the VR interface and initialize it :

    myvr = P3DOpenVR()
    myvr.init()

Once done, the module will enable the VR application layer of OpenVR, create the left and right cameras and configure the rendering system to send the images of each eye to the VR compositor.

Note that, on Linux, SteamVR **must** be already running before you launch your application.

The module will create the following hierachy in the scenegraph :

* Traking space origin (tracking_space)
    * HMD anchor (hmd_anchor)
        * Left eye (left_eye_anchor)
      * Right eye (right_eye_anchor)
    * Tracked device 1
    * Tracked device 2
    * ...

The controllers will be one the the tracked devices, see the samples to know how to map the tracked device with the actual controller and find its role (left or right hand).

By default the left eye image is also rendered on the main application window.

## Documentation

There is no manual available, but the code is heavily documented and each functionality is demonstrated in one of the following examples.

## Examples

All the examples are found under samples/ directory, to launch them simply go to their directory and run:

    python3 main.py

### Minimal

In minimal you can find a minimal setup that will draw a Panda avatar in front of you, render cameras for each tracking station and a (ugly) cube where your controllers ought to be.

This example shows how to use the simple event and pose interfaces to retrieve the position of the various elements in the tracking space and the events triggered by the user.

### Actions

In samples/actions, you can find a demo using action manifest to bind actions from the user to event in the application.
This is more complex to set up than the event interface, but allows the end user to remap the actions

### Skeleton

In samples/skeleton, you can find a demo using action manifest to animate the fingers of your virtual hands using the dynamic hand skeleton provided by OpenVR.
See the sample README for where to find the hand models to use.

### Ralph

In samples/ralph you can find a heavily modified version of the Roaming Ralph demo.
In the version, you are Ralph and you can explore the space around you. Using the trackpad on the left controller, you can move forward and backward in the direction you're facing, or rotate the camera.

## License

[B3D 3-Clause](https://choosealicense.com/licenses/bsd-3-clause/)

Some parts of the code are directly coming from pyopenvr examples, which are (c) pyopenvr author "cmbruns"

Ralph demo base is copied over from Panda3D source code.
