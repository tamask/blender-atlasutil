import os
import sys
import bpy

from atlasutil import atlas

def make(blendfile, sources, atlases, textures_path='textures'):
    lib = Library(blendfile, sources, atlases, textures_path)
    lib.build()

def constrain_size(width, height, size):
    if width > size or height > size:
        scale = min(size / width, size / height)
        width *= scale
        height *= scale
    return width, height

class LibraryError(Exception): pass

class Library(object):
    def __init__(self, blendfile, sources, atlases, textures_path):
        self.basepath = os.path.dirname(blendfile)
        self.blendfile = blendfile
        self.sources = sources
        self.textures_path = textures_path

        self.atlases = []
        for atlas_def in atlases:
            margin = trim = 0.
            name, params = atlas_def[0].split('@')
            dimensions, *rest = params.split(':')
            width, height = map(float, dimensions.split('x'))
            if len(rest) > 0:
                margin = float(rest[0])
            if len(rest) > 1:
                trim = float(rest[1])
            atlas_obj = LibraryAtlas(
                self, name, atlas_def[1:], width, height, margin, trim)
            self.atlases.append(atlas_obj)

        self.atlas_textures_path = os.path.join(self.basepath, self.textures_path)
        if not os.path.exists(self.atlas_textures_path):
            os.makedirs(self.atlas_textures_path)

    def build(self):
        self.import_groups()
        for atlas in self.atlases:
            atlas.build()
        self.save_blendfile()

    def import_groups(self):
        group_names = []
        for atlas in self.atlases:
            group_names.extend(atlas.group_names)

        imported_groups = []
        for group in group_names:
            for source in self.sources:
                bpy.ops.wm.link_append(
                    filename=group,
                    filepath=os.path.join(
                        os.sep + os.sep, os.path.basename(source), 'Group', group),
                    directory=os.path.abspath(
                        os.path.join(self.basepath, source, 'Group')) + os.sep,
                    link=True, instance_groups=False)
                if group in bpy.data.groups:
                    sys.stdout.write(
                        'A  %s:%s\n' % (os.path.basename(source), group))
                    break

        diff = set(group_names) - set(bpy.data.groups.keys())
        if len(diff):
            for group in diff:
                sys.stdout.write('!  %s\n' % group)
            raise LibraryError('missing groups')

        bpy.ops.object.make_local(type='ALL')

    def save_blendfile(self):
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.abspath(os.path.join(self.basepath, self.blendfile)),
            check_existing=False)

class LibraryAtlas(atlas.Atlas):
    def __init__(
        self, library, name, groups, width, height,
        margin=0., trim=0.):

        super(LibraryAtlas, self).__init__(width, height, [], margin, trim)
        self.library = library
        self.name = name

        self.group_names = []
        self.group_sizes = {}
        for group in groups:
            if '@' in group:
                group_name, size = group.split('@', 1)
                size = float(size)
            else:
                group_name = group
                size = -1
            self.group_names.append(group_name)
            self.group_sizes[group_name] = size
        self.image_locations = []

    def build(self):
        self.make_meshes()
        self.collect_images()
        self.render()
        self.adjust_library_data()

    def make_meshes(self):
        mesh_id = 0
        for group_name in self.group_names:
            for obj in bpy.data.groups[group_name].objects:
                if not obj.type == 'MESH':
                    continue
                obj.data = obj.data.copy()
                obj.data.name = '%s_%i' % (self.name, mesh_id)
                mesh_id += 1

    def collect_images(self):
        # TODO: handle images packed in blendfile
        image_map = {}
        material_map = {}
        for group_name in self.group_names:
            max_size = self.group_sizes[group_name]
            for obj in bpy.data.groups[group_name].objects:
                if not obj.type == 'MESH':
                    continue
                mesh = obj.data
                for mslot in obj.material_slots:
                    images = material_map.setdefault(mslot.material, [])
                    for tslot in mslot.material.texture_slots:
                        if (not tslot or
                            not tslot.texture or
                            tslot.texture.type != 'IMAGE' or
                            not tslot.texture.image or
                            tslot.texture.image.source != 'FILE'):
                            continue

                        channels = []
                        if tslot.use_map_color_diffuse:
                            channels.append('color')
                        if tslot.use_map_color_spec:
                            channels.append('specular')
                        if tslot.use_map_emit:
                            channels.append('emit')
                        if not channels:
                            continue

                        image = tslot.texture.image
                        if tslot.uv_layer:
                            uv_texture = mesh.uv_textures[tslot.uv_layer]
                        else:
                            uv_texture = mesh.uv_textures.active
                        if max_size > 0:
                            width, height = constrain_size(
                                image.size[0], image.size[1], max_size)
                        else:
                            width, height = image.size
                        if image not in image_map:
                            lib_image = image_map[image] = LibraryImage(0, 0, {})
                        else:
                            lib_image = image_map[image]
                        lib_image.width = max(width, lib_image.width)
                        lib_image.height = max(height, lib_image.height)

                        if mesh not in lib_image.meshes:
                            lib_image.meshes.append(mesh)
                        if tslot.texture not in lib_image.textures:
                            lib_image.textures.append(tslot.texture)
                        if uv_texture not in lib_image.uv_textures:
                            lib_image.uv_textures.append(uv_texture)
                        for channel in channels:
                            lib_image.channels[channel] = image.filepath

                        images.append(lib_image)

        self.images = []
        for material, images in material_map.items():
            width = 0
            height = 0
            meshes = set()
            textures = set()
            uv_textures = set()
            channels = {}

            for image in images:
                width = max(width, image.width)
                height = max(height, image.height)
                meshes.update(image.meshes)
                textures.update(image.textures)
                uv_textures.update(image.uv_textures)
                channels.update(image.channels)

            lib_image = LibraryImage(width, height, channels)
            lib_image.meshes = list(meshes)
            lib_image.textures = list(textures)
            lib_image.uv_textures = list(uv_textures)

            self.images.append(lib_image)

    def render(self):
        try:
            self.chart = super(LibraryAtlas, self).render(os.path.join(
                self.library.atlas_textures_path,
                '%s_%%(channel)s.png' % self.name))
        except atlas.PackOverflow as exc:
            raise atlas.PackOverflow(self.name)

    def adjust_library_data(self):
        atlas_images = [
            bpy.data.images.load(i)
            for i in set([d for (s, c, d, l) in self.chart])]
        altered_uv_textures = []

        for src, channel, dest, location in self.chart:
            x, y, width, height = location
            x /= float(self.width)
            y /= float(self.height)
            width /= float(self.width)
            height /= float(self.height)

            # TODO: this next part is pretty fragile, might need a
            # more robust way to install atlas textures

            atlas_image = bpy.data.images[os.path.basename(dest)]
            for texture in src.textures:
                texture.image = atlas_image

            for uv_texture in src.uv_textures:
                if uv_texture not in altered_uv_textures:
                    for item in uv_texture.data:
                        if channel == 'color':
                            item.image = atlas_image
                        for co in item.uv:
                            co[0] = co[0] * width + x
                            co[1] = co[1] * height + y
                    altered_uv_textures.append(uv_texture)

class LibraryImage(atlas.Image):
    def __init__(self, *args, **kwargs):
        super(LibraryImage, self).__init__(*args, **kwargs)
        self.meshes = []
        self.textures = []
        self.uv_textures = []
