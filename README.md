# cu2

comic updater 2

## Description

cu2 (comic updater 2, forked from the unfortunately-intentionally-named [comic updater, mangafied](https://github.com/hamuko/cum)) is a tool designed for automated manga downloads from various online manga aggregate sites. It is inspired by some of the popular package managers used with Linux distributions and OS X. The file naming scheme is partially based Daiz's [Manga Naming Scheme](https://gist.github.com/Daiz/bb8424cfedd0f05b7386).

Documentation updates for the fork are a work in progress.  Please, feel free to file PRs for any documentation that does not reflect the changes in this fork.

## Installation

No official packaging at this time - installation from the master branch can be done like so:

    pip install git+https://github.com/matoro/cu2

Please note that cu2 currently requires **Python 3.3** or newer.

## Usage

To print out a list of available commands, use `cu2 --help`. For help with a particular command, use `cu2 COMMAND --help`.

### Configuration

Configuration is stored at `~/.cu2/config.json` (`%APPDATA%\cu2\config.json` for Windows) and overwrites the following default values. cu2 will not write login information supplied by the user at run-time back to the config file, but will store session cookies if any exist. Configuration can get read with the command `cu2 config get [SETTING]` and set using `cu2 config set [SETTING] [VALUE]`.

See the [Configuration](../../wiki/Configuration) wiki page for more details and available settings.

Support for the XDG specification will be coming soon.

### Commands

```
chapters   List all chapters for a manga series.
config     Get or set configuration options.
download   Download all available chapters.
edit       Modify settings for a follow.
follow     Follow a series.
  --directory TEXT  Directory which download the series chapters into.
  --download        Downloads the chapters for the added follows.
  --ignore          Ignores the chapters for the added follows.
follows    List all follows.
get        Download chapters by URL or by alias:chapter.
  --directory TEXT  Directory which download chapters into.
ignore     Ignore chapters for a series.
latest     List most recent chapter addition for series.
  --relative        Uses relative times instead of absolute times.
new        List all new chapters.
open       Open the series URL in a browser.
repair-db  Runs an automated database repair.
unfollow   Unfollow manga.
unignore   Unignore chapters for a series.
update     Gather new chapters from followed series.
  --fast            Skips series based on average release interval.
```

### Examples

```bash
# Update the database with possible new chapters for followed series.
$ cu2 update

# List all new, non-ignored chapters.
$ cu2 new

# Add a follow for a manga series.
$ cu2 follow https://dynasty-scans.com/series/gakkou_gurashi

# Print out the chapter list for the added series.
$ cu2 chapters gakkou-gurashi

# Ignore the first three chapters for the added series.
$ cu2 ignore gakkou-gurashi 2 3 1

# Change the alias for the added series.
$ cu2 edit gakkou-gurashi alias school-live

# Download all new, non-ignored chapters for the added series using the new alias.
$ cu2 download school-live
```

## Supported sites

See the [Supported sites](../../wiki/Supported-sites) wiki page for details.

## Dependencies

* [alembic](https://pypi.python.org/pypi/alembic)
* [beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4)
* [click](https://pypi.python.org/pypi/click/4.0)
* [natsort](https://pypi.python.org/pypi/natsort/4.0.3)
* [requests](https://pypi.python.org/pypi/requests/2.7.0)
* [SQLAlchemy](https://pypi.python.org/pypi/SQLAlchemy/1.0.6)

## Contribution

If you wish to contribute to cu2, please consult the [Contribution Guide](CONTRIBUTING.md) first to make everything a bit easier.
