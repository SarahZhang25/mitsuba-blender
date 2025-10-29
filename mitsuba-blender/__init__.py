bl_info = {
    'name': 'Mitsuba-Blender',
    'author': 'Baptiste Nicolet, Dorian Ros, Rami Tabbara',
    'version': (0, 1),
    'blender': (4, 0, 0),
    'category': 'Render',
    'location': 'File menu, render engine menu',
    'description': 'Mitsuba integration for Blender',
    'wiki_url': 'https://github.com/mitsuba-renderer/mitsuba-blender/wiki',
    'tracker_url': 'https://github.com/mitsuba-renderer/mitsuba-blender/issues/new/choose',
    'warning': 'alpha',
}

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator, AddonPreferences
from bpy.utils import register_class, unregister_class

import os
import sys
import subprocess
import logging
import importlib

from . import io, engine

DEPS_MITSUBA_VERSION = '3.5.0'

# We will install add-on dependencies to this "deps" folder and add it to the sys.path
ADDON_DIR = os.path.dirname(__file__)
DEPS_PATH = os.path.join(ADDON_DIR, "deps")
if DEPS_PATH not in sys.path:
    sys.path.insert(0, DEPS_PATH)


def ensure_module(module_name):
    """Check if module exists, install it into deps if missing."""
    if importlib.util.find_spec(module_name) is None:
        subprocess.run([sys.executable, "-m", "pip", "install", pip_name, "--target", DEPS_PATH])

    
def get_addon_preferences(context):
    return context.preferences.addons[__name__].preferences

def init_mitsuba(context):
    # Make sure we can load mitsuba from blender
    try:
        os.environ['DRJIT_NO_RTLD_DEEPBIND'] = 'True'
        should_reload_mitsuba = 'mitsuba' in sys.modules
        import mitsuba
        # If mitsuba was already loaded and we change the path, we need to reload it, since the import above will be ignored
        if should_reload_mitsuba:
            import importlib
            importlib.reload(mitsuba)
        mitsuba.set_variant('scalar_rgb')
        # Set the global threading environment
        from mitsuba import ThreadEnvironment
        bpy.types.Scene.thread_env = ThreadEnvironment()
        return True
    except ModuleNotFoundError:
        return False

def try_register_mitsuba(context):
    prefs = get_addon_preferences(context)
    prefs.mitsuba_dependencies_status_message = ''

    could_init_mitsuba = False
    if prefs.using_mitsuba_custom_path:
        update_additional_custom_paths(prefs, context)
        could_init_mitsuba = init_mitsuba(context)
        if could_init_mitsuba:
            import mitsuba
            prefs.mitsuba_custom_version = mitsuba.__version__
            if prefs.has_valid_mitsuba_custom_version:
                prefs.mitsuba_dependencies_status_message = f'Found custom Mitsuba v{prefs.mitsuba_custom_version}.'
            else:
                prefs.mitsuba_dependencies_status_message = f'Found custom Mitsuba v{prefs.mitsuba_custom_version}. Supported version is v{DEPS_MITSUBA_VERSION}.'
        else:
            prefs.mitsuba_dependencies_status_message = 'Failed to load custom Mitsuba. Please verify the path to the build directory.'
    elif prefs.has_pip_dependencies:
        if prefs.has_valid_dependencies_version:
            could_init_mitsuba = init_mitsuba(context)
            if could_init_mitsuba:
                import mitsuba
                prefs.mitsuba_dependencies_status_message = f'Found pip Mitsuba v{mitsuba.__version__}.'
            else:
                prefs.mitsuba_dependencies_status_message = 'Failed to load Mitsuba package.'
        else:
            prefs.mitsuba_dependencies_status_message = f'Found pip Mitsuba v{prefs.installed_dependencies_version}. Supported version is v{DEPS_MITSUBA_VERSION}.'
    else:
        prefs.mitsuba_dependencies_status_message = 'Mitsuba dependencies not installed.'

    prefs.is_mitsuba_initialized = could_init_mitsuba

    if could_init_mitsuba:
        io.register()
        engine.register()

    return could_init_mitsuba

