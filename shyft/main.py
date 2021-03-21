#!/usr/bin/env python3

import sys

from shyft.parse_args import get_parser

parser = get_parser()
ns = parser.parse_args(sys.argv[1:])

ns.func(ns)
