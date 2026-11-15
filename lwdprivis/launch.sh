#!/bin/sh
# Start PriVis with a discoverable Qt platform plugin directory.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$project_dir"
python=.venv/bin/python

if [ ! -x "$python" ]; then
    echo "PriVis needs its .venv. See README.md for setup instructions." >&2
    exit 1
fi

if [ "$(uname -s)" = Darwin ]; then
    plugins=$("$python" -B -c 'from PySide6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))')
    case "$plugins" in
        "$project_dir"/.venv/*) ;;
        *)
            echo "Expected Qt plugins in the PriVis .venv, found: $plugins" >&2
            exit 1
            ;;
    esac
    if [ ! -f "$plugins/platforms/libqcocoa.dylib" ]; then
        echo "The Cocoa plugin is missing from $plugins/platforms. Check the PySide6 installation." >&2
        exit 1
    fi
    # Qt's directory scan skips files with the macOS hidden flag. A plain
    # copy to a private temporary directory leaves that flag behind.
    platforms=$(mktemp -d "${TMPDIR:-/tmp}/privis-qt.XXXXXXXX")
    trap 'rm -rf -- "$platforms"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    cp "$plugins/platforms/"*.dylib "$platforms/"
    chflags -R nohidden "$platforms"
    QT_QPA_PLATFORM_PLUGIN_PATH="$platforms" "$python" -B app.py "$@"
    exit
fi

exec "$python" -B app.py "$@"
