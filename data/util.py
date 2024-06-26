import torch
import random
from enum import IntEnum
from itertools import product, combinations

from util import convert_xywh_to_ltrb


class RelSize(IntEnum):
    UNKNOWN = 0
    SMALLER = 1
    EQUAL = 2
    LARGER = 3


class RelLoc(IntEnum):
    UNKNOWN = 4
    LEFT = 5
    TOP = 6
    RIGHT = 7
    BOTTOM = 8
    CENTER = 9


REL_SIZE_ALPHA = 0.1


def detect_size_relation(b1, b2):
    a1, a2 = b1[2] * b1[3], b2[2] * b2[3]
    a1_sm = (1 - REL_SIZE_ALPHA) * a1
    a1_lg = (1 + REL_SIZE_ALPHA) * a1

    if a2 <= a1_sm:
        return RelSize.SMALLER

    if a1_sm < a2 and a2 < a1_lg:
        return RelSize.EQUAL

    if a1_lg <= a2:
        return RelSize.LARGER

    raise RuntimeError(b1, b2)


def detect_loc_relation(b1, b2, canvas=False):
    if canvas:
        yc = b2[1]
        y_sm, y_lg = 1. / 3, 2. / 3

        if yc <= y_sm:
            return RelLoc.TOP

        if y_sm < yc and yc < y_lg:
            return RelLoc.CENTER

        if y_lg <= yc:
            return RelLoc.BOTTOM

    else:
        l1, t1, r1, b1 = convert_xywh_to_ltrb(b1)
        l2, t2, r2, b2 = convert_xywh_to_ltrb(b2)

        if b2 <= t1:
            return RelLoc.TOP

        if b1 <= t2:
            return RelLoc.BOTTOM

        if t1 < b2 and t2 < b1:
            if r2 <= l1:
                return RelLoc.LEFT

            if r1 <= l2:
                return RelLoc.RIGHT

            if l1 < r2 and l2 < r1:
                return RelLoc.CENTER

    raise RuntimeError(b1, b2, canvas)


def get_rel_text(rel, canvas=False):
    if type(rel) == RelSize:
        index = rel - RelSize.UNKNOWN - 1
        if canvas:
            return [
                'within canvas',
                'spread over canvas',
                'out of canvas',
            ][index]

        else:
            return [
                'larger than',
                'equal to',
                'smaller than',
            ][index]

    else:
        index = rel - RelLoc.UNKNOWN - 1
        if canvas:
            return [
                '', 'at top',
                '', 'at bottom',
                'at middle',
            ][index]

        else:
            return [
                'right to', 'below',
                'left to', 'above',
                'around',
            ][index]


class LexicographicSort():
    def __call__(self, data):
        assert not data.attr['has_canvas_element']
        l, t, _, _ = convert_xywh_to_ltrb(data.x.t())
        _zip = zip(*sorted(enumerate(zip(t, l)), key=lambda c: c[1:]))
        idx = list(list(_zip)[0])
        data.x_orig, data.y_orig = data.x, data.y
        data.x, data.y = data.x[idx], data.y[idx]
        return data


class HorizontalFlip():
    def __call__(self, data):
        data.x = data.x.clone()
        data.x[:, 0] = 1 - data.x[:, 0]
        return data


class AddCanvasElement():
    def __init__(self):
        self.x = torch.tensor([[.5, .5, 1., 1.]], dtype=torch.float)
        self.y = torch.tensor([0], dtype=torch.long)

    def __call__(self, data):
        if not data.attr['has_canvas_element']:
            data.x = torch.cat([self.x, data.x], dim=0)
            data.y = torch.cat([self.y, data.y + 1], dim=0)
            data.attr = data.attr.copy()
            data.attr['has_canvas_element'] = True
        return data

# randomly add relational constraints
class AddRelation():
    def __init__(self, seed=None, ratio=0.1):
        self.ratio = ratio
        self.generator = random.Random()
        if seed is not None:
            self.generator.seed(seed)

    def __call__(self, data):
        # N = number of boxes in layout
        N = data.x.size(0)
        # print(data.x.size())
        # print('=' * 20)
        # print(N)
        has_canvas = data.attr['has_canvas_element']

        rel_all = list(product(range(2), combinations(range(N), 2))) # get all possible pairs of boxes
        size = int(len(rel_all) * self.ratio) # randomly choose self.ratio of boxes with relations
        rel_sample = set(self.generator.sample(rel_all, size))
        # the pairs of element indices with relational constraints
        # SAMPLE:  {(0, (0, 3)), (1, (4, 5)), (0, (2, 4)), (0, (0, 4))} 
        # take (0, (0, 3)) -> (0, 3) are the element indices, 0 means size relation, 1 means location relation
        edge_index, edge_attr = [], []
        rel_unk = 1 << RelSize.UNKNOWN | 1 << RelLoc.UNKNOWN
        
        for i, j in combinations(range(N), 2):
            bi, bj = data.x[i], data.x[j]
            canvas = data.y[i] == 0 and has_canvas

            if (0, (i, j)) in rel_sample:
                rel_size = 1 << detect_size_relation(bi, bj)
            else:
                rel_size = 1 << RelSize.UNKNOWN

            if (1, (i, j)) in rel_sample:
                rel_loc = 1 << detect_loc_relation(bi, bj, canvas)
            else:
                rel_loc = 1 << RelLoc.UNKNOWN

            rel = rel_size | rel_loc # addition of rel_size and rel_loc

            if rel != rel_unk:
                edge_index.append((i, j))
                edge_attr.append(rel)

        data.edge_index = torch.as_tensor(edge_index).long()
        data.edge_index = data.edge_index.t().contiguous()
        data.edge_attr = torch.as_tensor(edge_attr).long()
        return data

class AddCustomRelation():
    '''
    box id_b has relation over box id_a (e.g. box id_b is smaller than box id_a)
    '''
    def __init__(self, id_a, id_b, relation): 
        self.str_to_loc_relations = {'unknown': RelLoc.UNKNOWN, 'left': RelLoc.LEFT, 'top': RelLoc.TOP, 'right': RelLoc.RIGHT, 'bottom': RelLoc.BOTTOM, 'center': RelLoc.CENTER}
        self.str_to_size_relations = {'unknown': RelSize.UNKNOWN, 'small': RelSize.SMALLER, 'equal': RelSize.EQUAL, 'larger': RelSize.LARGER}
        self.id_a = id_a
        self.id_b = id_b
        self.relation = relation

    def __call__(self, data):
        print(data.x)
        rel_loc = 1 << self.str_to_loc_relations.get(self.relation, RelLoc.UNKNOWN)
        rel_size = 1 << self.str_to_size_relations.get(self.relation, RelLoc.UNKNOWN)
        edge_index, edge_attr = [], []
        rel_unk = 1 << RelSize.UNKNOWN | 1 << RelLoc.UNKNOWN
        rel = rel_size | rel_loc
        if rel != rel_unk:
            edge_index.append((self.id_a, self.id_b))
            edge_attr.append(rel)
        data.edge_index = torch.as_tensor(edge_index).long()
        data.edge_index = data.edge_index.t().contiguous()
        data.edge_attr = torch.as_tensor(edge_attr).long()
        return data