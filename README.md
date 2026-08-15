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
- Explore the result on street, satellite, or bundled offline map layers
- Save optional text reports without the image's private folder path
- Protect saved API keys and guidance with Windows per-user encryption
- Keep preferences locally with no analytics or telemetry

The app connects directly to xAI Grok, Google Gemini, Anthropic, or OpenAI with the API key you provide. Each listed model supports image input, and the app uses separate regular-image and GeoGuessr prompt profiles.

## installation

1. Download and extract the release ZIP.
2. Double-click `Installer.bat`.
3. Let every setup check pass.
4. Double-click the `AI Location Finder` shortcut created in the folder.

The setup keeps the private Python runtime and packages inside the extracted folder. The app shortcut uses that runtime directly, so it does not depend on Microsoft Store or system Python. Setup does not need administrator access, change PATH, or install global packages. It also installs one small shared launcher in `%LOCALAPPDATA%\Fleece Tools\Python Launcher` and sets `.pyw` files to open with it for your Windows account. The launcher prefers the selected tool's sibling `.runtime\python\pythonw.exe` and keeps a legacy `.venv\Scripts\pythonw.exe` fallback for older Fleece Tool releases; it never uses another tool's Python. You can copy the shortcut to your Desktop or pin it to the taskbar.

Before the first Fleece Tools association change, setup exports any existing per-user `.pyw` settings to that shared folder. If the previous setting cannot be backed up safely, setup stops without overwriting it. A later non-Fleece choice is also left alone.

Setup installs or repairs official 64-bit Python 3.14.7 privately in `.runtime\python`; it does not use or modify Microsoft Store or system Python. Python, pip, PySide6-Essentials, and HTTPX are pinned and validated. Downloaded runtime archives are checked against pinned SHA-256 checksums.

Keep the extracted folder path at 72 characters or fewer to avoid Windows path-length failures while PySide6 is installed. Run `Installer.bat` again whenever you want to repair or update the private components, or after moving the extracted folder so the shortcut is recreated for its new location.

## usage

1. Open **AI Settings**, choose an AI service and model, then save that service's API key.
2. Choose one monitor, **All monitors**, or an image file.
3. Choose **Regular photo or screenshot** or **GeoGuessr screenshot**.
4. Set the analysis effort and number of AI checks.
5. Choose whether to save a text report.
6. Click **Find Location**.
7. Review the returned place, coordinates, confidence, evidence, and map pin.

The selected image and analysis prompt are sent only to the AI service you choose and only after you start an analysis. Additional checks normally increase cost and run time. Results are estimates and can be confidently wrong.

Street and satellite map details load online from OpenStreetMap or Esri. The bundled Natural Earth map remains available as an offline fallback.

## built with

- [PySide6](https://doc.qt.io/qtforpython-6/)
- [HTTPX](https://www.python-httpx.org/)
- [OpenStreetMap](https://www.openstreetmap.org/copyright)
- [Esri](https://www.esri.com/)
- [Natural Earth](https://www.naturalearthdata.com/)
- xAI, Google Gemini, Anthropic, and OpenAI direct APIs
- [Python](https://www.python.org/)

## privacy and removal

The app has no telemetry, analytics, advertisements, app accounts, or background image uploads. It sends the selected image and analysis context only to the provider you choose after you start an analysis. Visible online map areas require normal tile requests to OpenStreetMap or Esri. Provider data handling depends on the selected provider and account; review the in-app privacy note before sending a sensitive image.

API keys and optional guidance are encrypted separately for the current Windows user in `.runtime/settings.ini`. Reports are saved only when enabled and do not include the source image's full folder path. Setup logs can include local folder paths, so review them before sharing.

To remove only AI Location Finder, close it and delete the extracted folder. The app does not install a background service, add itself to startup, or create an uninstaller entry. Reports saved somewhere else and map tiles in Windows' application cache remain until you delete them separately.

The shared `.pyw` launcher is used by every installed Fleece Tool, so removing one tool does not remove it. To restore the `.pyw` settings that existed before Fleece Tools first configured them, run `%LOCALAPPDATA%\Fleece Tools\Python Launcher\Restore pyw association.cmd`. The restore helper refuses to overwrite a newer non-Fleece choice. After restoring, and after removing every Fleece Tool that uses it, you can delete the shared `Python Launcher` folder. The registry backup files can contain local application names and paths, so review them before sharing.

## source use

The source is public for transparency and security review. Copyright 2026 Fleece. All rights reserved. No license is granted to use, modify, redistribute, sell, or publish derivative versions beyond the limited rights provided by the hosting platform.

## note

This project was made with AI.

Only analyze images you own or have permission to send to the selected AI service. Do not use an estimated location to stalk, harass, dox, trespass, or endanger anyone.
