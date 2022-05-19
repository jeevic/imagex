#!/usr/bin/env python 
# -*- coding: utf-8 -*-
from .configs import get_configs


settings = get_configs()


__all__ = [
    "settings",
]