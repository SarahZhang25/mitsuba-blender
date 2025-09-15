"""Utils for parsing configuration files and setting up Blender scenes."""

import bpy


def load_config(path="scene_config.yml"):
    """Load configuration from a YAML file."""
    import yaml
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_render(scene, cfg):
    """Set up render settings based on configuration."""
    scene.render.resolution_x = cfg["render"]["resolution_x"]
    scene.render.resolution_y = cfg["render"]["resolution_y"]


def setup_camera(scene, cfg):
    """Set up camera based on configuration."""
    cam = scene.objects.get("Camera")
    # cam = bpy.data.objects.get("Camera")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
    cam.location = cfg["camera"]["location"]
    cam.rotation_euler = cfg["camera"]["rotation_euler"]


def setup_background(scene, config):
    """Set up environment background based on configuration."""
    if "background" in config and "envmap" in config["background"]:
        bg_cfg = config["background"]

        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        world = scene.world
        # world = bpy.data.worlds["World"]
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputWorld")
        bg = nodes.new(type="ShaderNodeBackground")

        if "envmap" in bg_cfg:
            env = nodes.new(type="ShaderNodeTexEnvironment")
            env.image = bpy.data.images.load(bg_cfg["envmap"]["filepath"])
            links.new(env.outputs["Color"], bg.inputs["Color"])

        if "strength" in bg_cfg:
            bg.inputs["Strength"].default_value = bg_cfg["strength"]
        links.new(bg.outputs["Background"], output.inputs["Surface"])


def setup_lights(scene, cfg):
    """Add lights to the scene based on configuration."""
    for light_cfg in cfg.get("lights", []):
        light_data = bpy.data.lights.new(light_cfg["name"], light_cfg["type"])
        light_obj = bpy.data.objects.new(light_cfg["name"], light_data)
        light_obj.location = light_cfg["location"]
        light_data.energy = light_cfg["energy"]
        scene.collection.objects.link(light_obj)


def create_material(mat_cfg):
    """Add material properties to objects based on configuration."""
    name = mat_cfg["name"]

    # If exists, reuse instead of creating duplicates
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)

    if "diffuse_color" in mat_cfg: ## solid color
        mat.diffuse_color = mat_cfg["diffuse_color"]

    elif mat_cfg.get("shader") == "BSDF": ## principled shader
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear all existing nodes
        for node in list(nodes):
            nodes.remove(node)

        # Create necessary nodes
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (400, 0)

        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # If we have a texture
        if "texture" in mat_cfg and mat_cfg["texture"]["type"] == "IMAGE":
            tex_image = nodes.new(type="ShaderNodeTexImage")
            tex_image.location = (-400, 0)
            tex_image.image = bpy.data.images.load(mat_cfg["texture"]["filepath"])
            links.new(tex_image.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        raise ValueError(f"Unknown material configuration: {mat_cfg}")

    return mat


def setup_objects(scene, cfg):
    """Add objects to the scene based on configuration."""
    for obj_cfg in cfg.get("objects", []):
        if obj_cfg["type"] == "CUBE":
            bpy.ops.mesh.primitive_cube_add(
                size=obj_cfg.get("size", 1.0),
                location=obj_cfg.get("location", (0, 0, 0)),
            )
        elif obj_cfg["type"] == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=obj_cfg.get("radius", 1.0),
                location=obj_cfg.get("location", (0, 0, 0)),
            )
        obj = bpy.context.active_object
        # scene.collection.objects.link(obj)

        # Assign material
        if "material" in obj_cfg:
            mat = create_material(obj_cfg["material"])
            obj.data.materials.clear()
            obj.data.materials.append(mat)
