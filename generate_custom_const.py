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
from data.util import AddCanvasElement, AddRelation, AddCustomRelation
from model.layoutganpp import Generator, Discriminator

import clg.const
from clg.auglag import AugLagMethod
from clg.optim import AdamOptimizer, CMAESOptimizer
from metric import compute_violation, get_relations


def generate_bbox_beautify(ckpt_path, label, num_label):
    # load checkpoint
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location=device)
    train_args = ckpt['args']

    # set up transforms and constraints
    transforms = [AddCanvasElement()]
    constraints = clg.const.beautify

    label = torch.tensor(label)

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

    data = data.to(device)

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
    inner_optimizer = CMAESOptimizer()
    optimizer = AugLagMethod(netG, netD, inner_optimizer, constraints)

    label = label[None, :].to(device) # expand label dims

    results, violation = [], []

    z = torch.randn(label.size(0), label.size(1),
                    train_args['latent_size'],
                    device=device)
    z_hist = [z]
    for z in optimizer.generator(z, data):
        if len(results) < 1:
            z_hist.append(z)

    bbox = netG(z, label, padding_mask)
    mask_j = mask[0]
    b = bbox[0][mask_j].cpu().numpy()
    l = label[0][mask_j].cpu().numpy()
    return (b, l)

def generate_bbox_relation(ckpt_path, id_a, id_b, relation, bbox, label, num_label):
    # load checkpoint
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location=device)
    train_args = ckpt['args']

    # set up transforms and constraints
    transforms = [AddCanvasElement(), AddCustomRelation(id_a, id_b, relation)] 
    constraints = clg.const.relation

    label = torch.tensor(label)

    mask = torch.full(label.size(), True).to(device)
    mask = mask[None, :] #expand dims
    padding_mask = ~mask

    y = label
    x = torch.tensor(bbox)
    
    attr = {'has_canvas_element': False, 'filtered': False}
    
    data = Data(x=x, y=y, attr=attr)
    for t in transforms:
        t(data)

    data.batch = torch.full(data.y.size(), 0)
    data.attr = [data.attr.copy()]

    data = data.to(device)

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
    inner_optimizer = CMAESOptimizer()
    optimizer = AugLagMethod(netG, netD, inner_optimizer, constraints)

    label = label[None, :].to(device) # expand label dims

    results, violation = [], []

    z = torch.randn(label.size(0), label.size(1),
                    train_args['latent_size'],
                    device=device)
    z_hist = [z]
    for z in optimizer.generator(z, data):
        if len(results) < 1:
            z_hist.append(z)

    bbox = netG(z, label, padding_mask)
    mask_j = mask[0]
    b = bbox[0][mask_j].cpu().numpy()
    l = label[0][mask_j].cpu().numpy()
    return (b, l)