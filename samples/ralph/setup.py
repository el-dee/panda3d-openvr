from setuptools import setup

setup(
    name="Ralph",
    options = {
        'build_apps': {
            'include_patterns': [
                '**/*.vrmanifest',
                '**/*.json',
                '**/*.png',
                '**/*.jpg',
                '**/*.egg',
                '**/*.pz',
            ],
            'package_data_dirs':
            {
             'openvr': [('openvr/*.dll', '', {'PKG_DATA_MAKE_EXECUTABLE'}),
                        ('openvr/*.dylib', '', {'PKG_DATA_MAKE_EXECUTABLE'}),
                        ('openvr/*.so', '', {'PKG_DATA_MAKE_EXECUTABLE'})],
            },
            'gui_apps': {
                'ralph': 'main.py',
            },
            'log_filename': '$USER_APPDATA/Ralph/output.log',
            'log_append': False,
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],
        }
    }
)
