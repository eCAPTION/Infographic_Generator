import json
from pathlib import Path

import torch
from torch_geometric.data import Data

from data.base import BaseDataset

class Infographic(BaseDataset):
    labels = ['text', 'image', 'chart']

    def __init__(self, split='train', transform=None):
        super().__init__('infographic', split, transform)

    def download(self):
        super().download()

    def process(self):

        data_list = []
        raw_dir = Path(self.raw_dir) / 'semantic_annotations'
        for json_path in sorted(raw_dir.glob('*.json')):
            with json_path.open() as f:
                ann = json.load(f)

            W, H = ann['image_size']['width'], ann['image_size']['height'] 
            boxes = []
            labels = []
            
            elements = ann['annotations']

            for element in elements:
                # bbox
                top = element['top']
                left = element['left']
                width = element['width']
                height = element['height']

                xc = left + width / 2
                yc = top + height / 2

                b = [xc / W, yc / H,
                     width / W, height / H]
                boxes.append(b)

                # label
                l = element['class_id']
                labels.append(l)

            boxes = torch.tensor(boxes, dtype=torch.float)
            labels = torch.tensor(labels, dtype=torch.long)
            print('BOX SIZES: ', boxes.size())
            data = Data(x=boxes, y=labels)
            data.attr = {
                'name': json_path.name,
                'width': W,
                'height': H,
                'filtered': False,
                'has_canvas_element': False,
            }
            data_list.append(data)

        # shuffle with seed
        generator = torch.Generator().manual_seed(0)
        indices = torch.randperm(len(data_list), generator=generator)
        data_list = [data_list[i] for i in indices]
        # train 85% / val 5% / test 10%
        N = len(data_list)
        s = [int(N * .85), int(N * .90)]
        torch.save(self.collate(data_list[:s[0]]), self.processed_paths[0])
        torch.save(self.collate(data_list[s[0]:s[1]]), self.processed_paths[1])
        torch.save(self.collate(data_list[s[1]:]), self.processed_paths[2])
