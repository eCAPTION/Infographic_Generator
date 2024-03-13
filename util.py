import json
import random
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw

import torch
import torchvision.utils as vutils
import torchvision.transforms as T


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    print("Random Seed:", seed)


def init_experiment(args, prefix):
    if args.seed is None:
        args.seed = random.randint(0, 10000)

    set_seed(args.seed)

    if not args.name:
        args.name = datetime.now().strftime('%Y%m%d%H%M%S%f')

    out_dir = Path('output') / args.dataset / prefix / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / 'args.json'
    with json_path.open('w') as f:
        json.dump(vars(args), f, indent=2)

    return out_dir


def save_checkpoint(state, is_best, out_dir):
    out_path = Path(out_dir) / 'checkpoint.pth.tar'
    torch.save(state, out_path)

    if is_best:
        best_path = Path(out_dir) / 'model_best.pth.tar'
        shutil.copyfile(out_path, best_path)


def convert_xywh_to_ltrb(bbox):
    xc, yc, w, h = bbox
    x1 = xc - w / 2
    y1 = yc - h / 2
    x2 = xc + w / 2
    y2 = yc + h / 2
    return [x1, y1, x2, y2]


def convert_layout_to_image(boxes, labels, colors, canvas_size):
    H, W = canvas_size
    img = Image.new('RGB', (int(W), int(H)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img, 'RGBA')

    # draw from larger boxes
    area = [b[2] * b[3] for b in boxes]
    indices = sorted(range(len(area)),
                     key=lambda i: area[i],
                     reverse=True)

    for i in indices:
        bbox, color = boxes[i], colors[labels[i]]
        c_fill = color + (100,)
        x1, y1, x2, y2 = convert_xywh_to_ltrb(bbox)
        x1, x2 = x1 * (W - 1), x2 * (W - 1)
        y1, y2 = y1 * (H - 1), y2 * (H - 1)
        draw.rectangle([x1, y1, x2, y2],
                       outline=color,
                       fill=c_fill)
        draw.text(((x1+x2)/2, (y1+y2)/2), str(i + 1), fill=(0,0,0), anchor='mm')
    return img


def save_image(batch_boxes, batch_labels, batch_mask,
               dataset_colors, out_path, canvas_size=(60, 40),
               nrow=None):
    # batch_boxes: [B, N, 4]
    # batch_labels: [B, N]
    # batch_mask: [B, N]

    imgs = []
    B = batch_boxes.size(0)
    to_tensor = T.ToTensor()
    for i in range(B):
        mask_i = batch_mask[i]
        boxes = batch_boxes[i][mask_i]
        labels = batch_labels[i][mask_i]
        img = convert_layout_to_image(boxes, labels,
                                      dataset_colors,
                                      canvas_size)
        imgs.append(to_tensor(img))
    image = torch.stack(imgs)

    if nrow is None:
        nrow = int(np.ceil(np.sqrt(B)))

    vutils.save_image(image, out_path, normalize=False, nrow=nrow)

def convert_layout_to_infographic(input_dict, boxes, labels, canvas_size): 
    '''
    the input is a dict[label_index: [values of each label element]]
    e.g. {0: ['Biden', 'Trump']}
    images are represented by Pillow Image object.
    '''
    H, W = canvas_size
    img = Image.new('RGB', (int(W), int(H)), color=(255,255,255))
    draw = ImageDraw.Draw(img, 'RGBA')

    area = [b[2] * b[3] for b in boxes]
    indices = sorted(range(len(area)), key=lambda i:area[i], reverse=True)

    for i in indices:
        bbox, label = boxes[i], labels[i]
        x1, y1, x2, y2 = convert_xywh_to_ltrb(bbox)
        x1, y1, x2, y2 = int(x1*W), int(y1*H), int(x2*W), int(y2*H)

        if label == 1 or label == 2:
            img_to_paste = input_dict[label][0].resize((x2-x1, y2-y1))
            img.paste(img_to_paste, (x1, y1, x2, y2))
            input_dict[label].pop(0)
        else:
            # text
            text = input_dict[label][0]
            font_size = 100
            words = text.split()
            
            while font_size > 0:
                size = None
                curr_words = []
                idx = 0 # index of current word to select
                while idx < len(words):
                    l, t, r, b = draw.multiline_textbbox((x1, y1), ' '.join(curr_words), font_size=font_size)
                    size = (r-l, b-t) # (width, height)
                    if size[1] > y2-y1:
                        break
                    if size[0] < x2-x1:
                        curr_words.append(words[idx])
                        idx += 1
                    else:
                        if curr_words[-1] == '\n':
                            break
                        curr_words.pop()
                        idx -= 1
                        curr_words.append('\n') # add new line  

                if idx >= len(words):
                    break
                font_size -= 1
            draw.multiline_text((x1, y1), ' '.join(curr_words), fill="#000", font_size=font_size)
    return img