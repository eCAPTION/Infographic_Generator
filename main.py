from generate_custom_const import generate_bbox_beautify, generate_bbox_relation
from util import set_seed, convert_layout_to_image
import seaborn as sns

def get_colors(num_classes):
    n_colors = num_classes
    colors = sns.color_palette('husl', n_colors=n_colors)
    return [tuple(map(lambda x: int(x * 255), c)) for c in colors]

(bbox, label) = generate_bbox_beautify('pretrained/layoutganpp_magazine.pth.tar', [0,0,1,1,2], 5)
out_path = 'output/beautify/optimized_0.png'
convert_layout_to_image(bbox, label, get_colors(5), (120, 80)).save(out_path)
(bbox2, label2) = generate_bbox_relation('pretrained/layoutganpp_magazine.pth.tar', 4, 3, 'top', bbox, label, 5)
out_path_2 = 'output/beautify/optimized_0_rel.png'
convert_layout_to_image(bbox2, label2, get_colors(5), (120, 80)).save(out_path_2)