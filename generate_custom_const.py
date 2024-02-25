import os
os.environ['OMP_NUM_THREADS'] = '1'  # noqa

import pickle
import argparse
import tempfile
import subprocess
from tqdm import tqdm
from pathlib import Path
import seaborn as sns

import torch
import torchvision.transforms as T

from torch_geometric.data import DataLoader, InMemoryDataset, Data
from torch_geometric.utils import to_dense_batch

from data import get_dataset
from util import set_seed, convert_layout_to_image
from data.util import AddCanvasElement, AddRelation
from model.layoutganpp import Generator, Discriminator

import clg.const
from clg.auglag import AugLagMethod
from clg.optim import AdamOptimizer, CMAESOptimizer
from metric import compute_violation, get_relations

def save_gif(out_path, j, netG,
             z_hist, label, mask, padding_mask,
             dataset_colors, canvas_size):
    mask = mask[j]
    _j = slice(j, j + 1)

    z_before, z_filtered = None, []
    for z in z_hist:
        if z_before is not None:
            if z_before.eq(z[_j]).all():
                continue
        z_filtered.append(z)
        z_before = z[_j]
    z_filtered += [z] * 2

    with tempfile.TemporaryDirectory() as tempdir:
        for i, z in enumerate(z_filtered):
            bbox = netG(z[_j], label[_j], padding_mask[_j])
            b = bbox[0][mask].cpu().numpy()
            l = label[0][mask].cpu().numpy()

            convert_layout_to_image(
                b, l, dataset_colors, canvas_size
            ).save(tempdir + f'/{j}_{i:08d}.png')

        subprocess.run(['convert', '-delay', '50',
                        tempdir + f'/{j}_*.png', str(out_path)])

def get_colors(num_classes):
    n_colors = num_classes
    colors = sns.color_palette('husl', n_colors=n_colors)
    return [tuple(map(lambda x: int(x * 255), c)) for c in colors]

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('ckpt_path', type=str, help='checkpoint path')
    parser.add_argument('--label', type=int, nargs='+',
                        help='label')
    parser.add_argument('-o', '--out_path', type=str,
                        default='output/generated_layouts.pkl',
                        help='output pickle path')
    parser.add_argument('--seed', type=int, help='manual seed')

    # CLG specific options
    parser.add_argument('--const_type', type=str,
                        default='beautify', help='constraint type',
                        choices=['beautify', 'relation'])
    parser.add_argument('--optimizer', type=str,
                        default='CMAES', help='inner optimizer',
                        choices=['Adam', 'CMAES'])
    parser.add_argument('--rel_ratio', type=float, default=0.1,
                        help='ratio of relational constraints')

    args = parser.parse_args()

    if args.seed is not None:
        set_seed(args.seed)

    out_path = Path(args.out_path)
    out_dir = out_path.parent
    out_dir.mkdir(exist_ok=True, parents=True)

    # load checkpoint
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.ckpt_path, map_location=device)
    train_args = ckpt['args']

    # setup transforms and constraints
    transforms = [AddCanvasElement()]
    if args.const_type == 'relation':
        transforms += [AddRelation(args.seed, args.rel_ratio)]
        constraints = clg.const.relation
    else:
        constraints = clg.const.beautify

    
    label = list(args.label)
    label = torch.tensor(label)

    num_label = 5
    mask = torch.full(label.size(), True).to(device)
    mask = mask[None, :] #expand dims
    padding_mask = ~mask

    y = label
    x = torch.full((y.size(0), 4), 0.0) # placeholder boxes with coords 0
    
    attr = {'has_canvas_element': False, 'filtered': False}
    
    data = Data(x=x, y=y, attr=attr)

    for t in transforms:
        t(data)
    data.batch = torch.full(data.y.size(), 0)
    data.attr = [data.attr.copy()]

    data.y = data.y.to(device)
    data.x = data.x.to(device)
    data.batch = data.batch.to(device)

    # setup model and load state
    netG = Generator(train_args['latent_size'], num_label,
                     d_model=train_args['G_d_model'],
                     nhead=train_args['G_nhead'],
                     num_layers=train_args['G_num_layers'],
                     ).eval().requires_grad_(False).to(device)
    netG.load_state_dict(ckpt['netG'])

    netD = Discriminator(num_label,
                         d_model=train_args['D_d_model'],
                         nhead=train_args['D_nhead'],
                         num_layers=train_args['D_num_layers'],
                         ).eval().requires_grad_(False).to(device)
    netD.load_state_dict(ckpt['netD'])

    # setup optimizers
    if args.optimizer == 'CMAES':
        inner_optimizer = CMAESOptimizer(seed=args.seed)
    else:
        inner_optimizer = AdamOptimizer()
    optimizer = AugLagMethod(netG, netD, inner_optimizer, constraints)

    results, violation = [], []
    label = label[None, :].to(device) # expand label dims

    z = torch.randn(label.size(0), label.size(1),
                    train_args['latent_size'],
                    device=device)

    z_hist = [z]
    for z in optimizer.generator(z, data):
        if len(results) < 1:
            z_hist.append(z)

    bbox = netG(z, label, padding_mask)

    if args.const_type == 'relation':
        canvas = optimizer.bbox_canvas.to(bbox)
        canvas = canvas.expand(bbox.size(0), -1, -1)
        bbox_flatten = torch.cat([canvas, bbox], dim=1)[mask_c]
        v = compute_violation(bbox_flatten, data)
        relations = get_relations(bbox_flatten, data)
        print('\nRELATIONS: ', relations)
        violation += v[~v.isnan()].tolist()

    bbox_init = netG(z_hist[0], label, padding_mask)
    print(bbox.size())
    colors = get_colors(num_label)
    for j in range(bbox.size(0)):
        mask_j = mask[j]
        b = bbox[j][mask_j].cpu().numpy()
        l = label[j][mask_j].cpu().numpy()

        out_path = out_dir / f'initial_{len(results)}.png'
        convert_layout_to_image(
            bbox_init[j][mask_j].cpu().numpy(),
            l, colors, (120, 80)
        ).save(out_path)

        out_path = out_dir / f'optimized_{len(results)}.png'
        convert_layout_to_image(
            b, l, colors, (120, 80)
        ).save(out_path)

        out_path = out_dir / f'optimizing_{len(results)}.gif'
        save_gif(out_path, j, netG,
                    z_hist, label, mask, padding_mask,
                    colors, (120, 80))

        results.append((b, l))

    if args.const_type == 'relation':
        violation = sum(violation) / len(violation)
        print(f'Relation violation: {violation:.2%}')

    # save results
    with Path(args.out_path).open('wb') as fb:
        pickle.dump(results, fb)
    print('Generated layouts are saved at:', args.out_path)


if __name__ == '__main__':
    main()            