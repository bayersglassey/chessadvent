#!/usr/bin/env python3

from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser()
    return parser.parse_args()


def main(curses=False):
    args = parse_args()


if __name__ == '__main__':

    main()

    # TODO: implement a curses mode, see:
    # * https://docs.python.org/3/howto/curses.html
    #curses.wrapper(main, curses=True)
