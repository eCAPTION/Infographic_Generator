from data.rico import Rico
from data.publaynet import PubLayNet
from data.magazine import Magazine
from data.infographic import Infographic


def get_dataset(name, split, transform=None):
    if name == 'rico':
        return Rico(split, transform)

    elif name == 'publaynet':
        return PubLayNet(split, transform)

    elif name == 'magazine':
        return Magazine(split, transform)

    elif name == 'infographic':
        return Infographic(split, transform)

    raise NotImplementedError(name)
