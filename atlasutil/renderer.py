import os
import bpy

EPSILON = 0.000001

def approx_eq(a, b):
    return abs(a - b) < EPSILON

def render(filename, width, height, quads):
    # TODO handle images packed in blendfile passed in `quads`
    materials = []
    textures = []
    images = []

    bpy.ops.scene.new()
    scene = bpy.context.scene
    scene.render.use_antialiasing = False
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = filename.rsplit('.', 1)[0]
    scene.render.file_format = 'PNG'
    scene.render.color_mode = 'RGBA'

    if width > height:
        ortho_scale = width
        camera_offset_y = -(width - height) / 2.
        camera_offset_x = 0.
    else:
        ortho_scale = height
        camera_offset_y = 0.
        camera_offset_x = -(height - width) / 2.

    bpy.ops.object.add(type='CAMERA')
    camera = bpy.context.active_object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = ortho_scale
    camera.data.shift_x = 0.5
    camera.data.shift_y = 0.5
    camera.location.z = 1.0
    camera.location.x = camera_offset_x
    camera.location.y = camera_offset_y
    scene.camera = camera

    for quad in quads:
        texture_filename, rect = quad
        quad_x, quad_y, quad_width, quad_height = rect

        bpy.ops.mesh.primitive_plane_add()
        bpy.ops.object.editmode_toggle()
        bpy.ops.uv.unwrap()
        bpy.ops.object.editmode_toggle()
        quad = bpy.context.active_object
        quad.data.vertices[0].co = (0, 0, 0)
        quad.data.vertices[1].co = (0, 1, 0)
        quad.data.vertices[2].co = (1, 1, 0)
        quad.data.vertices[3].co = (1, 0, 0)
        quad.data.uv_textures.active.data[0].uv1 = (0, 0)
        quad.data.uv_textures.active.data[0].uv2 = (1, 0)
        quad.data.uv_textures.active.data[0].uv3 = (1, 1)
        quad.data.uv_textures.active.data[0].uv4 = (0, 1)

        quad.location.x = quad_x
        quad.location.y = quad_y
        quad.scale.x = quad_width
        quad.scale.y = quad_height

        existing_images = set(bpy.data.images)
        image = bpy.data.images.load(filepath=texture_filename)
        try:
            (set(bpy.data.images) - existing_images).pop()
        except KeyError:
            # image alread existing in blendfile, don't track
            pass
        else:
            images.append(image)

        image_width = image.size[0]
        image_height = image.size[1]
        if approx_eq(image_width, quad_width) and approx_eq(image_height, quad_height):
            sampling = 'none'
        elif quad_width < image_width or quad_height < image_height:
            sampling = 'down'
        elif quad_width > image_width or quad_height > image_height:
            sampling = 'up'

        bpy.ops.object.material_slot_add()
        material = bpy.data.materials.new(name='Material')
        material.use_shadeless = True
        material.use_transparency = True
        material.alpha = 0.0
        quad.material_slots[0].material = material
        texture = bpy.data.textures.new(name='Texture', type='IMAGE')
        texture.image = image
        texture.use_mipmap = False
        if sampling == 'none':
            texture.use_interpolation = False
            texture.filter_size = 0.1
        elif sampling == 'up':
            texture.use_interpolation = True
            texture.filter_size = 1.0
        elif sampling == 'down':
            texture.use_interpolation = False
            texture.filter_size = 0.25
        texture.extension = 'EXTEND'
        texture_slot = material.texture_slots.add()
        texture_slot.texture_coords = 'UV'
        texture_slot.uv_layer = quad.data.uv_textures.active.name
        texture_slot.use_map_color_diffuse = True
        texture_slot.use_map_alpha = True
        texture_slot.texture = texture
        materials.append(material)
        textures.append(texture)

    bpy.ops.render.render(write_still=True)

    for obj in scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_name(name=obj.name)
        bpy.ops.object.delete()
    for material in materials:
        bpy.data.materials.remove(material)
    for texture in textures:
        bpy.data.textures.remove(texture)
    bpy.data.scenes.remove(scene)
