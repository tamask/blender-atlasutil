from atlasutil.renderer import render
from atlasutil.packer import pack, PackOverflow

class Image(object):
    def __init__(self, width, height, channels):
        self.width = width
        self.height = height
        self.channels = channels

class Atlas(object):
    def __init__(self, width, height, images, margin=0.):
        self.width = width
        self.height = height
        self.images = images
        self.margin = margin

    def pack(self):
        return pack(self.images, self.width, self.height, self.margin)

    def render(self, filename):
        chart = []
        image_locations = self.pack()
        channels = set()
        for image in self.images:
            channels.update(image.channels.keys())
        for channel in channels:
            output = filename % {'channel': channel}
            channel_locations = [
                (image.channels[channel], location)
                for (image, location) in image_locations
                if channel in image.channels]
            chart.extend(
                (image, channel, output, loc)
                for (image, loc) in image_locations
                if channel in image.channels)
            render(output, self.width, self.height, channel_locations)
        return chart
