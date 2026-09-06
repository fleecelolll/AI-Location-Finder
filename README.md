<div align="center">

# ai location finder

A little tool I made with AI to estimate real-world locations from screenshots and images locally on 64-bit Windows.

<img src="AI%20Location%20Finder.png" alt="AI Location Finder app window" width="760">

</div>

## features

- Choose one monitor, all monitors, or an existing image
- Use regular-image or GeoGuessr-focused analysis
- Choose from four direct AI services and thirteen curated vision models
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
4. Press **Y** once to accept the Terms and bundled Tool License and approve setup.
5. Leave the setup window open until every check passes.
6. Double-click the `AI Location Finder` shortcut created in the folder.

Keep the full extracted folder path at 72 characters or fewer so Windows can install the private packages reliably.

Setup keeps the private Python runtime, dependencies, settings, and every app component inside the extracted folder. It does not require administrator access, change PATH, or install global Python packages. The generated folder-local shortcut starts the app directly with that private runtime, so Microsoft Store or system Python is not required.

Setup pins and verifies official Python 3.14.7, pip, and the complete private PySide6-Essentials, HTTPX, and AnyIO dependency set. Downloaded runtime archives are checked against pinned SHA-256 hashes before use.

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

The app has no telemetry, analytics, advertisements, app accounts, or background image uploads. The map opens the last layer you selected, or Street on first run, so an online layer may request the currently visible OpenStreetMap or Esri tiles before you start AI analysis. Those map providers do not receive your selected image, AI prompt, or API key. API keys and optional guidance are encrypted separately for the current Windows user in `.runtime\settings.ini`. Setup logs can contain local folder paths, so review them before sharing.

To remove AI Location Finder, close it and delete the extracted folder. This removes its folder-local shortcut, private runtime, dependencies, settings, and app files. The app does not install a background service, add itself to startup, or create an uninstaller entry.

## troubleshooting

If setup stops, review `setup.log`, correct the listed problem, and run `Installer.bat` again. Setup reports success only after its dependencies, offline self-tests, and shortcut all pass.

If the `AI Location Finder` shortcut does not open, run `Installer.bat` again and keep the complete extracted folder together. Setup recreates and validates the shortcut for the folder's current location.

Street and satellite layers need internet access. The bundled Natural Earth layer remains available as an offline fallback.

## license

Copyright 2026 Fleece. This project is source-available, not open source. The bundled [LICENSE](LICENSE) permits downloading, installing, and running an unmodified official release for lawful personal, non-commercial use. Modification, redistribution, sale, rebranding, and derivative versions remain prohibited. Third-party materials retain their own licenses.

## note

This project was made with AI.

Only analyze images you own or have permission to send to the selected AI service. Do not use an estimated location to stalk, harass, dox, trespass, or endanger anyone.
