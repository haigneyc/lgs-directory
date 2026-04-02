"""Main CLI entry point for the LGS Directory."""

from __future__ import annotations

import click

from lgs_directory.cli.discover import discover
from lgs_directory.cli.presence import presence
from lgs_directory.cli.scrape import scrape
from lgs_directory.cli.store import store
from lgs_directory.cli.validate import validate


@click.group()
@click.version_option(package_name="lgs-directory")
def cli() -> None:
    """LGS Directory — US Local Game Store management CLI."""


cli.add_command(discover)
cli.add_command(presence)
cli.add_command(scrape)
cli.add_command(store)
cli.add_command(validate)
