# FinderPilot

Two small Finder tools for macOS. Double-click them from a Finder window and they do the thing you were about to walk to a terminal and type.

| App | What it does |
|---|---|
| **Open in Pi** | Select a folder in Finder, double-click — launches the [pi](https://github.com/earendil-works/pi) coding agent rooted at that folder |
| **New Markdown** | Double-click — creates a `.md` file in the front Finder window and selects it |

No config, no daemon, no dependencies. Two AppleScript applets and a build script.

## Why it works this way

These ship as **source, not as `.app` bundles**. The installer compiles them on your machine with `osacompile` and signs them ad-hoc.

That sidesteps the whole problem: a pre-built `.app` copied from another Mac carries a quarantine attribute and an ad-hoc signature that Gatekeeper rejects, so it either refuses to open or demands a right-click override every time. Compiling locally sidesteps all of it — the signature is minted on the machine that will run it.

The build output is universal, so the same install works on Apple Silicon and Intel.

## Requirements

macOS only.

The apps themselves need nothing beyond a stock system. **Open in Pi** needs the `pi` command:

```bash
npm install -g @earendil-works/pi-coding-agent
```

New Markdown has no dependencies at all.

## Install

```bash
git clone https://github.com/afeicn/FinderPilot.git
cd FinderPilot
./install.sh
```

Both apps land in `/Applications`.

### Other options

```bash
./install.sh --uninstall                        # remove both apps
./install.sh --help                             # usage
FINDERPILOT_DIR=~/Applications ./install.sh     # install elsewhere
```

Re-running the installer is safe. If an app already exists, the old version is moved to `backup/` before being replaced.

## Use

**Open in Pi** reads your Finder selection and uses the directory:

- folder selected → that folder
- file selected → its parent directory
- nothing selected → the front Finder window's folder
- no Finder window → Desktop

It opens a terminal, `cd`s there, and starts pi. If iTerm is already running it opens a new iTerm window; otherwise it uses Terminal.app.

**New Markdown** creates the file in the front Finder window's folder, then reveals and selects it. Name collisions get a counter, so you get `Untitled.md`, then `Untitled 1.md`, `Untitled 2.md`, and so on.

### Finder toolbar

Hold `⌘` in a Finder window and drag either app onto the toolbar. Both are designed for one-click access from there.

## Troubleshooting

**Double-clicking does nothing.**
The app is blocked. Right-click it → **Open** → confirm. One time per app.

**"Could not find the pi command."**
pi isn't installed, or your terminal PATH hasn't picked it up. Install it with the npm command above, then reopen your terminal and try again.

**No permission prompt appears on first launch.**
That's the same Gatekeeper block as above — right-click → Open.

**The app opens but nothing happens.**
macOS asks for permission to control Finder on first run. Click **OK**. If you clicked **Don't Allow**, re-enable it under System Settings → Privacy & Security → Automation.

## How it works under the hood

Both apps are AppleScript applets:

```
Open in Pi.app
└── Contents/
    ├── MacOS/applet          ← the standard applet launcher
    └── Resources/Scripts/
        └── main.scpt         ← the logic
```

`install.sh` runs `osacompile` on the `.applescript` sources in `src/`, swaps in the iconset from `icons/`, then runs `codesign --force --deep --sign -` and `xattr -cr`.

Editing the logic means editing the `.applescript` files and re-running the installer. Use **Script Editor** (in `/Applications/Utilities`). Mind the parenthesis pairing — AppleScript won't tell you where you mismatched, only that it failed to parse.

## Project layout

```
FinderPilot/
├── install.sh              build + install
├── src/
│   ├── open-in-pi.applescript
│   └── new-markdown.applescript
├── icons/
│   ├── pi.iconset/         π icon
│   └── md.iconset/         MD icon
├── build/                  build output (generated)
└── backup/                 previous installs (generated)
```

## License

MIT — see [LICENSE](LICENSE).

The pi name and logo belong to the [pi project](https://github.com/earendil-works/pi). This is an unofficial companion tool.