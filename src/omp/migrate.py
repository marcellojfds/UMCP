"""Installed-package migration entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config


def _script_location() -> Path:
    packaged = Path(__file__).with_name("migrations")
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "migrations"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(_script_location()))
    return config


def main() -> None:
    parser = argparse.ArgumentParser(prog="omp-migrate")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("upgrade", "downgrade"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("revision", default="head", nargs="?")
    subparsers.add_parser("current")
    subparsers.add_parser("heads")
    args = parser.parse_args()
    config = _config()
    if args.command == "upgrade":
        command.upgrade(config, args.revision)
    elif args.command == "downgrade":
        command.downgrade(config, args.revision)
    elif args.command == "current":
        command.current(config)
    else:
        command.heads(config)  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    main()
