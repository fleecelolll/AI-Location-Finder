<div align="center">

# ai location finder

A little tool I made with AI to estimate real-world locations from screenshots and images locally on 64-bit Windows.

<img src="AI%20Location%20Finder.png" alt="AI Location Finder app window" width="760">

</div>

## features

- Choose one monitor, all monitors, or an existing image
- Use regular-image or GeoGuessr-focused analysis
- Choose from four direct AI services and twelve curated vision models
- Set analysis effort and run one to three AI checks
- Review the estimated place, coordinates, confidence, and evidence
- Explore street, satellite, and bundled offline map layers
- Save optional reports without exposing the image's private folder path
- Protect saved API keys and guidance with Windows per-user encryption

## requirements

- 64-bit x64 or ARM64 Windows
- An internet connection during first setup
- An API key for xAI, Google Gemini, Anthropic, or OpenAI
- An internet connection while using an AI service or online map layer

## installation

1. Download the latest release ZIP.
2. Extract the complete folder.
3. Double-click `Installer.bat`.
4. Press **Y** once to approve setup.
5. Leave the setup window open until every check passes.
6. Double-click the `AI Location Finder` shortcut created in the folder.

Keep the full extracted folder path at 72 characters or fewer so Windows can install the private packages reliably.

Setup keeps the private Python runtime and all app-specific components inside the extracted folder. It does not require administrator access, change PATH, or install global Python packages. The shortcut starts the app with that private runtime, so Microsoft Store or system Python is not required.

Setup pins and verifies official Python 3.14.7, pip, PySide6-Essentials, and HTTPX. Downloaded runtime archives are checked against pinned SHA-256 hashes before use.

Setup also installs one small shared per-user launcher in `%LOCALAPPDATA%\Fleece Tools\Python Launcher` and safely associates `.pyw` files with it for the current Windows account. It backs up an existing per-user association before the first change and never borrows another tool's Python runtime.

Run `Installer.bat` again to repair the private components or after moving the complete folder. Setup preserves saved provider keys and preferences and recreates the shortcut for the folder's current location.

## usage

1. Open **AI Settings**, choose a service and model, and save that service's API key.
2. Choose one monitor, all monitors, or an image file.
3. Choose the regular-image or GeoGuessr analysis profile.
4. Set the analysis effort and number of checks.
5. Click **Find Location**.
6. Review the estimated location, evidence, coordinates, confidence, and map.

The selected image and analysis context are sent only to the provider you choose and only after you start an analysis. Extra checks can increase cost and run time. Location results are estimates and can be wrong.

## built with

- [PySide6](https://doc.qt.io/qtforpython-6/)
- [HTTPX](https://www.python-httpx.org/)
- [OpenStreetMap](https://www.openstreetmap.org/copyright)
- [Esri](https://www.esri.com/)
- [Natural Earth](https://www.naturalearthdata.com/)
- xAI, Google Gemini, Anthropic, and OpenAI direct APIs
- [Python](https://www.python.org/)

## privacy and removal

The app has no telemetry, analytics, advertisements, app accounts, or background image uploads. Online provider and map requests occur only for the features you choose. API keys and optional guidance are encrypted separately for the current Windows user in `.runtime\settings.ini`. Setup logs can contain local folder paths, so review them before sharing.

To remove only AI Location Finder, close it and delete the extracted folder. The app does not install a background service, add itself to startup, or create an uninstaller entry.

The shared `.pyw` launcher can be used by every installed Fleece Tool, so removing one tool does not remove it. To restore the association that existed before Fleece Tools first configured it, run `%LOCALAPPDATA%\Fleece Tools\Python Launcher\Restore pyw association.cmd` after closing every Fleece Tool.

## troubleshooting

If setup stops, review `setup.log`, correct the listed problem, and run `Installer.bat` again. Setup reports success only after its dependencies, offline self-tests, and shortcut all pass.

If the `AI Location Finder` shortcut does not open, run `Installer.bat` again and keep the complete extracted folder together. Setup recreates and validates the shortcut for the folder's current location.

Street and satellite layers need internet access. The bundled Natural Earth layer remains available as an offline fallback.

## source use

The source is public for transparency and security review. Copyright 2026 Fleece. All rights reserved. No permission is granted to use, copy, modify, redistribute, sell, or publish derivative versions. See [LICENSE](LICENSE).

## note

This project was made with AI.

Only analyze images you own or have permission to send to the selected AI service. Do not use an estimated location to stalk, harass, dox, trespass, or endanger anyone.
