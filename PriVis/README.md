# PriVis

**See the Access. Reduce the Risk.**

PriVis is a local, read-only desktop app for reviewing account and group access from CSV files. It uses Python, Pandas, and PySide6 Qt Widgets. The included dataset is synthetic. The app works offline after dependencies are installed and requires no credentials or directory connection.

## Quick start

Install **Python 3.13**. Clone the repository or extract a copy of the source, then open a terminal in the folder containing `app.py`. Create a fresh virtual environment on each computer.

### macOS

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
sh launch.sh
```

Use `sh launch.sh` for subsequent launches. The launcher makes Qt platform plugins discoverable on macOS and cleans up its temporary copies after PriVis exits.

### Windows

Run in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B app.py
```

After setup, you can also double-click `launch.bat`. If your Python installation provides `python` instead of `py`, check `python --version` for 3.13 and use `python -m venv .venv` in the first step.

## Using PriVis

PriVis opens the bundled `data/sample` folder and uses the computer's local date. **Open Data Folder…** loads another validated dataset. If the load fails, the previous review stays available.

| Screen | What it shows |
| --- | --- |
| Overview | Account, group, and finding totals, plus severity distribution |
| Users and Groups | Searchable tables, direct memberships, and selected-record details |
| Findings | Severity, matching rule, explanation, and review recommendation |
| Simulations | Before-and-after findings for removing one direct membership |
| Advanced | Access and approval evidence, policy coverage, and a remediation sandbox |

In **Advanced → Solutions**, **Execute Highlighted Fix** and **Execute All Fixes** apply actions to the session sandbox. They disable expired accounts or remove the relevant denied or unapproved direct memberships. The app recalculates findings after each execution. Reopen the data folder to reset the sandbox. Source files stay untouched.

## Data

Place the four CSVs together in one folder. Use the headers in the bundled files as templates.

- `users.csv` contains account identifiers, roles, departments, status, and optional end dates.
- `groups.csv` contains identifiers, risk levels, descriptions, and resource scopes.
- `memberships.csv` links users to groups and contains approval status, optional tickets, and expiry dates.
- `access_policy.csv` defines access decisions and reasons by role and group.

Files must be UTF-8 and at most 10 MiB each. Enabled values are `TRUE` or `FALSE`. Dates use `YYYY-MM-DD`. Keep private datasets outside the repository and select them through the app.

The engine checks enabled accounts with past end dates, explicitly denied memberships, and approval-required memberships without valid approval. Approval requires a ticket and an expiry date. End dates and approvals remain valid through the stated date. Advanced Policy Coverage surfaces direct memberships without a matching rule.

## Verification

From the project root on macOS:

```sh
.venv/bin/python -B data_loader.py
.venv/bin/python -B security_analysis.py --as-of 2026-11-14
.venv/bin/python -B -m unittest discover -s tests -v
```

In Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B data_loader.py
.\.venv\Scripts\python.exe -B security_analysis.py --as-of 2026-11-14
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The sample contains 12 users, 8 groups, 30 direct memberships, and 26 policies. The fixed-date review reports 5 findings. The desktop app uses the local date, so the total can change over time.

If the macOS test command reports a missing Cocoa plugin, run the test suite offscreen with the installed Qt plugin copied to a temporary directory:

```sh
qt_plugins=$(.venv/bin/python -c 'from PySide6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))')
(
  test_plugins=$(mktemp -d)
  trap 'rm -rf "$test_plugins"' EXIT
  cp "$qt_plugins/platforms/libqoffscreen.dylib" "$test_plugins/" &&
  chflags nohidden "$test_plugins/libqoffscreen.dylib" &&
  QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORM_PLUGIN_PATH="$test_plugins" \
    .venv/bin/python -B -m unittest discover -s tests -v
)
```
