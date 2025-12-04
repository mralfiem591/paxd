---
name: PaxD-Package-Creation-Instructions
applyTo: '**'
description: Instructions for creating PaxD packages.
---

Welcome, AI model, to the instructions of creating a PaxD package.
PaxD is a python package manager, for python command-line or GUI applications.

Your package will be a folder, with a package.yaml, and a src/ directory.

The package.yaml serves as a file containing important data for PaxD to handle your package, and the src/ dir is your actual package.

# Package.yaml

Here is an example of a package.yaml.

```
name: PaxD
author: mralfiem591
version: 1.6.15
description: The main command line tool for using PaxD.
license: MIT
tags:
  - cli
  - package manager
  - installer
  - windows
  - tool
  - gateway
  - http
  - repository

install:
  files:
    - paxd.py
    - run_pkg.py
    - repository
    - LICENSE
    - asset/logo.png
    - asset/kris-susie-and-ralsei.png

  dependencies:
    pip:
      - requests
      - colorama
      - argparse
      - pyyaml
      - sentry-sdk
      - uv
    paxd:
      - com.mralfiem591.paxd-sdk
      - com.mralfiem591.paxd-imageview
  
  firstrun: true
  updaterun: true
  exclude_from_updates:
    - repository
  main_executable: paxd.py
  command_alias: paxd
  supports_fastxd: false
```

name, author, dexcription, license: pretty self-explanitory.
version: the version of this publish of the package, in format release.major.minor. This format is **REQUIRED** for PaxD to understand your versioning.
tags (optional, recommended): tags that you would use to describe your package. used to improve reach, and make your package more visible in `paxd search` commands.
install: contains the following parts:
    files: files from the src/ dir to contain in your package. PaxD will only request and download these files. Directories are kept intact - a file in src/asset/ will stay in asset/ relative to the main file.
    dependencies (optional): contains the following parts:
        pip (optional): packages to install with pip upon installing the package.
        winget (optional): packages to install with winget.
        choco (optional): packages to install with choco.
        npm (optional): packages to install with npm.
        paxd (optional): packages to install with paxd.
    firstrun (optional: default to false): create a FIRSTRUN file in the package root when it is installed for the first time.
    updaterun (optional: defaults to false): same as firstrun, but the file name is UPDATERUN and made after any update.
    exclude_from_updates (optional): files in the install > files part, that shouldnt be installed after an update (aka files that should be installed when the package is installed but not updated)
    main_executable (optional): the main file to run when this package is called. If this is set, command_alias should be set.
    command_alias (optional): the command the user can run to call the main executable. automatically added to PATH. args given to this are passed into the main executable.
    supports_fastxd (optional, HEAVILY recommended): controls if the package supports the FastxD system. this allows for temporary install of the package, into a temp directory. this can break some packages, and shouldnt be used on packages that write to exteral sources (like appdata)!
