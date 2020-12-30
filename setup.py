from setuptools import setup

__version__ = ''
exec(open('p3dopenvr/version.py').read())
helpers = Extension('helpers',
                    sources = ['helpers.c'])
setup(
    version=__version__,
    keywords='panda3d openvr',
    packages=['p3dopenvr'],
    python_requires='>=3.5',
    install_requires=[
        'panda3d',
        'openvr',
    ],
    ext_modules = [helpers]
)
