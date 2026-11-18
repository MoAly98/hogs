# hogs

Find out what is slowing down your Mac. `hogs` ranks the processes using the
most CPU, memory and energy, with their full commands, either in the terminal
or in a live browser view.

macOS only: it reads `ps`, `top` and `sysctl`. No dependencies beyond Python.

## Use

```
hogs                 # CPU, memory and energy rankings, 10 rows each
hogs mem -n 5        # one ranking, 5 rows
hogs energy          # takes about a second to sample
hogs cpu --full      # whole commands instead of cutting them to the terminal width
hogs cpu --live      # keep redrawing in the terminal, Ctrl-C to stop
hogs web             # live view in the browser, Ctrl-C to stop
```

Commands are cut to the terminal width only when printing to a terminal, so
`hogs | grep python` still sees every command in full.

In a terminal the tables are coloured the same way as the browser view: CPU
in blue, memory in yellow, energy in green, with the ranked column in bold.
Load turns red when it is more than the cores can run. Pipes get plain text,
and setting `NO_COLOR` turns colour off in a terminal too.

`--live` redraws the rankings in place every two seconds (change with
`--interval`), showing as many of the `-n` rows as fit the terminal height.
Your scrollback is back as it was once you stop it.

### Browser view

`hogs web` serves a page on `http://127.0.0.1:8765` (change with `--port`,
skip opening a browser with `--no-open`) that refreshes every two seconds:

- tiles for CPU, memory, load and swap, with a short history you can hover
- a table you can sort, filter and switch between processes and apps
- click a row for the full command, the chain of parents that started it, its
  children, and buttons that copy the command or a `kill` line

The server only listens on this machine and only answers requests addressed to
`127.0.0.1` or `localhost`, since command lines can contain secrets. The page
never kills anything itself.

## Install

From a clone of this repo:

```
uv tool install --editable .
```

This puts a `hogs` command on your PATH. It is editable, so changes in the
clone take effect without reinstalling.

## Develop

```
uv run pytest
```

- `processes.py`: the `Process` record, parsing of `ps` and `top`, ranking.
- `system.py`: load, cores, memory size and swap.
- `sampler.py`: runs the system commands and builds a `Snapshot`.
- `report.py`: terminal tables.
- `server.py`, `index.html`: the browser view.
- `cli.py`: the `hogs` command.

The energy figure is `top`'s power score, which tracks CPU use closely.
