import logging
from argparse import ArgumentParser, Namespace
from collections import OrderedDict
from typing import Tuple

from shyft.config import Config
from shyft.app.app import get_apps
from shyft.logger import get_logger


def handle_universal_options(ns: Namespace) -> Tuple[Config, logging.Logger]:
    """Handle "universal" options (options that apply across all
    commands), such as debug mode or specifying the config file to use.
    """
    config = Config(ns.config)
    if ns.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    logger = get_logger(file_level=log_level, console_level=log_level, config=config)
    logger.info(f'Loaded configuration from {ns.config}.')
    return config, logger


def run_app(ns: Namespace):
    """Run the Dash app."""
    config, logger = handle_universal_options(ns)
    logger.debug('Running "run" command.')
    _, dash_app = get_apps(config)
    logger.info(f'Starting dash app on {ns.host}:{ns.port}.{" Debug mode active." if ns.debug else ""}')
    dash_app.run_server(ns.host, ns.port, debug=ns.debug, use_reloader=False)


def mk_config(ns: Namespace):
    """Create a new configuration by taking the given (or default)
    configuration, making the specified changes and saving the .ini file
    to the given location.
    """
    config, logger = handle_universal_options(ns)
    logger.debug('Running "mkconfig" command.')
    ns_dict = vars(ns)
    out_file = ns_dict.pop('outfile')
    for field in Config.__dataclass_fields__:
        if (k := ns_dict.get(field)) is not None:
            logger.debug(f'Setting config value "{field}" to "{k}".')
            setattr(config, field, k)
    config.to_file(fpath=out_file)


COMMANDS = OrderedDict([
    ('run', run_app),
    ('mkconfig', mk_config)
])


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Self-hosted fitness tracker app.')
    subparsers = parser.add_subparsers()

    parser.add_argument('-c', '--config', metavar='FILE', help='Specify the configuration file to be used.')
    parser.add_argument('--debug', action='store_true', help='Debug mode (more verbose output).')

    run_subparser = subparsers.add_parser('run', description='Run app.')
    run_subparser.add_argument('--host', metavar='ADDRESS', help='Address to listen on.', default='127.0.0.1')
    run_subparser.add_argument('--port', metavar='PORT', help='Port to listen on.', type=int, default=8080)
    run_subparser.set_defaults(func=run_app)

    mkconf_subparser = subparsers.add_parser('mkconfig', help='Create a new configuration file, by taking the default '
                                                              '(or provided) config file, making the specified changes '
                                                              'and saving to the given location.')
    for field in Config.__dataclass_fields__:
        mkconf_subparser.add_argument(f'--{field}')
    mkconf_subparser.add_argument('outfile', metavar='FILE', nargs='?',
                                  help='The file to save the new configuration to.')
    mkconf_subparser.set_defaults(func=mk_config)

    return parser
