![Addon Banner](res/banner.jpg)

# Mitsuba Blender Add-on

[![Nightly Release](https://github.com/mitsuba-renderer/mitsuba-blender/actions/workflows/nightly_release.yml/badge.svg)](https://github.com/mitsuba-renderer/mitsuba-blender/actions/workflows/nightly_release.yml)

This add-on integrates the Mitsuba renderer into Blender.

## Main Features

* **Mitsuba scene import**: Import Mitsuba XML scenes in Blender to edit and preview them. Materials are converted to Cycles shader node trees.

* **Mitsuba scene export**: Export a Blender scene to a Mitsuba XML scene for rendering.

More in-depth information about the features of the add-on are available on the [wiki](https://github.com/mitsuba-renderer/mitsuba-blender/wiki).

## Installation

- Download the latest release from the [release section](https://github.com/mitsuba-renderer/mitsuba-blender/releases).
- In Blender, go to **Edit** -> **Preferences** -> **Add-ons** -> **Install**.
- Select the downloaded ZIP archive.
- Find the add-on using the search bar and enable it.
- To point the add-on to the Mitsuba dependencies, either click on *Install dependencies using pip* to download the latest package, or check *Use custom Mitsuba path* and browse to your Mitsuba build directory.

## Common issues

:warning: For versions of blender prior to 3.5, you may encounter the error message `Failed to load Mitsuba package` after installing the dependencies via pip. In order to fix that, you need to run blender with the `--python-use-system-env` flag in order for it to correctly pick up the dependencies. In order to do so, find the path to the blender executable, and in a command prompt run:
```
<path_to_blender> --python-use-sytem-env
```

You can refer to the [Installation & Update Guide](https://github.com/mitsuba-renderer/mitsuba-blender/wiki/Installation-&-Update-Guide) on the wiki for more detailed instructions.

### Supported versions

Blender version should be at least `2.93`. The addon has been extensively tested
on LTS versions of blender (`3.6`, `4.2`). We recommend using those whenever
possible.

# New Custom Features
## Note: dependency installations
Additional dependencies are installed into the `deps/` folder of this repo and linked to the Blender runtime

## Custom Import: Import YML Configs
Usage: Menu option `File -> Import -> Custom Config (.yml)`

This option allows for importing predefined scene descriptions into Blender. On import, will wipe everything in the current open workspace and replace it with the config contents.

Supports primitive objects, color and image bitmap textures, textured meshes (from obj, stl, ply, fbx file format), environmental maps, lighting, cameras. See `.yml` files in https://github.com/twosixlabs/gard-mit/tree/renderer_nn_module/configs for example configs. 
 
## Custom Export: Export to Mitsuba WITH Auxiliary Optimization Information
Usage: Menu option `File -> Export -> Mitsuba (.xml) with Aux Data (.yml)`

This export option extends the base plugin's Export to Mitsuba feature (`File -> Export -> Mitsuba (.xml)`) by exporting an additional `auxiliary_outputs.yml` file in the same directory as the rest of the scene export. THis file records exportable optimization parameters (currently supports cameras and textures). 

When exporting with the `File -> Export -> Mitsuba (.xml) with Aux Data (.yml)` option, the objects marked as optimizable will be saved into an `auxiliary_outputs.yml` which can be processed downstream by our custom [Differential Renderer module](https://github.com/twosixlabs/gard-mit/blob/renderer_nn_module/src/renderer_module.py).


## Marking scene parameters as optimizable
Currently the plugin supports marking object materials and camaeras for downstream optimizations, e.g. to optimize a patch texture or whether to use a camera or not in a multi-view optimization. 

* To mark as texture or camera as optimizable on import via yml config, add the line

```optimizable: true``` 

to the config for the respective object. E.g.

```
objects:
  - type: MESH
    filepath: "path/to/mesh.obj"
    name: MyMesh
    material:
      name: TexturedMaterial
      shader: BSDF
      texture:
        type: IMAGE
        filepath: "path/to/some/bitmap.png"
        optimizable: true
```

On import into the Blender UI, this property is viewable and editable as a custom property of the object:

- For textures: click on `Material` tab/icon (note: NOT `Object`!) in the right sidebar, scroll down to `Custom Properties` section
- For cameras: with the camera object selected, click on the  `Object` tab/icon in the right sidebar, scroll down to `Custom Properties` section

If not explicitly defined as optimizable in the config, textures and cameras are left as not optimizable by default in the UI. To add the `optimizable` flag to a texture or camera without the field (e.g. user-added object to the scene), you can add the custom property yourself in the appropriate `Custom Properties` section: click `+ New`, edit the property to have type Boolean and name `optimizable`. This will be preserved upon export.