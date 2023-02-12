# sync-debs-to-gemfury

[![Sponsor on GitHub](https://img.shields.io/github/sponsors/Jackenmen?logo=github)](https://github.com/sponsors/Jackenmen)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
[![We use pre-commit!](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> Synchronize deb packages to Gemfury repository.
> Useful for debs that aren't distributed through an apt repository.

## Basic usage

Create a YAML file in `.github/workflows` directory of your repository,
e.g. `.github/workflows/sync_debs_to_gemfury.yaml` with content:

```yaml
name: Synchronize deb packages to Gemfury repository.
on:
  schedule:
    - cron: '42 * * * *'
  workflow_dispatch:

permissions:
  issues: write
  contents: write

jobs:
  sync_debs_to_gemfury:
    runs-on: ubuntu-latest
    steps:
      - name: Synchronize deb packages to Gemfury repository.
        uses: Jackenmen/sync-debs-to-gemfury@v1
        env:
          GEMFURY_USERNAME: YOUR_USERNAME
          GEMFURY_PUSH_TOKEN: ${{ secrets.gemfury_push_token }}
```

Create a configuration file named `config.yaml` at the root of the repository with package list:

```yaml
---
packages:
  discord:
    type: direct_url
    config:
      url: https://discord.com/api/download?platform=linux&format=deb

  heroic:
    type: github_release
    config:
      repository: Heroic-Games-Launcher/HeroicGamesLauncher
      asset_name_pattern: _amd64.deb$
```

## Environment variables

### `GEMFURY_USERNAME`

Your Gemfury personal or organisation username.

### `GEMFURY_PUSH_TOKEN`

Gemfury push token.

## Configuration file

Configuration file is a YAML file used to configure a list of packages.

The base format looks as follows:

```yaml
packages:
  PACKAGE_NAME:
    type: PACKAGE_DOWNLOAD_TYPE
    config:
      # type-specific configuration
      url: https://url-to-package-file.com/used-in-direct_url-type.deb
```

## Available package download types

### `direct_url`

This download type can be used when a package's latest .deb file is available at a static direct url.

Available options:

- `url` - URL to the .deb file.

### `github_release`

This download type can be used for packages that are uploaded as part of a GitHub release.
It gets the latest stable release and finds the .deb file using provided asset name pattern.

Available options:

- `repository` - repository owner and name in a format: `owner/name`
- `asset_name_pattern` - regex pattern for the names of assets that are relevant .deb files

## License

Distributed under the Apache License 2.0. See ``LICENSE`` for more information.

---

> Jakub Kuczys &nbsp;&middot;&nbsp;
> GitHub [@Jackenmen](https://github.com/Jackenmen)
