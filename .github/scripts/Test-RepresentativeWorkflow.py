"""Exercise a synthetic image through the real UI/worker/provider request path.

The provider transport is mocked in-process. No real image, key, provider call,
map request, or paid API request is involved.
"""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time


release = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(release))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import httpx
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

import location_providers


loader = importlib.machinery.SourceFileLoader(
    "fleece_location_representative", str(release / "AI Location Finder.pyw")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)

requests = []
location = {
    "found": True,
    "location": "Synthetic Test Harbor",
    "country": "Testland",
    "latitude": 12.25,
    "longitude": -34.5,
    "confidence_km": 10,
    "confidence_percent": 90,
    "evidence": ["Synthetic skyline geometry"],
}


def handle(request):
    if request.method != "POST" or request.url.host != "api.openai.com":
        raise AssertionError("The app selected an unexpected provider request.")
    body = json.loads(request.content)
    if body.get("store") is not False or not body.get("model"):
        raise AssertionError("The direct request lost its model or no-store setting.")
    requests.append(body)
    response = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(location)}],
            }
        ],
    }
    return httpx.Response(200, json=response)


application = QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory(prefix="fleece-ai-workflow-") as temporary:
    folder = Path(temporary)
    image_file = folder / "synthetic-test-harbor.png"
    image = QImage(640, 360, QImage.Format_RGB32)
    image.fill(QColor("#334455"))
    if not image.save(str(image_file), "PNG"):
        raise AssertionError("The synthetic image could not be saved.")
    settings_path = folder / "settings.ini"
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.setValue("save_results_enabled", False)
    settings.sync()
    window = module.LocationFinder(settings_path=settings_path, testing=True)
    client = httpx.Client(transport=httpx.MockTransport(handle), trust_env=False)
    original_client_factory = location_providers._get_http_client
    location_providers._get_http_client = lambda: client
    try:
        window._confirm_model_privacy = lambda _model: True
        window.provider_dropdown.select(location_providers.provider_by_id("openai").label)
        window.passes_dropdown.select(module.PASS_OPTIONS[0])
        window.set_source_file(image_file)
        window.api_key_input.setText("ci-mock-key-not-a-real-secret")
        # set_source_file resolves the chosen path, including a hosted runner's
        # temporary-directory alias, before retaining it in the window.
        source_matches = window.source_file == image_file.resolve()
        selected_passes = window.selected_passes()
        if not source_matches or selected_passes != 1:
            raise AssertionError(
                "The synthetic user input was not selected: "
                f"canonical source matched={source_matches}, selected passes={selected_passes}."
            )
        window.start_analysis()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            application.processEvents()
            if not window.running and window.last_result is not None:
                break
            time.sleep(0.01)
        result = window.last_result
        if window.running or result is None:
            raise AssertionError("The mocked image-to-location workflow did not finish.")
        if len(requests) != 1 or result.location != location["location"]:
            raise AssertionError("The expected single mocked provider result was not shown.")
        if result.latitude != 12.25 or result.longitude != -34.5:
            raise AssertionError("The UI received incorrect coordinates.")
        if window.status_label.text() != "Done":
            raise AssertionError("The user-facing completion state was not shown.")
        print("Synthetic image -> real app worker -> mocked OpenAI transport -> UI result passed.")
    finally:
        location_providers._get_http_client = original_client_factory
        client.close()
        window.close()
        application.processEvents()
