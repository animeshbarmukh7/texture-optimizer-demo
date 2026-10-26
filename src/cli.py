import argparse
from collections.abc import Callable
from pathlib import Path

from config import Config
from constants import DEFAULT_JSON_CONFIG_PATH
from logging_setup import logger, setup_logger
from models import TextureCollection


def check_path(input_dir_path: str) -> str:
    """Validate that the supplied path exists."""
    if not Path(input_dir_path).exists():
        raise argparse.ArgumentTypeError(f"Path does not exist: {input_dir_path}")

    return input_dir_path


def check_directory(input_dir_path: str) -> str:
    """Validate that the supplied path is an existing directory."""
    check_path(input_dir_path)

    if not Path(input_dir_path).is_dir():
        raise argparse.ArgumentTypeError(f"Expected a directory: {input_dir_path}")

    return input_dir_path


def check_config_file(input_dir_path: str) -> str:
    """Validate that the supplied path is an existing file."""
    check_path(input_dir_path)

    if not Path(input_dir_path).is_file():
        raise argparse.ArgumentTypeError(
            f"Expected a configuration file: {input_dir_path}"
        )

    return input_dir_path


def get_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    main_parser = argparse.ArgumentParser(
        prog="ag_nw_texture_optimizer",
        description="Reduces texture sizes for armors.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    main_parser.add_argument(
        "input_directory",
        type=check_directory,
        help="Path to a directory containing texture files.",
    )

    main_parser.add_argument(
        "--config-json",
        dest="config_json",
        default=DEFAULT_JSON_CONFIG_PATH,
        type=check_config_file,
        metavar="PATH",
        help="Path to a JSON configuration file.",
    )

    main_parser.add_argument(
        "-s",
        "--include-sub-dirs",
        dest="include_sub_directories",
        action="store_true",
        help="Search subdirectories for texture files.",
    )

    main_parser.add_argument(
        "-c",
        "--checkout-files",
        dest="checkout_files",
        action="store_true",
        help="Check out texture files in Perforce after processing.",
    )

    main_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        type=int,
        choices=range(1, 6),
        default=4,
        help=("Logging verbosity: 1=CRITICAL, 2=ERROR, 3=WARNING, 4=INFO, 5=DEBUG."),
    )

    return main_parser


def main(run: Callable[[Path, bool, bool], None]) -> None:
    """Parse arguments, initialize configuration, and run the workflow."""
    parser = get_parser()
    parsed_args = parser.parse_args()

    verbose_val = (6 - parsed_args.verbose) * 10
    setup_logger(verbose_val)

    logger.debug("Parsed arguments: %s", parsed_args)

    try:
        Config.load(parsed_args.config_json)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.error(
            f"Unable to load configuration '{parsed_args.config_json}': {error}"
        )

    TextureCollection.initialize_texture_mapping()

    run(
        Path(parsed_args.input_directory),
        parsed_args.include_sub_directories,
        parsed_args.checkout_files,
    )
