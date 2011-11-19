EPSILON = 0.000001

def approx_eq(a, b):
    return abs(a - b) < EPSILON

def get_item_or_attr(obj, attr):
    try:
        return obj[attr]
    except (TypeError, KeyError):
        return getattr(obj, attr)

def sort_by_largest(objects):
    objects = list(objects)
    objects.sort(
        key=lambda i: -(
            get_item_or_attr(i, 'width') *
            get_item_or_attr(i, 'height')))
    return objects

def pack(objects, width, height, margin=0.):
    root = PackNode(
        0., 0., float(width), float(height),
        margin=float(margin))
    for obj in sort_by_largest(objects):
        node = root.insert(obj)
        if node is None:
            raise PackOverflow(obj)
    return root.flatten()

class PackOverflow(Exception): pass

class PackNode(object):
    def __init__(
        self, x, y, width, height,
        obj=None, a=None, b=None, margin=0.):

        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.a = a
        self.b = b
        self.obj = obj
        self.margin = margin

    def insert(self, obj):
        width = self.width - self.margin
        height = self.height - self.margin

        if self.a and self.b:
            # not leaf
            return self.a.insert(obj) or self.b.insert(obj)
        else:
            # leaf
            if self.obj is not None:
                # leaf, filled
                return None
            else:
                # leaf, unfilled
                obj_width = get_item_or_attr(obj, 'width')
                obj_height = get_item_or_attr(obj, 'height')
                if obj_width > width or obj_height > height:
                    # doesn't fit
                    return None
                if approx_eq(obj_width, width) and \
                   approx_eq(obj_height, height):
                    # same size
                    self.obj = obj
                    return self
                else:
                    # split
                    delta_width = width - obj_width
                    delta_height = height - obj_height
                    if (delta_width > delta_height):
                        a_x = self.x
                        a_y = self.y
                        a_width = obj_width + self.margin
                        a_height = self.height
                        b_x = self.x + a_width
                        b_y = self.y
                        b_width = delta_width;
                        b_height = self.height
                    else:
                        a_x = self.x
                        a_y = self.y
                        a_height = obj_height + self.margin
                        a_width = self.width;
                        b_x = self.x
                        b_y = self.y + a_height;
                        b_height = delta_height;
                        b_width = self.width;
                    self.a = self.__class__(
                        a_x, a_y, a_width, a_height, margin=self.margin)
                    self.b = self.__class__(
                        b_x, b_y, b_width, b_height, margin=self.margin)
                    return self.a.insert(obj)

    def flatten(self):
        if self.obj is not None:
            return [(self.obj, (
                    self.x, self.y,
                    self.width - self.margin, self.height - self.margin))]
        if self.a and self.b:
            return self.a.flatten() + self.b.flatten()
        else:
            return []
