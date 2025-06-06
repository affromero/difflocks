##from https://github.com/Tony-Y/pytorch_warmup/blob/master/pytorch_warmup/base.py

import math
from contextlib import contextmanager
from torch.optim import Optimizer


def _check_optimizer(optimizer):
    if not isinstance(optimizer, Optimizer):
        raise TypeError('{} ({}) is not an Optimizer.'.format(
            optimizer, type(optimizer).__name__))


class BaseWarmup(object):
    """Base class for all warmup schedules

    Arguments:
        optimizer (Optimizer): an instance of a subclass of Optimizer
        warmup_params (list): warmup paramters
        last_step (int): The index of last step. (Default: -1)
    """

    def __init__(self, optimizer, warmup_params, last_step=-1):
        self.optimizer = optimizer
        self.warmup_params = warmup_params
        self.last_step = last_step
        self.lrs = [group['lr'] for group in self.optimizer.param_groups]
        self.dampen()

    def state_dict(self):
        """Returns the state of the warmup scheduler as a :class:`dict`.

        It contains an entry for every variable in self.__dict__ which
        is not the optimizer.
        """
        return {key: value for key, value in self.__dict__.items() if key != 'optimizer'}

    def load_state_dict(self, state_dict):
        """Loads the warmup scheduler's state.

        Arguments:
            state_dict (dict): warmup scheduler state. Should be an object returned
                from a call to :meth:`state_dict`.
        """
        self.__dict__.update(state_dict)

    def dampen(self, step=None):
        """Dampen the learning rates.

        Arguments:
            step (int): The index of current step. (Default: None)
        """
        if step is None:
            step = self.last_step + 1
        self.last_step = step

        for group, params in zip(self.optimizer.param_groups, self.warmup_params):
            omega = self.warmup_factor(step, **params)
            group['lr'] *= omega

    @contextmanager
    def dampening(self):
        for group, lr in zip(self.optimizer.param_groups, self.lrs):
            group['lr'] = lr
        yield
        self.lrs = [group['lr'] for group in self.optimizer.param_groups]
        self.dampen()

    def warmup_factor(self, step, **params):
        raise NotImplementedError


def get_warmup_params(warmup_period, group_count):
    if isinstance(warmup_period, list):
        if len(warmup_period) != group_count:
            raise ValueError(
                'The size of warmup_period ({}) does not match the size of param_groups ({}).'.format(
                    len(warmup_period), group_count))
        for x in warmup_period:
            if not isinstance(x, int):
                raise TypeError(
                    'An element in warmup_period, {}, is not an int.'.format(
                        type(x).__name__))
            if x <= 0:
                raise ValueError(
                    'An element in warmup_period must be a positive integer, but is {}.'.format(x))
        warmup_params = [dict(warmup_period=x) for x in warmup_period]
    elif isinstance(warmup_period, int):
        if warmup_period <= 0:
            raise ValueError(
                'warmup_period must be a positive integer, but is {}.'.format(warmup_period))
        warmup_params = [dict(warmup_period=warmup_period)
                         for _ in range(group_count)]
    else:
        raise TypeError('{} ({}) is not a list nor an int.'.format(
            warmup_period, type(warmup_period).__name__))
    return warmup_params


class LinearWarmup(BaseWarmup):
    """Linear warmup schedule.

    Arguments:
        optimizer (Optimizer): an instance of a subclass of Optimizer
        warmup_period (int or list): Warmup period
        last_step (int): The index of last step. (Default: -1)
    """

    def __init__(self, optimizer, warmup_period, last_step=-1):
        _check_optimizer(optimizer)
        group_count = len(optimizer.param_groups)
        warmup_params = get_warmup_params(warmup_period, group_count)
        super(LinearWarmup, self).__init__(optimizer, warmup_params, last_step)

    def warmup_factor(self, step, warmup_period):
        return min(1.0, (step+1) / warmup_period)


class ExponentialWarmup(BaseWarmup):
    """Exponential warmup schedule.

    Arguments:
        optimizer (Optimizer): an instance of a subclass of Optimizer
        warmup_period (int or list): Effective warmup period
        last_step (int): The index of last step. (Default: -1)
    """

    def __init__(self, optimizer, warmup_period, last_step=-1):
        _check_optimizer(optimizer)
        group_count = len(optimizer.param_groups)
        warmup_params = get_warmup_params(warmup_period, group_count)
        super(ExponentialWarmup, self).__init__(optimizer, warmup_params, last_step)

    def warmup_factor(self, step, warmup_period):
        return 1.0 - math.exp(-(step+1) / warmup_period)