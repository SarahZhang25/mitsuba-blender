
set -e

# Path to the add-on root (where this script lives)
ADDON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEPS_PATH="$ADDON_DIR/mitsuba-blender/deps"
REQ_FILE="$ADDON_DIR/mitsuba-blender/extra_pip_dependencies.txt"

# Path to Blender's bundled Python
# TODO: Fill this in with your Blender installation
BLENDER_PYTHON="/Applications/Blender.app/Contents/Resources/4.2/python/bin/python3.11"

# Make deps folder if it doesn't exist
# mkdir -p "$DEPS_PATH"

# if [[ ! -f "$REQ_FILE" ]]; then
#     echo "No requirements.txt found at $REQ_FILE"
#     exit 1
# fi

echo "Installing dependencies from $REQ_FILE into $DEPS_PATH ..."
"$BLENDER_PYTHON" -m pip install -r "$REQ_FILE" --target "$DEPS_PATH" --force-reinstall

echo "Dependencies installed successfully into $DEPS_PATH"