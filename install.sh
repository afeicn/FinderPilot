#!/bin/bash
#
# FinderPilot installer
#
#   ./install.sh              build and install both apps
#   ./install.sh --uninstall  remove both apps
#   ./install.sh --help       show this message
#
# Apps are built from source on this machine (osacompile) and signed ad-hoc, so
# nothing here needs to pass Apple's notarization gate. Run it as many times as
# you like - it's idempotent.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_DIR/src"
ICON_DIR="$REPO_DIR/icons"
TARGET_DIR="${FINDERPILOT_DIR:-/Applications}"
BUILD_DIR="$REPO_DIR/build"
BACKUP_DIR="$REPO_DIR/backup"

BLUE='\033[0;34m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { printf "${GREEN}✓${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
fail() { printf "${RED}✗${NC} %s\n" "$1"; }
step() { printf "${BLUE}▸${NC} %s\n" "$1"; }
die()  { fail "$1"; exit 1; }

usage() {
	cat <<'EOF'
FinderPilot installer

  ./install.sh              build and install both apps
  ./install.sh --uninstall  remove both apps
  ./install.sh --help       show this message

Environment:
  FINDERPILOT_DIR   install somewhere other than /Applications
EOF
}

# Parallel arrays keep the fields unambiguous - no string parsing.
APP_NAMES=("Open in Pi" "New Markdown")
APP_SOURCES=("open-in-pi" "new-markdown")
APP_ICONS=("pi" "md")

app_count() { printf '%s' "${#APP_NAMES[@]}"; }

# ---------------------------------------------------------------- preflight
preflight() {
	[ "$(uname)" = "Darwin" ] || die "FinderPilot only runs on macOS."

	if ! command -v osacompile >/dev/null 2>&1; then
		die "osacompile not found. Install Xcode Command Line Tools: xcode-select --install"
	fi

	ok "macOS check passed ($(sw_vers -productVersion), $(uname -m))"
}

check_pi() {
	local p pi_bin=""
	for p in "$HOME/.local/bin/pi" /opt/homebrew/bin/pi /usr/local/bin/pi "$HOME/.pi/bin/pi"; do
		if [ -x "$p" ]; then pi_bin="$p"; break; fi
	done
	[ -z "$pi_bin" ] && pi_bin="$(command -v pi 2>/dev/null || true)"

	if [ -n "$pi_bin" ]; then
		ok "Found pi at $pi_bin"
	else
		warn "pi command not found"
		printf "  ${YELLOW}Open in Pi${NC} will explain how to install it when you first run it.\n"
		printf "    npm install -g @earendil-works/pi-coding-agent\n\n"
	fi
}

# ------------------------------------------------------------------- build
build_app() {
	local idx="$1"
	local name src iconset bundle tmp_icns
	name="${APP_NAMES[$idx]}"
	src="$SRC_DIR/${APP_SOURCES[$idx]}.applescript"
	iconset="$ICON_DIR/${APP_ICONS[$idx]}.iconset"
	bundle="$BUILD_DIR/$name.app"

	step "Building $name.app"
	rm -rf "$bundle"
	osacompile -o "$bundle" "$src"

	if [ -d "$iconset" ]; then
		tmp_icns="$(mktemp -t finderpilot).icns"
		if iconutil -c icns "$iconset" -o "$tmp_icns" 2>/dev/null; then
			cp "$tmp_icns" "$bundle/Contents/Resources/applet.icns"
			/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" \
				"$bundle/Contents/Info.plist" 2>/dev/null || true
		else
			warn "Icon synthesis failed, falling back to the default applet icon"
		fi
		rm -f "$tmp_icns"
	fi

	# Sign ad-hoc and strip quarantine so Gatekeeper stays out of the way.
	codesign --force --deep --sign - "$bundle" 2>/dev/null || true
	xattr -cr "$bundle" 2>/dev/null || true

	ok "$name.app built"
}

install_app() {
	local idx="$1"
	local name src_app dst_app
	name="${APP_NAMES[$idx]}"
	src_app="$BUILD_DIR/$name.app"
	dst_app="$TARGET_DIR/$name.app"

	[ -d "$src_app" ] || return 0

	if [ -e "$dst_app" ]; then
		mkdir -p "$BACKUP_DIR"
		rm -rf "$BACKUP_DIR/$name.app"
		mv "$dst_app" "$BACKUP_DIR/$name.app"
		warn "$name.app already existed - previous version backed up to backup/$name.app"
	fi

	if mv "$src_app" "$dst_app" 2>/dev/null; then
		ok "Installed $dst_app"
	elif command -v sudo >/dev/null 2>&1 && sudo mv "$src_app" "$dst_app" 2>/dev/null; then
		ok "Installed $dst_app (used sudo)"
	else
		warn "Could not write to $TARGET_DIR - move $src_app there manually"
	fi
}

uninstall_app() {
	local idx="$1"
	local dst_app="$TARGET_DIR/${APP_NAMES[$idx]}.app"

	if [ -e "$dst_app" ]; then
		rm -rf "$dst_app" && ok "Removed $dst_app" || warn "Could not remove $dst_app"
	else
		printf "  %s not found, skipping\n" "$dst_app"
	fi
}

# -------------------------------------------------------------------- main
main() {
	case "${1:-}" in
		--help|-h) usage; exit 0 ;;
		--uninstall)
			printf "\n${YELLOW}Removing FinderPilot apps${NC}\n\n"
			local i
			for ((i = 0; i < $(app_count); i++)); do uninstall_app "$i"; done
			printf "\nDone.\n\n"
			exit 0
			;;
	esac

	printf "\n"
	printf "======================================\n"
	printf "  FinderPilot installer\n"
	printf "======================================\n\n"

	preflight
	check_pi
	printf "\n"

	mkdir -p "$BUILD_DIR"
	local i
	for ((i = 0; i < $(app_count); i++)); do build_app "$i"; done

	printf "\n"
	step "Installing to $TARGET_DIR"
	for ((i = 0; i < $(app_count); i++)); do install_app "$i"; done

	printf "\n"
	printf "======================================\n"
	printf "  Done\n"
	printf "======================================\n\n"
	printf "  Open in Pi    Select a folder in Finder, then double-click the app.\n"
	printf "                It launches pi rooted at that folder. Uses iTerm when\n"
	printf "                iTerm is already running, otherwise Terminal.\n\n"
	printf "  New Markdown  Double-click to create a .md file in the front Finder\n"
	printf "                window and select it. Same-name files get a counter.\n\n"
	printf "  Toolbar       Hold ⌘ in a Finder window and drag either app onto the\n"
	printf "                toolbar for one-click access.\n\n"
	printf "  First launch  If macOS says the app can't be opened, right-click it\n"
	printf "                and choose Open. Only needed once per app.\n\n"
}

main "$@"