def try_unregister_mitsuba():
    '''
    Try unregistering Addon classes.
    This may fail if Mitsuba wasn't found, hence the try catch guard
    '''
    try:
        io.unregister()
        engine.unregister()
        return True
    except RuntimeError:
        return False

def try_reload_mitsuba(context):
    try_unregister_mitsuba()
    if try_register_mitsuba(context):
        # Save user preferences
        bpy.ops.wm.save_userpref()

def ensure_pip():
    result = subprocess.run([sys.executable, '-m', 'ensurepip'], capture_output=True)
    return result.returncode == 0

def check_pip_dependencies(context, requirements):
    """Check if the required pip dependencies are installed.

    Args:
        context: Blender context
        requirements: List of requirements to check (i.e. read from extra_pip_dependencies.txt)
    """
    prefs = get_addon_preferences(context)
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True)
    deps_path_result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--path', DEPS_PATH], capture_output=True)

    prefs.has_pip_dependencies = False
    prefs.has_valid_dependencies_version = False

    if result.returncode == 0 and deps_path_result.returncode == 0:
        output_lines = result.stdout.decode('utf-8').splitlines(keepends=False)[2:]  # Skip header lines
        output_lines += deps_path_result.stdout.decode('utf-8').splitlines(keepends=False)[2:]

        packages = {line.split()[0] : line.split()[1] for line in output_lines}

        has_all_requirements = all([req.split('==')[0] in packages for req in requirements])
        logging.info(f"has all requirements: {has_all_requirements}")
        if has_all_requirements:
            prefs.has_pip_dependencies = True
            prefs.installed_dependencies_version = packages["mitsuba"]

def clean_additional_custom_paths(self, context):
    # Remove old values from system PATH and sys.path
    if self.additional_python_path in sys.path:
        sys.path.remove(self.additional_python_path)
    if self.additional_path and self.additional_path in os.environ['PATH']:
        items = os.environ['PATH'].split(os.pathsep)
        items.remove(self.additional_path)
        os.environ['PATH'] = os.pathsep.join(items)

def update_additional_custom_paths(self, context):
    build_path = bpy.path.abspath(self.mitsuba_custom_path)
    if len(build_path) > 0:
        clean_additional_custom_paths(self, context)

        # Add path to the binaries to the system PATH
        self.additional_path = build_path
        if self.additional_path not in os.environ['PATH']:
            os.environ['PATH'] += os.pathsep + self.additional_path

        # Add path to python libs to sys.path
        self.additional_python_path = os.path.join(build_path, 'python')
        if self.additional_python_path not in sys.path:
            # NOTE: We insert in the first position here, so that the custom path
            #       supersede the pip version
            sys.path.insert(0, self.additional_python_path)

class MITSUBA_OT_install_pip_dependencies(Operator):
    bl_idname = 'mitsuba.install_pip_dependencies'
    bl_label = 'Install Mitsuba pip dependencies'
    bl_description = 'Use pip to install the add-on\'s required dependencies'

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return not prefs.has_pip_dependencies or not prefs.has_valid_dependencies_version

    def execute(self, context):
        """Install the required pip dependencies for mitsuba-blender."""
        with open(os.path.join(os.path.dirname(__file__), 'extra_pip_dependencies.txt'), 'r', encoding='utf-8') as f:
            requirements = f.read().splitlines()  # format: package==version
        requirements.append(f"mitsuba=={DEPS_MITSUBA_VERSION}")

        for req in requirements:
            result = subprocess.run([
                sys.executable, '-m','pip', 'install', req, '--force-reinstall',
                '--target', DEPS_PATH 
            ], capture_output=False, check=True)

            if result.returncode != 0:
                self.report({'ERROR'}, f'Failed to install {req} with return code {result.returncode}.')
                return {'CANCELLED'}

        check_pip_dependencies(context, requirements)

        try_reload_mitsuba(context)

        return {'FINISHED'}

def update_using_mitsuba_custom_path(self, context):
    self.require_restart = True
    if self.using_mitsuba_custom_path:
        update_mitsuba_custom_path(self, context)
    else:
        clean_additional_custom_paths(self, context)

def update_mitsuba_custom_path(self, context):
    if self.is_mitsuba_initialized:
        self.require_restart = True
    if self.using_mitsuba_custom_path and len(self.mitsuba_custom_path) > 0:
        update_additional_custom_paths(self, context)
        if not self.is_mitsuba_initialized:
            try_reload_mitsuba(context)

