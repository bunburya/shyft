#!/usr/bin/env python3

from shyft.parse_args import get_parser

if __name__ == '__main__':
    parser = get_parser()
    ns = parser.parse_args()

    ns.func(ns)
