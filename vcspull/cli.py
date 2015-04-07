# -*- coding: utf-8 -*-
"""CLI utilities for vcspull.

vcspull.cli
~~~~~~~~~~~

"""

from __future__ import absolute_import, division, print_function, \
    with_statement, unicode_literals

import os
import sys
import fnmatch
import glob
import logging
import re
import argparse

import kaptan
import argcomplete

from .__about__ import __version__
from ._compat import string_types
from .util import expand_config, get_repos, update_dict, in_dir
from .config import find_configs
from .log import DebugLogFormatter
from .repo import Repo

log = logging.getLogger(__name__)


config_dir = os.path.expanduser('~/.vcspull/')
cwd_dir = os.getcwd() + '/'


def setup_logger(log=None, level='INFO'):
    """Setup logging for CLI use.

    :param log: instance of logger
    :type log: :py:class:`Logger`

    """
    if not log:
        log = logging.getLogger()
    if not log.handlers:
        channel = logging.StreamHandler()
        channel.setFormatter(DebugLogFormatter())

        log.setLevel(level)
        log.addHandler(channel)


def get_parser():
    """Return :py:class:`argparse.ArgumentParser` instance for CLI."""

    main_parser = argparse.ArgumentParser()

    main_parser.add_argument(
        '-c', '--config',
        dest='config',
        type=str,
        nargs='?',
        help='Pull the latest repositories from config(s)'
    ).completer = ConfigFileCompleter(
        allowednames=('.yaml', '.json'), directories=False
    )

    main_parser.add_argument(
        '-d', '--dirmatch',
        dest='dirmatch',
        type=str,
        nargs='?',
        help='Pull only from the directories. Accepts fnmatch(1)'
             'by commands'
    )

    main_parser.add_argument(
        '-r', '--repomatch',
        dest='repomatch',
        type=str,
        nargs='?',
        help='Pull only from the repository urls. Accepts fnmatch(1)'
    )

    main_parser.add_argument(
        dest='namematch',
        type=str,
        nargs='?',
        help='Pull only from project name. Accepts fnmatch(1)'
    )

    main_parser.set_defaults(callback=command_load)

    main_parser.add_argument(
        '-v', '--version', action='version',
        version='vcspull %s' % __version__,
        help='Prints the vcspull version',
    )

    return main_parser


def main():
    """Main CLI application."""

    parser = get_parser()

    argcomplete.autocomplete(parser, always_complete_options=False)

    args = parser.parse_args()

    setup_logger(
        level=args.log_level.upper() if 'log_level' in args else 'INFO'
    )

    try:
        if not args.config or args.config and args.callback is command_load:
            command_load(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        pass


def command_load(args):
    if not args.config or args.config == ['*']:
        yaml_config = os.path.expanduser('~/.vcspull.yaml')
        has_yaml_config = os.path.exists(yaml_config)
        json_config = os.path.expanduser('~/.vcspull.json')
        has_json_config = os.path.exists(json_config)
        if not has_yaml_config and not has_json_config:
            log.fatal(
                'No config file found. Create a .vcspull.yaml or .vcspull.json'
                ' in your $HOME directory. http://vcspull.rtfd.org for a'
                ' quickstart.'
            )
        else:
            if sum(filter(None, [has_json_config, has_yaml_config])) > int(1):
                sys.exit(
                    'multiple configs found in home directory use only one.'
                    ' .yaml, .json.'
                )
            elif has_yaml_config:
                config_file = yaml_config
            elif has_json_config:
                config_file = json_config

            config = kaptan.Kaptan()
            config.import_config(config_file)

            logging.debug('%r' % config.get())
            logging.debug('%r' % expand_config(config.get()))
            logging.debug('%r' % get_repos(expand_config(config.get())))

            repos = get_repos(
                expand_config(config.get()),
                dirmatch=args.dirmatch,
                repomatch=args.repomatch,
                namematch=args.namematch
            )
            for repo_dict in repos:
                r = Repo(repo_dict)
                log.debug('%s' % r)
                r.update_repo()


class ConfigFileCompleter(argcomplete.completers.FilesCompleter):

    """argcomplete completer for vcspull files."""

    def __call__(self, prefix, **kwargs):

        completion = argcomplete.completers.FilesCompleter.__call__(
            self, prefix, **kwargs
        )

        completion += [os.path.join(config_dir, c)
                       for c in in_dir(config_dir)]

        return completion