def update_installed_dependencies_version(self, context):
    self.has_valid_dependencies_version = self.installed_dependencies_version == DEPS_MITSUBA_VERSION

def update_mitsuba_custom_version(self, context):
    self.has_valid_mitsuba_custom_version = self.mitsuba_custom_version == DEPS_MITSUBA_VERSION

class MitsubaPreferences(AddonPreferences):
    bl_idname = __name__

    is_mitsuba_initialized : BoolProperty(
        name = 'Is Mitsuba initialized',
    )

    has_pip_dependencies : BoolProperty(
        name = 'Has pip dependencies installed',
    )

    installed_dependencies_version : StringProperty(
        name = 'Installed Mitsuba dependencies version string',
        default = '',
        update = update_installed_dependencies_version,
    )

    has_valid_dependencies_version : BoolProperty(
        name = 'Has the correct version of dependencies'
    )

    mitsuba_dependencies_status_message : StringProperty(
        name = 'Mitsuba dependencies status message',
        default = '',
    )

    require_restart : BoolProperty(
        name = 'Require a Blender restart',
    )

    # Advanced settings

    using_mitsuba_custom_path : BoolProperty(
        name = 'Using custom Mitsuba path',
        update = update_using_mitsuba_custom_path,
    )

    mitsuba_custom_path : StringProperty(
        name = 'Custom Mitsuba path',
        description = 'Path to the custom Mitsuba build directory',
        default = '',
        subtype = 'DIR_PATH',
        update = update_mitsuba_custom_path,
    )

    mitsuba_custom_version : StringProperty(
        name = 'Custom Mitsuba build version',
        default = '',
        update = update_mitsuba_custom_version,
    )

    has_valid_mitsuba_custom_version : BoolProperty(
        name = 'Has the correct version of custom Mitsuba build'
    )

    additional_path : StringProperty(
        name = 'Addition to PATH',
        default = '',
        subtype = 'DIR_PATH',
    )

    additional_python_path : StringProperty(
        name = 'Addition to sys.path',
        default = '',
        subtype = 'DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        icon = 'ERROR'
        row.alert = True
        if self.require_restart:
            self.mitsuba_dependencies_status_message = 'A restart is required to apply the changes.'
        elif self.is_mitsuba_initialized and (not self.using_mitsuba_custom_path or (self.using_mitsuba_custom_path and self.has_valid_mitsuba_custom_version)):
            icon = 'CHECKMARK'
            row.alert = False
        row.label(text=self.mitsuba_dependencies_status_message, icon=icon)

        operator_text = 'Install dependencies'
        if self.has_pip_dependencies and not self.has_valid_dependencies_version:
            operator_text = 'Update dependencies'
        layout.operator(MITSUBA_OT_install_pip_dependencies.bl_idname, text=operator_text)

        box = layout.box()
        box.label(text='Advanced Settings')
        box.prop(self, 'using_mitsuba_custom_path', text=f'Use custom Mitsuba path (Supported version is v{DEPS_MITSUBA_VERSION})')
        if self.using_mitsuba_custom_path:
            box.prop(self, 'mitsuba_custom_path')

classes = (
    MITSUBA_OT_install_pip_dependencies,
    MitsubaPreferences,
)

def register():
    for cls in classes:
        register_class(cls)

    context = bpy.context
    prefs = get_addon_preferences(context)
    prefs.require_restart = False
    if not ensure_pip():
        raise RuntimeError('Cannot activate mitsuba-blender add-on. Python pip module cannot be initialized.')

    with open(os.path.join(os.path.dirname(__file__), 'extra_pip_dependencies.txt'), 'r', encoding='utf-8') as f:
        requirements = f.read().splitlines()  # format: package==version
    check_pip_dependencies(context, requirements)

    if try_register_mitsuba(context):
        import mitsuba
        print(f'mitsuba-blender v{".".join(str(e) for e in bl_info["version"])}{bl_info["warning"] if "warning" in bl_info else ""} registered (with mitsuba v{mitsuba.__version__})')

def unregister():
    for cls in classes:
        unregister_class(cls)
    try_unregister_mitsuba()
