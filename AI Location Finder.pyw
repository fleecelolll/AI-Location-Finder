import atexit
import base64
import ctypes
import html
import json
import math
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


APP_NAME = "AI Location Finder"
APP_VERSION = "1.0.6"
APP_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = APP_DIR / ".runtime"
SETTINGS_PATH = RUNTIME_DIR / "settings.ini"
SETUP_LOCK_DIR = RUNTIME_DIR / "setup.lock"
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
EMBEDDED_PYTHON = RUNTIME_DIR / "python" / "python.exe"
EMBEDDED_PYTHONW = RUNTIME_DIR / "python" / "pythonw.exe"
APP_MUTEX_NAMES = (
    r"Global\FleeceAILocationFinderApp",
    r"Local\FleeceAILocationFinderApp",
)
APP_MUTEX_NAME = APP_MUTEX_NAMES[0]
APP_MUTEX_HANDLE = None
PROVIDER_WARMUP_LOCK = threading.Lock()
PROVIDER_WARMUP_STARTED = False
PROVIDER_WARMUP_THREAD = None

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def show_native_error(message: str, title: str = APP_NAME):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    else:
        print(f"{title}: {message}", file=sys.stderr)


def bootstrap_local_python():
    current = os.path.normcase(os.path.realpath(sys.executable))
    for local_python, local_pythonw in (
        (VENV_PYTHON, VENV_PYTHONW),
        (EMBEDDED_PYTHON, EMBEDDED_PYTHONW),
    ):
        valid_executables = {
            os.path.normcase(os.path.realpath(path))
            for path in (local_python, local_pythonw)
            if path.is_file()
        }
        if current in valid_executables and sys.flags.isolated:
            return
        if not local_python.is_file() or not local_pythonw.is_file():
            continue
        try:
            if current not in valid_executables:
                validation = subprocess.run(
                    [str(local_python), "-I", "-c", "pass"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if validation.returncode != 0:
                    continue
            subprocess.Popen(
                [
                    str(local_pythonw),
                    "-I",
                    str(Path(__file__).resolve()),
                    *sys.argv[1:],
                ],
                cwd=str(APP_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            continue
        raise SystemExit(0)

    show_native_error(
        "Setup is missing, incomplete, or no longer usable.\n\n"
        "Run Installer.bat, let it finish, then open the AI Location Finder "
        "shortcut."
    )
    raise SystemExit(1)


if __name__ == "__main__":
    bootstrap_local_python()


try:
    import location_providers as provider_catalog
    from location_map import (
        WorldMapView,
        run_self_test as run_map_self_test,
        verify_map_asset,
    )
    from location_prompts import (
        accuracy_tips_text,
        build_analysis_prompt as build_model_prompt,
        prompt_profile_identifier,
        run_self_tests as run_prompt_self_tests,
    )
    from location_providers import (
        EFFORT_LABELS,
        MODELS,
        PROVIDERS,
        ProviderRequestError,
        call_vision_model,
        default_model,
        estimate_cost,
        model_by_id,
        models_for_provider,
        native_effort,
        prepare_vision_image,
        provider_by_id,
        self_test as provider_self_test,
        warm_provider_runtime,
    )
    from screen_capture import (
        ALL_MONITORS_ID,
        MONITOR_SETTING_KEY,
        ScreenCaptureError,
        capture_screen,
        enumerate_capture_targets,
        resolve_saved_target_from_targets,
        run_self_tests as run_capture_self_tests,
    )
    from PySide6.QtCore import (
        QBuffer,
        QByteArray,
        QEasingCurve,
        QEvent,
        QObject,
        QPoint,
        QPropertyAnimation,
        QRect,
        QRectF,
        QSettings,
        QSize,
        QThread,
        QTimer,
        Qt,
        QUrl,
        Signal,
        Slot,
    )
    from PySide6.QtGui import (
        QCloseEvent,
        QColor,
        QDesktopServices,
        QDragEnterEvent,
        QDropEvent,
        QImage,
        QImageReader,
        QMouseEvent,
        QPainter,
        QPen,
        QTextCursor,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QBoxLayout,
        QDialog,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLayout,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QScrollArea,
        QScrollBar,
        QSizeGrip,
        QSizePolicy,
        QTabBar,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    from shiboken6 import delete as delete_qt_object
except Exception:
    if __name__ == "__main__":
        show_native_error(
            "Setup is incomplete and the app window cannot load.\n\n"
            "Run Installer.bat again to repair the setup."
        )
        raise SystemExit(1)
    raise


if os.name == "nt":
    NATIVE_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    NATIVE_KERNEL32.CreateMutexW.argtypes = (
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    NATIVE_KERNEL32.CreateMutexW.restype = wintypes.HANDLE
    NATIVE_KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    NATIVE_KERNEL32.CloseHandle.restype = wintypes.BOOL
else:
    NATIVE_KERNEL32 = None


ERROR_ACCESS_DENIED = 5
ERROR_ALREADY_EXISTS = 183


def release_app_mutex():
    global APP_MUTEX_HANDLE
    if APP_MUTEX_HANDLE is None or NATIVE_KERNEL32 is None:
        return
    NATIVE_KERNEL32.CloseHandle(APP_MUTEX_HANDLE)
    APP_MUTEX_HANDLE = None


def _try_create_named_mutex(name: str):

    if NATIVE_KERNEL32 is None:
        return "unavailable", None
    ctypes.set_last_error(0)
    handle = NATIVE_KERNEL32.CreateMutexW(None, False, name)
    error_code = ctypes.get_last_error()
    if handle and error_code == ERROR_ALREADY_EXISTS:
        NATIVE_KERNEL32.CloseHandle(handle)
        return "exists", None
    if handle:
        return "acquired", handle
    if error_code == ERROR_ACCESS_DENIED:
        return "denied", None
    return "failed", None


def acquire_app_mutex() -> bool:
    global APP_MUTEX_HANDLE, APP_MUTEX_NAME
    if NATIVE_KERNEL32 is None:
        return True
    for index, name in enumerate(APP_MUTEX_NAMES):
        status, handle = _try_create_named_mutex(name)
        if status == "acquired":
            APP_MUTEX_NAME = name
            APP_MUTEX_HANDLE = handle
            atexit.register(release_app_mutex)
            return True
        if status == "exists":
            return False
        if index == 0 and status == "denied":
            continue
        return False
    return False


def start_provider_runtime_warmup(warm_callback=None):

    global PROVIDER_WARMUP_STARTED, PROVIDER_WARMUP_THREAD
    callback = warm_callback or warm_provider_runtime
    with PROVIDER_WARMUP_LOCK:
        if PROVIDER_WARMUP_STARTED:
            return PROVIDER_WARMUP_THREAD
        thread = threading.Thread(
            target=_run_provider_runtime_warmup,
            args=(callback,),
            name="AILocationProviderWarmup",
            daemon=True,
        )
        PROVIDER_WARMUP_STARTED = True
        PROVIDER_WARMUP_THREAD = thread
        try:
            thread.start()
        except Exception:
            PROVIDER_WARMUP_STARTED = False
            PROVIDER_WARMUP_THREAD = None
            return None
        return thread


def _run_provider_runtime_warmup(callback):
    try:
        callback()
    except Exception:
        pass


def handle_unhandled_exception(error_type, error, trace):
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / "error.log").write_text(
            "".join(traceback.format_exception(error_type, error, trace)),
            encoding="utf-8",
        )
    except OSError:
        pass
    show_native_error(
        "The app stopped because of an unexpected error.\n\n"
        "Run Installer.bat again. If it still happens, check "
        ".runtime\\error.log."
    )
    application = QApplication.instance()
    if application is not None:
        application.quit()


class DataBlob(ctypes.Structure):
    _fields_ = (
        ("size", wintypes.DWORD),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
    )


def _input_blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    blob = DataBlob(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


DPAPI_UI_FORBIDDEN = 0x01
PROTECTED_SECRET_PREFIX = "dpapi2:"
PROTECTED_SECRET_MAGIC = "AILF-PROTECTED-SETTING-V2\0"
MAX_CLEAR_SECRET_BYTES = 16 * 1024
MAX_PROTECTED_SECRET_BYTES = 64 * 1024
MAX_PROTECTED_SECRET_TEXT = 96 * 1024
PROTECTED_PROVIDER_IDS = frozenset(("xai", "google", "anthropic", "openai"))
REDACTED_SECRET = "[redacted]"


def _free_local_blob(blob: DataBlob, wipe=False):
    if not bool(blob.data):
        return
    if wipe and blob.size:
        ctypes.memset(blob.data, 0, blob.size)
    local_free = ctypes.windll.kernel32.LocalFree
    local_free.argtypes = (ctypes.c_void_p,)
    local_free.restype = ctypes.c_void_p
    local_free(ctypes.cast(blob.data, ctypes.c_void_p))


def _secret_entropy(purpose: str) -> bytes:
    purpose_text = str(purpose or "").strip()
    if not purpose_text or "\0" in purpose_text or len(purpose_text) > 128:
        raise OSError("Protected settings could not be processed.")
    return (APP_NAME + "\0protected-settings-v2\0" + purpose_text).encode("utf-8")


def _secret_plaintext_prefix(purpose: str) -> str:
    _secret_entropy(purpose)
    return PROTECTED_SECRET_MAGIC + purpose + "\0"


def _protect_dpapi_payload(secret: str, entropy: Optional[bytes]) -> bytes:
    if os.name != "nt":
        raise OSError("Windows data protection is unavailable.")
    try:
        clear_bytes = secret.encode("utf-8")
    except (AttributeError, UnicodeError):
        raise OSError("Protected settings could not be processed.") from None
    if not clear_bytes or len(clear_bytes) > MAX_CLEAR_SECRET_BYTES:
        raise OSError("Protected settings could not be processed.")

    source, source_buffer = _input_blob(clear_bytes)
    entropy_blob = None
    entropy_buffer = None
    entropy_pointer = None
    if entropy:
        entropy_blob, entropy_buffer = _input_blob(entropy)
        entropy_pointer = ctypes.byref(entropy_blob)
    protected = DataBlob()
    try:
        crypt32 = ctypes.windll.crypt32
        crypt32.CryptProtectData.argtypes = (
            ctypes.POINTER(DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        )
        crypt32.CryptProtectData.restype = wintypes.BOOL
        if not crypt32.CryptProtectData(
            ctypes.byref(source),
            APP_NAME,
            entropy_pointer,
            None,
            None,
            DPAPI_UI_FORBIDDEN,
            ctypes.byref(protected),
        ):
            raise OSError("Windows data protection failed.")
        if not protected.size or protected.size > MAX_PROTECTED_SECRET_BYTES:
            raise OSError("Windows data protection returned invalid data.")
        return ctypes.string_at(protected.data, protected.size)
    except Exception:
        raise OSError("Windows could not protect app data.") from None
    finally:
        if clear_bytes:
            ctypes.memset(ctypes.addressof(source_buffer), 0, len(clear_bytes))
        if entropy_buffer is not None and entropy:
            ctypes.memset(ctypes.addressof(entropy_buffer), 0, len(entropy))
        _free_local_blob(protected)


def _unprotect_dpapi_payload(payload: bytes, entropy: Optional[bytes]) -> str:
    if os.name != "nt":
        raise OSError("Windows data protection is unavailable.")
    if not payload or len(payload) > MAX_PROTECTED_SECRET_BYTES:
        raise OSError("Saved protected data could not be decrypted.")

    source, source_buffer = _input_blob(payload)
    entropy_blob = None
    entropy_buffer = None
    entropy_pointer = None
    if entropy:
        entropy_blob, entropy_buffer = _input_blob(entropy)
        entropy_pointer = ctypes.byref(entropy_blob)
    clear = DataBlob()
    try:
        crypt32 = ctypes.windll.crypt32
        crypt32.CryptUnprotectData.argtypes = (
            ctypes.POINTER(DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        )
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        if not crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            entropy_pointer,
            None,
            None,
            DPAPI_UI_FORBIDDEN,
            ctypes.byref(clear),
        ):
            raise OSError("Windows data protection failed.")
        if not clear.size or clear.size > MAX_CLEAR_SECRET_BYTES:
            raise OSError("Windows data protection returned invalid data.")
        return ctypes.string_at(clear.data, clear.size).decode("utf-8")
    except Exception:
        raise OSError("Saved protected data could not be decrypted.") from None
    finally:
        if payload:
            ctypes.memset(ctypes.addressof(source_buffer), 0, len(payload))
        if entropy_buffer is not None and entropy:
            ctypes.memset(ctypes.addressof(entropy_buffer), 0, len(entropy))
        _free_local_blob(clear, wipe=True)


def protect_local_secret(secret: str, purpose="local-setting") -> str:
    protected_plaintext = _secret_plaintext_prefix(purpose) + secret
    payload = _protect_dpapi_payload(
        protected_plaintext,
        _secret_entropy(purpose),
    )
    return PROTECTED_SECRET_PREFIX + base64.b64encode(payload).decode("ascii")


def _unprotect_local_secret_state(protected_text: str, purpose: str):
    text = str(protected_text or "").strip()
    if not text or len(text) > MAX_PROTECTED_SECRET_TEXT:
        raise OSError("Saved protected data could not be decrypted.")
    current_format = text.startswith(PROTECTED_SECRET_PREFIX)
    encoded = text[len(PROTECTED_SECRET_PREFIX):] if current_format else text
    try:
        payload = base64.b64decode(encoded, validate=True)
    except Exception:
        raise OSError("Saved protected data could not be decrypted.") from None
    entropy = _secret_entropy(purpose) if current_format else None
    secret = _unprotect_dpapi_payload(payload, entropy)
    if current_format:
        plaintext_prefix = _secret_plaintext_prefix(purpose)
        if not secret.startswith(plaintext_prefix):
            raise OSError("Saved protected data could not be decrypted.")
        secret = secret[len(plaintext_prefix):]
        if not secret:
            raise OSError("Saved protected data could not be decrypted.")
    return secret, not current_format


def unprotect_local_secret(protected_text: str, purpose="local-setting") -> str:
    secret, _ = _unprotect_local_secret_state(protected_text, purpose)
    return secret


def redact_secret_text(message, *secrets) -> str:
    text = str(message or "")
    for secret in secrets:
        secret_text = str(secret or "")
        if secret_text:
            text = text.replace(secret_text, REDACTED_SECRET)
    return text


def _sync_protected_settings(settings):
    settings.sync()
    if settings.status() != QSettings.Status.NoError:
        raise OSError("Protected settings could not be saved.")


def _validated_provider_id(provider_id: str) -> str:
    provider_text = str(provider_id or "").strip()
    if provider_text not in PROTECTED_PROVIDER_IDS:
        raise ValueError("Unknown AI service.")
    return provider_text


def _provider_key_setting(provider_id: str) -> str:
    return f"api_keys/{_validated_provider_id(provider_id)}/protected"


def _provider_key_purpose(provider_id: str) -> str:
    return "provider-api-key:" + _validated_provider_id(provider_id)


def load_saved_provider_key(settings, provider_id: str):
    provider_id = _validated_provider_id(provider_id)
    setting = _provider_key_setting(provider_id)
    purpose = _provider_key_purpose(provider_id)
    protected = str(settings.value(setting, "") or "").strip()
    if protected:
        key, needs_upgrade = _unprotect_local_secret_state(protected, purpose)
        if needs_upgrade:
            settings.setValue(setting, protect_local_secret(key, purpose))
            _sync_protected_settings(settings)
        if provider_id == "anthropic" and (
            settings.contains("api_key_protected") or settings.contains("api_key")
        ):
            settings.remove("api_key_protected")
            settings.remove("api_key")
            _sync_protected_settings(settings)
        return key, False

    if provider_id != "anthropic":
        return "", False

    legacy_protected = str(settings.value("api_key_protected", "") or "").strip()
    legacy_plain = str(settings.value("api_key", "") or "").strip()
    if not legacy_protected and not legacy_plain:
        return "", False
    if legacy_protected:
        key, _ = _unprotect_local_secret_state(
            legacy_protected,
            "legacy-single-api-key",
        )
    else:
        if len(legacy_plain.encode("utf-8")) > MAX_CLEAR_SECRET_BYTES:
            raise OSError("Saved protected data could not be migrated.")
        key = legacy_plain

    migrate_anthropic = key.casefold().startswith("sk-ant-")
    if migrate_anthropic:
        settings.setValue(setting, protect_local_secret(key, purpose))
        _sync_protected_settings(settings)
    settings.remove("api_key_protected")
    settings.remove("api_key")
    _sync_protected_settings(settings)
    return (key, True) if migrate_anthropic else ("", False)


def save_provider_key(settings, provider_id: str, key: str):
    provider_id = _validated_provider_id(provider_id)
    setting = _provider_key_setting(provider_id)
    clean_key = str(key or "").strip()
    if clean_key:
        settings.setValue(
            setting,
            protect_local_secret(clean_key, _provider_key_purpose(provider_id)),
        )
    else:
        settings.remove(setting)
    if provider_id == "anthropic":
        settings.remove("api_key_protected")
        settings.remove("api_key")
    _sync_protected_settings(settings)


def load_saved_extra_guidance(settings) -> str:
    setting = "extra_guidance_protected"
    purpose = "extra-guidance"
    protected = str(settings.value(setting, "") or "").strip()
    if protected:
        guidance, needs_upgrade = _unprotect_local_secret_state(protected, purpose)
        if needs_upgrade:
            settings.setValue(setting, protect_local_secret(guidance, purpose))
            _sync_protected_settings(settings)
        if settings.contains("extra_guidance"):
            settings.remove("extra_guidance")
            _sync_protected_settings(settings)
        return guidance[:1200]

    legacy_plain = str(settings.value("extra_guidance", "") or "")[:1200]
    if not legacy_plain:
        return ""
    settings.setValue(setting, protect_local_secret(legacy_plain, purpose))
    _sync_protected_settings(settings)
    settings.remove("extra_guidance")
    _sync_protected_settings(settings)
    return legacy_plain


def save_extra_guidance(settings, guidance: str):
    clean_guidance = str(guidance or "").strip()[:1200]
    if clean_guidance:
        settings.setValue(
            "extra_guidance_protected",
            protect_local_secret(clean_guidance, "extra-guidance"),
        )
    else:
        settings.remove("extra_guidance_protected")
    settings.remove("extra_guidance")
    _sync_protected_settings(settings)


def saved_bool(settings, key: str, default=True) -> bool:

    value = settings.value(key, default)
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().casefold()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return bool(default)


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_INPUT_IMAGE_PIXELS = 64_000_000
MAX_IMAGE_LONG_EDGE = 2576
HAIKU_MAX_IMAGE_LONG_EDGE = 1568
HAIKU_MAX_VISUAL_TOKENS = 1568
IMAGE_PATCH_SIZE = 28
UPLOAD_QUALITY_BY_EFFORT = {
    "Low": 95,
    "Medium": 97,
    "High": 99,
    "Ultra": 99,
}
PNG_SIZE_LIMIT = 5 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 180.0
MAX_IMAGE_LONG_EDGE_BY_EFFORT = {
    "Low": 2048,
    "Medium": 2304,
    "High": 2496,
    "Ultra": MAX_IMAGE_LONG_EDGE,
}
DIRECT_PROVIDER_ORDER = ("xai", "google", "anthropic", "openai")
MAP_PREFERENCE_SCHEMA_VERSION = 2

SOURCE_OPTIONS = ("Screen capture", "Image file")
EMPTY_IMAGE_LABEL = "Choose or drop an image"
EMPTY_IMAGE_TOOLTIP = (
    "Choose an image file with Browse, or drop an image into the app."
)
PROMPT_OPTIONS = ("GeoGuessr screenshot", "Regular photo or screenshot")
PASS_OPTIONS = (
    "1 AI check - fastest",
    "2 AI checks - reviewed",
    "3 AI checks - thorough",
)
PASSES_BY_LABEL = {label: index for index, label in enumerate(PASS_OPTIONS, 1)}

EFFORT_EXPLANATIONS = {
    "Low": "does a quicker first look",
    "Medium": "balances speed with careful checking",
    "High": "gives the AI more time to check details",
    "Ultra": "uses the deepest available reasoning for difficult images",
}

def direct_providers():

    indexed = {provider.id: provider for provider in PROVIDERS}
    chosen = tuple(
        indexed[provider_id]
        for provider_id in DIRECT_PROVIDER_ORDER
        if provider_id in indexed
    )
    return chosen


def model_privacy_notice(model):

    warning = None
    helper = getattr(provider_catalog, "privacy_warning_for_model", None)
    if callable(helper):
        warning = helper(model)
    if warning is None:
        warning = getattr(model, "privacy_warning", None)
    if warning is not None:
        return {
            "title": str(getattr(warning, "title", "Model privacy warning")),
            "message": str(
                getattr(
                    warning,
                    "message",
                    "This model has provider-specific retention or privacy terms.",
                )
            ),
            "link_label": str(
                getattr(warning, "details_label", "Review official privacy details")
            ),
            "link_url": str(getattr(warning, "details_url", "")),
            "accept_label": str(getattr(warning, "accept_label", "OK")),
            "cancel_label": str(getattr(warning, "cancel_label", "Cancel")),
        }

    return None


def accuracy_tip_sections():

    heading_names = {
        "choose the right image": "Regular photos and screenshots",
        "for geoguessr": "GeoGuessr",
        "pick sensible settings": "Settings",
    }
    source_lines = accuracy_tips_text().splitlines()
    if source_lines and source_lines[0].strip().casefold().startswith("how to get"):
        source_lines = source_lines[1:]

    sections = []
    heading = "Regular photos and screenshots"
    tips = []
    current_tip = ""

    def finish_tip():
        nonlocal current_tip
        if current_tip:
            tips.append(current_tip)
            current_tip = ""

    def finish_section():
        nonlocal tips
        finish_tip()
        if tips:
            sections.append((heading, tuple(tips)))
            tips = []

    for raw_line in source_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("* "):
            finish_tip()
            current_tip = stripped[2:].strip()
        elif current_tip and raw_line[:1].isspace():
            current_tip += " " + stripped
        else:
            finish_section()
            heading = heading_names.get(stripped.casefold(), stripped)
    finish_section()
    return tuple(sections)


def numbered_accuracy_tips() -> str:

    blocks = []
    for heading, tips in accuracy_tip_sections():
        lines = [heading]
        for number, tip in enumerate(tips, 1):
            lines.extend((f"{number}. {tip}", ""))
        while lines and not lines[-1]:
            lines.pop()
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def accuracy_tips_html() -> str:

    sections = []
    for section_index, (heading, tips) in enumerate(accuracy_tip_sections()):
        top_margin = 0 if section_index == 0 else 24
        content = [
            '<p style="margin:%dpx 0 12px 0; font-size:17px; '
            'font-weight:650; color:#f2f2f2;">%s</p>'
            % (top_margin, html.escape(heading))
        ]
        for number, tip in enumerate(tips, 1):
            content.append(
                '<p style="margin:0 0 13px 0; line-height:1.35; '
                'color:#d2d2d2;"><span style="font-weight:650; '
                'color:#ffffff;">%d.</span>&nbsp;&nbsp;%s</p>'
                % (number, html.escape(tip))
            )
        sections.append("".join(content))
    return '<div style="font-family:\'Segoe UI\'; font-size:13px;">' + "".join(
        sections
    ) + "</div>"


GEO_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "found",
        "location",
        "country",
        "region",
        "city",
        "latitude",
        "longitude",
        "confidence_km",
        "confidence_percent",
        "evidence",
        "alternatives",
        "error",
    ],
    "properties": {
        "found": {"type": "boolean"},
        "location": {"type": "string"},
        "country": {"type": "string"},
        "region": {"type": "string"},
        "city": {"type": "string"},
        "latitude": {"type": "number"},
        "longitude": {"type": "number"},
        "confidence_km": {"type": "number"},
        "confidence_percent": {"type": "number"},
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
        "alternatives": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["location", "latitude", "longitude", "reason"],
                "properties": {
                    "location": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "reason": {"type": "string"},
                },
            },
        },
        "error": {"type": "string"},
    },
}


class AnalysisCancelled(Exception):
    pass


class AnalysisError(Exception):
    pass


@dataclass
class GeoResult:
    location: str
    country: str
    region: str
    city: str
    latitude: float
    longitude: float
    confidence_km: float
    confidence_percent: float
    evidence: list[str]
    alternatives: list[dict]


@dataclass
class AnalysisStats:
    requested: int
    attempted: int = 0
    completed: int = 0
    usable: int = 0


NON_RETRYABLE_PROVIDER_CATEGORIES = frozenset(
    {
        "access",
        "auth",
        "billing",
        "image_format",
        "image_size",
        "model",
        "privacy",
        "provider",
        "request",
        "request_configuration",
        "refusal",
    }
)


def check_cancel(cancel_event: Optional[threading.Event]):
    if cancel_event is not None and cancel_event.is_set():
        raise AnalysisCancelled("Analysis cancelled.")


@dataclass
class ProviderPassOutcome:
    index: int
    prompt: str
    attempted: bool = False
    completed: bool = False
    payload: object = None
    error: Optional[Exception] = None
    elapsed_seconds: float = 0.0


class CombinedCancelEvent:

    def __init__(self, *events):
        self.events = tuple(event for event in events if event is not None)

    def is_set(self) -> bool:
        return any(event.is_set() for event in self.events)


def analysis_duration_text(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 0.1:
        return "under 0.1 seconds"
    if seconds < 10.0:
        return f"{seconds:.1f} seconds"
    if seconds < 120.0:
        return f"{seconds:.0f} seconds"
    return f"{seconds / 60.0:.1f} minutes"


def execute_provider_pass(
    outcome: ProviderPassOutcome,
    prepared_image,
    media_type: str,
    api_key: str,
    model,
    effort_label: str,
    cancel_event,
    cache_repeated_input: bool,
    clock,
    stop_event: Optional[threading.Event] = None,
):

    if cancel_event is not None and cancel_event.is_set():
        outcome.error = AnalysisCancelled("Analysis cancelled.")
        return
    outcome.attempted = True
    started = clock()
    try:
        outcome.payload = call_vision_model(
            model,
            api_key,
            prepared_image,
            media_type,
            outcome.prompt,
            GEO_SCHEMA,
            effort_label,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            cancel_event=cancel_event,
            cache_repeated_input=cache_repeated_input,
        )
        outcome.completed = True
    except Exception as error:
        outcome.error = error
        if stop_event is not None and (
            not isinstance(error, ProviderRequestError)
            or error.category in NON_RETRYABLE_PROVIDER_CATEGORIES
        ):
            stop_event.set()
    finally:
        outcome.elapsed_seconds = max(0.0, clock() - started)


def _short_text(value, maximum: int) -> str:
    raw = str(value or "").replace("\u2013", "-").replace("\u2014", "-")
    clean = " ".join(raw.split())
    if len(clean) <= maximum:
        return clean
    return clean[: maximum - 1].rstrip() + "…"


def result_from_payload(payload: dict) -> GeoResult:
    if not isinstance(payload, dict):
        raise AnalysisError("The selected model returned an unexpected response.")
    found = payload.get("found", False)
    if isinstance(found, str):
        found = found.strip().casefold() == "true"
    if not bool(found):
        reason = _short_text(payload.get("error"), 300)
        raise AnalysisError(reason or "No usable location could be identified.")

    try:
        latitude = float(payload.get("latitude"))
        longitude = float(payload.get("longitude"))
        confidence_km = float(payload.get("confidence_km", 500))
        confidence_percent = float(payload.get("confidence_percent", 50))
    except (TypeError, ValueError) as error:
        raise AnalysisError("The model returned coordinates that could not be read.") from error
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise AnalysisError("The model returned non-finite coordinates.")
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise AnalysisError("The model returned coordinates outside the valid range.")
    if not math.isfinite(confidence_km) or not math.isfinite(confidence_percent):
        raise AnalysisError("The model returned an invalid confidence value.")

    country = _short_text(payload.get("country"), 120)
    region = _short_text(payload.get("region"), 120)
    city = _short_text(payload.get("city"), 120)
    location = _short_text(payload.get("location"), 180)
    if not location:
        location = ", ".join(part for part in (city, region, country) if part)
    if not location:
        location = "Unnamed location"

    raw_evidence = payload.get("evidence", [])
    evidence = []
    if isinstance(raw_evidence, list):
        for item in raw_evidence[:8]:
            text = _short_text(item, 300)
            if text and text not in evidence:
                evidence.append(text)

    alternatives = []
    raw_alternatives = payload.get("alternatives", [])
    if isinstance(raw_alternatives, list):
        for item in raw_alternatives[:3]:
            if not isinstance(item, dict):
                continue
            try:
                alt_latitude = float(item.get("latitude"))
                alt_longitude = float(item.get("longitude"))
            except (TypeError, ValueError):
                continue
            if not (
                math.isfinite(alt_latitude)
                and math.isfinite(alt_longitude)
                and -90 <= alt_latitude <= 90
                and -180 <= alt_longitude <= 180
            ):
                continue
            alt_location = _short_text(item.get("location"), 180)
            if not alt_location:
                continue
            alternatives.append(
                {
                    "location": alt_location,
                    "latitude": alt_latitude,
                    "longitude": alt_longitude,
                    "reason": _short_text(item.get("reason"), 260),
                }
            )

    return GeoResult(
        location=location,
        country=country,
        region=region,
        city=city,
        latitude=latitude,
        longitude=longitude,
        confidence_km=max(0.5, min(20_000.0, confidence_km)),
        confidence_percent=max(1.0, min(99.0, confidence_percent)),
        evidence=evidence,
        alternatives=alternatives,
    )


def result_payload(result: GeoResult) -> dict:
    return {
        "found": True,
        "location": result.location,
        "country": result.country,
        "region": result.region,
        "city": result.city,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "confidence_km": result.confidence_km,
        "confidence_percent": result.confidence_percent,
        "evidence": result.evidence,
        "alternatives": result.alternatives,
        "error": "",
    }


def build_analysis_prompt(
    model,
    prompt_mode: str,
    effort_label: str,
    pass_index: int,
    total_passes: int,
    previous_results: list[dict],
    extra_guidance: str,
) -> str:
    return build_model_prompt(
        model,
        prompt_mode,
        pass_index,
        previous_results,
        extra_guidance,
        effort=effort_label,
        total_passes=total_passes,
    )


def analyse_image(
    image_data: bytes,
    media_type: str,
    api_key: str,
    model,
    effort_label: str,
    passes: int,
    prompt_mode: str,
    extra_guidance: str,
    cancel_event: Optional[threading.Event] = None,
    log_callback=None,
    progress_callback=None,
    stats: Optional[AnalysisStats] = None,
    clock_callback=None,
):
    if passes not in (1, 2, 3):
        raise AnalysisError("Choose one, two, or three analysis passes.")
    if stats is None:
        stats = AnalysisStats(passes)
    elif stats.requested != passes:
        raise AnalysisError("The analysis pass counter does not match the request.")

    def log(message: str):
        if log_callback is not None:
            log_callback(message)

    def progress(value: int):
        if progress_callback is not None:
            progress_callback(value)

    clock = clock_callback or time.perf_counter
    analysis_started = clock()
    previous_payloads = []
    last_result = None

    def analysis_note() -> str:
        if stats.usable == passes:
            return (
                "Completed one evidence check (one API call attempted and one usable result)."
                if passes == 1
                else (
                    f"Completed all {passes} evidence and review checks "
                    f"({stats.attempted} API calls attempted and "
                    f"{stats.usable} usable results)."
                )
            )
        return (
            f"Finished {stats.attempted} of {passes} requested checks: "
            f"{stats.completed} API calls completed and {stats.usable} produced "
            "a usable location. Kept the newest usable answer."
        )

    def record_call(outcome: ProviderPassOutcome):
        if not outcome.attempted:
            return
        stats.attempted += 1
        if outcome.completed:
            stats.completed += 1
            log(
                f"Pass {outcome.index} API call completed in "
                f"{analysis_duration_text(outcome.elapsed_seconds)}."
            )
        else:
            log(
                f"Pass {outcome.index} API call stopped after "
                f"{analysis_duration_text(outcome.elapsed_seconds)}."
            )

    def accept_payload(outcome: ProviderPassOutcome):
        nonlocal last_result
        try:
            result = result_from_payload(outcome.payload)
        except AnalysisError as error:
            if isinstance(outcome.payload, dict):
                previous_payloads.append(outcome.payload)
            return error
        last_result = result
        stats.usable += 1
        previous_payloads.append(result_payload(result))
        log(
            f"Pass {outcome.index}: {result.location} "
            f"({result.confidence_percent:.0f}% confidence)."
        )
        return None

    def provider_failure(outcome: ProviderPassOutcome, has_future: bool) -> bool:

        error = outcome.error
        if isinstance(error, AnalysisCancelled):
            raise error
        if not isinstance(error, ProviderRequestError):
            if error is not None:
                raise error
            raise AnalysisError("The provider call stopped without a result.")
        if error.category == "cancelled" or (
            cancel_event is not None and cancel_event.is_set()
        ):
            raise AnalysisCancelled("Analysis cancelled.") from error
        retryable = error.category not in NON_RETRYABLE_PROVIDER_CATEGORIES
        if last_result is not None and not retryable:
            log(
                f"Pass {outcome.index} could not finish ({str(error)}). "
                "Keeping the last usable estimate."
            )
            return True
        if retryable and has_future:
            log(
                f"Pass {outcome.index} could not finish ({str(error)}). "
                f"Continuing with pass {outcome.index + 1}."
            )
            return False
        if last_result is not None:
            log(
                f"Pass {outcome.index} could not finish ({str(error)}). "
                "Keeping the last usable estimate."
            )
            return True
        raise AnalysisError(str(error)) from error

    try:
        try:
            prepared_image = prepare_vision_image(image_data, media_type)
        except ProviderRequestError as error:
            raise AnalysisError(str(error)) from error
        except (TypeError, ValueError) as error:
            raise AnalysisError("The prepared image could not be reused.") from error

        if passes in (1, 2):
            for index in range(1, passes + 1):
                check_cancel(cancel_event)
                if index == 1:
                    log(f"Pass {index} of {passes}: examining the image.")
                else:
                    log(
                        f"Pass {index} of {passes}: performing the final evidence audit."
                    )
                progress(8 + int((index - 1) / passes * 78))
                prompt = build_analysis_prompt(
                    model,
                    prompt_mode,
                    effort_label,
                    index,
                    passes,
                    previous_payloads,
                    extra_guidance,
                )
                outcome = ProviderPassOutcome(index, prompt)
                execute_provider_pass(
                    outcome,
                    prepared_image,
                    media_type,
                    api_key,
                    model,
                    effort_label,
                    cancel_event,
                    passes > 1,
                    clock,
                )
                record_call(outcome)
                check_cancel(cancel_event)
                if outcome.error is not None:
                    if provider_failure(outcome, index < passes):
                        break
                    progress(8 + int(index / passes * 78))
                    continue
                parse_error = accept_payload(outcome)
                if parse_error is not None:
                    if index < passes:
                        log(
                            f"Pass {index} did not produce a usable location "
                            f"({str(parse_error)}). Continuing with pass {index + 1}."
                        )
                        progress(8 + int(index / passes * 78))
                        continue
                    if last_result is not None:
                        log(
                            f"Pass {index} returned unusable location data. "
                            "Keeping the last usable estimate."
                        )
                        continue
                    raise parse_error
                progress(8 + int(index / passes * 78))
        else:
            check_cancel(cancel_event)
            log("Pass 1 of 3: examining the image independently.")
            log("Pass 2 of 3: forming an independent competing hypothesis.")
            progress(8)
            seed_outcomes = [
                ProviderPassOutcome(
                    index,
                    build_analysis_prompt(
                        model,
                        prompt_mode,
                        effort_label,
                        index,
                        3,
                        [],
                        extra_guidance,
                    ),
                )
                for index in (1, 2)
            ]
            internal_stop = threading.Event()
            shared_cancel = CombinedCancelEvent(cancel_event, internal_stop)
            seed_threads = [
                threading.Thread(
                    target=execute_provider_pass,
                    args=(
                        outcome,
                        prepared_image,
                        media_type,
                        api_key,
                        model,
                        effort_label,
                        shared_cancel,
                        True,
                        clock,
                        internal_stop,
                    ),
                    name=f"AILocationSeed{outcome.index}",
                    daemon=True,
                )
                for outcome in seed_outcomes
            ]
            started_threads = []
            try:
                for seed_thread in seed_threads:
                    seed_thread.start()
                    started_threads.append(seed_thread)
            except Exception as error:
                internal_stop.set()
                for seed_thread in started_threads:
                    seed_thread.join()
                raise AnalysisError(
                    "The independent evidence checks could not start."
                ) from error
            for seed_thread in started_threads:
                seed_thread.join()
            if any(seed_thread.is_alive() for seed_thread in started_threads):
                raise AnalysisError("An independent evidence check did not stop.")

            for outcome in seed_outcomes:
                record_call(outcome)
            progress(60)
            check_cancel(cancel_event)

            parse_errors = {}
            for outcome in seed_outcomes:
                if outcome.completed:
                    parse_error = accept_payload(outcome)
                    if parse_error is not None:
                        parse_errors[outcome.index] = parse_error

            unexpected_errors = [
                outcome.error
                for outcome in seed_outcomes
                if outcome.error is not None
                and not isinstance(
                    outcome.error,
                    (AnalysisCancelled, ProviderRequestError),
                )
            ]
            if unexpected_errors:
                raise unexpected_errors[0]

            nonretryable = [
                outcome
                for outcome in seed_outcomes
                if isinstance(outcome.error, ProviderRequestError)
                and outcome.error.category in NON_RETRYABLE_PROVIDER_CATEGORIES
            ]
            if nonretryable:
                for outcome in nonretryable:
                    log(
                        f"Pass {outcome.index} could not finish "
                        f"({str(outcome.error)})."
                    )
                if last_result is None:
                    raise AnalysisError(str(nonretryable[0].error)) from nonretryable[0].error
                log("Skipped the final adjudication and kept the usable seed result.")
                return last_result, analysis_note(), stats

            for outcome in seed_outcomes:
                error = outcome.error
                if isinstance(error, AnalysisCancelled):
                    if internal_stop.is_set():
                        continue
                    raise error
                if isinstance(error, ProviderRequestError):
                    if error.category == "cancelled" and internal_stop.is_set():
                        continue
                    log(
                        f"Pass {outcome.index} could not finish ({str(error)}). "
                        "Continuing with pass 3."
                    )
            for index, parse_error in parse_errors.items():
                log(
                    f"Pass {index} did not produce a usable location "
                    f"({str(parse_error)}). Continuing with pass 3."
                )

            check_cancel(cancel_event)
            log("Pass 3 of 3: performing the final evidence adjudication.")
            final_prompt = build_analysis_prompt(
                model,
                prompt_mode,
                effort_label,
                3,
                3,
                previous_payloads,
                extra_guidance,
            )
            final_outcome = ProviderPassOutcome(3, final_prompt)
            execute_provider_pass(
                final_outcome,
                prepared_image,
                media_type,
                api_key,
                model,
                effort_label,
                cancel_event,
                True,
                clock,
            )
            record_call(final_outcome)
            check_cancel(cancel_event)
            if final_outcome.error is not None:
                provider_failure(final_outcome, False)
            else:
                parse_error = accept_payload(final_outcome)
                if parse_error is not None:
                    if last_result is not None:
                        log(
                            "Pass 3 returned unusable location data. "
                            "Keeping the last usable estimate."
                        )
                    else:
                        raise parse_error
            progress(86)

        if last_result is None:
            raise AnalysisError("No analysis pass returned a usable location.")
        return last_result, analysis_note(), stats
    finally:
        if stats.attempted:
            log(
                "Total analysis time: "
                f"{analysis_duration_text(clock() - analysis_started)}."
            )


def format_coordinate(value: float, is_latitude: bool) -> str:
    if is_latitude:
        direction = "N" if value >= 0 else "S"
    else:
        direction = "E" if value >= 0 else "W"
    return f"{abs(value):.5f}° {direction}"


def _safe_report_source(source_name: str) -> str:
    raw_source = str(source_name or "").strip()
    if not raw_source:
        return "Unknown image"
    try:
        source_path = Path(raw_source)
        if source_path.is_absolute():
            raw_source = source_path.name or "Image file"
    except (OSError, TypeError, ValueError):
        raw_source = "Image file"
    return _short_text(raw_source, 260)


def report_text(
    result: GeoResult,
    source_name: str,
    prompt_mode: str,
    model,
    effort_label: str,
    requested_passes: int,
    completed_passes: int,
    attempted_passes: Optional[int] = None,
    usable_passes: Optional[int] = None,
) -> str:
    provider = provider_by_id(model.provider_id)
    attempted_passes = completed_passes if attempted_passes is None else attempted_passes
    usable_passes = completed_passes if usable_passes is None else usable_passes
    lines = [
        f"{APP_NAME} result",
        "",
        f"Location:     {result.location}",
        f"Latitude:     {format_coordinate(result.latitude, True)}",
        f"Longitude:    {format_coordinate(result.longitude, False)}",
        f"Confidence:   {result.confidence_percent:.0f}%",
        f"Likely radius: about {result.confidence_km:,.0f} km",
        "",
        f"Coordinates:  {result.latitude:.6f}, {result.longitude:.6f}",
        "",
        "Evidence:",
    ]
    lines.extend(
        [f"- {item}" for item in result.evidence]
        or ["- The model did not provide a separate evidence list."]
    )
    if result.alternatives:
        lines.extend(["", "Alternatives:"])
        for alternative in result.alternatives:
            reason = alternative.get("reason") or "No separate reason supplied."
            lines.append(f"- {alternative['location']}: {reason}")
    lines.extend(
        [
            "",
            f"Source:       {_safe_report_source(source_name)}",
            f"Prompt mode:  {prompt_mode}",
            f"AI service:   {provider.display_name}",
            f"Model:        {model.display_name}",
            f"Model ID:     {model.id}",
            f"Prompt tuning: {prompt_profile_identifier(model)}",
            f"Effort:       {effort_label} (native setting: {native_effort(model, effort_label)})",
            (
                "Checks:       "
                f"{attempted_passes} attempted / {completed_passes} completed / "
                f"{usable_passes} usable / {requested_passes} requested"
            ),
            f"Created:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This is an estimate produced by an AI model. Treat it as a lead,",
            "not as a confirmed location. Do not use it to stalk, harass, dox,",
            "trespass, or endanger anyone.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    output: Path,
    result: GeoResult,
    source_name: str,
    prompt_mode: str,
    model,
    effort_label: str,
    requested_passes: int,
    completed_passes: int,
    attempted_passes: Optional[int] = None,
    usable_passes: Optional[int] = None,
) -> Path:
    try:
        output = output.expanduser().resolve()
    except (OSError, TypeError, ValueError) as error:
        raise AnalysisError("The result report path is not usable.") from error
    temporary_path = None
    descriptor = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        report = report_text(
            result,
            source_name,
            prompt_mode,
            model,
            effort_label,
            requested_passes,
            completed_passes,
            attempted_passes,
            usable_passes,
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=str(output.parent),
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = None
            handle.write(report)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output)
        temporary_path = None
    except (OSError, TypeError, ValueError) as error:
        raise AnalysisError("The result report could not be saved.") from error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    try:
        report_is_valid = output.is_file() and output.stat().st_size > 0
    except OSError as error:
        raise AnalysisError("The result report could not be verified.") from error
    if not report_is_valid:
        raise AnalysisError("The result report could not be saved.")
    return output


def validated_input_image_dimensions(width: int, height: int) -> tuple[int, int]:

    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width < 1
        or height < 1
        or width > MAX_INPUT_IMAGE_PIXELS // height
    ):
        raise AnalysisError(
            "The selected image has too many pixels to decode safely. "
            "Choose an image with at most 64 million pixels."
        )
    return width, height


def load_image_file(
    path: Path,
    *,
    max_long_edge: int = MAX_IMAGE_LONG_EDGE,
    max_visual_tokens: Optional[int] = None,
) -> QImage:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise AnalysisError("The selected image no longer exists.")
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise AnalysisError("Choose a PNG, JPG, WEBP, BMP, GIF, or TIFF image.")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise AnalysisError("The image is larger than the 20 MB limit.")
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    reader.setDecideFormatFromContent(True)
    if not reader.canRead():
        raise AnalysisError("The selected file is not a readable image.")
    source_size = reader.size()
    if not source_size.isValid():
        raise AnalysisError("The selected image dimensions could not be validated safely.")
    source_width, source_height = validated_input_image_dimensions(
        source_size.width(),
        source_size.height(),
    )
    scaled_width, scaled_height = scaled_upload_dimensions(
        source_width,
        source_height,
        max_long_edge=max_long_edge,
        max_visual_tokens=max_visual_tokens,
    )
    if (scaled_width, scaled_height) != (source_width, source_height):
        reader.setScaledSize(QSize(scaled_width, scaled_height))
    image = reader.read()
    if image.isNull():
        raise AnalysisError("The selected file is not a readable image.")
    return image


def source_file_is_available(path) -> bool:

    if path is None:
        return False
    try:
        return bool(path.is_file())
    except (OSError, TypeError, ValueError):
        return False


def image_visual_tokens(width: int, height: int) -> int:
    return math.ceil(width / IMAGE_PATCH_SIZE) * math.ceil(height / IMAGE_PATCH_SIZE)


def image_upload_profile(model, effort_label: str, passes: int):

    normalized_effort = str(effort_label or "").strip().title()
    if normalized_effort not in UPLOAD_QUALITY_BY_EFFORT:
        raise AnalysisError("Choose Low, Medium, High, or Ultra effort.")
    if passes not in (1, 2, 3):
        raise AnalysisError("Choose one, two, or three analysis passes.")
    quality = min(
        99,
        UPLOAD_QUALITY_BY_EFFORT[normalized_effort] + passes - 1,
    )
    is_haiku = (
        model.provider_id == "anthropic"
        and model.id == "claude-haiku-4-5-20251001"
    )
    return {
        "format": "JPEG" if model.provider_id == "xai" else "WEBP",
        "media_type": "image/jpeg" if model.provider_id == "xai" else "image/webp",
        "quality": quality,
        "max_long_edge": (
            HAIKU_MAX_IMAGE_LONG_EDGE
            if is_haiku
            else MAX_IMAGE_LONG_EDGE_BY_EFFORT[normalized_effort]
        ),
        "max_visual_tokens": (
            HAIKU_MAX_VISUAL_TOKENS if is_haiku else None
        ),
    }


def scaled_upload_dimensions(
    width: int,
    height: int,
    max_long_edge: int = MAX_IMAGE_LONG_EDGE,
    max_visual_tokens: Optional[int] = None,
) -> tuple[int, int]:

    if width < 1 or height < 1 or max_long_edge < 1:
        raise AnalysisError("The image dimensions are not usable.")
    long_edge = max(width, height)
    within_token_limit = (
        max_visual_tokens is None
        or image_visual_tokens(width, height) <= max_visual_tokens
    )
    if long_edge <= max_long_edge and within_token_limit:
        return width, height

    ratio = min(1.0, max_long_edge / long_edge)
    if max_visual_tokens is not None:
        approximate_tokens = max(1.0, (width * height) / (IMAGE_PATCH_SIZE**2))
        ratio = min(ratio, math.sqrt(max_visual_tokens / approximate_tokens))

    scaled_width = max(1, round(width * ratio))
    scaled_height = max(1, round(height * ratio))
    while (
        max(scaled_width, scaled_height) > max_long_edge
        or (
            max_visual_tokens is not None
            and image_visual_tokens(scaled_width, scaled_height) > max_visual_tokens
        )
    ):
        if scaled_width >= scaled_height:
            scaled_width -= 1
            scaled_height = max(1, round(scaled_width * height / width))
        else:
            scaled_height -= 1
            scaled_width = max(1, round(scaled_height * width / height))

    return scaled_width, scaled_height


def scale_for_upload(
    image: QImage,
    max_long_edge: int = MAX_IMAGE_LONG_EDGE,
    max_visual_tokens: Optional[int] = None,
) -> QImage:

    scaled_width, scaled_height = scaled_upload_dimensions(
        image.width(),
        image.height(),
        max_long_edge=max_long_edge,
        max_visual_tokens=max_visual_tokens,
    )
    if (scaled_width, scaled_height) == (image.width(), image.height()):
        return image
    return image.scaled(
        scaled_width,
        scaled_height,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


def encode_image(
    image: QImage,
    model=None,
    effort_label: str = "",
    passes: int = 0,
):
    profile = (
        image_upload_profile(model, effort_label, passes)
        if model is not None
        else None
    )
    scaled = scale_for_upload(
        image,
        max_long_edge=(
            profile["max_long_edge"] if profile is not None else MAX_IMAGE_LONG_EDGE
        ),
        max_visual_tokens=(
            profile["max_visual_tokens"] if profile is not None else None
        ),
    ).convertToFormat(QImage.Format_RGB32)

    prepared = QImage(scaled.size(), QImage.Format_RGB32)
    prepared.fill(QColor("#000000"))
    painter = QPainter(prepared)
    painter.setCompositionMode(QPainter.CompositionMode_Source)
    painter.drawImage(0, 0, scaled)
    painter.end()

    def encode(image_format: str, quality: int) -> bytes:
        payload = QByteArray()
        buffer = QBuffer(payload)
        buffer.open(QBuffer.WriteOnly)
        try:
            if not prepared.save(buffer, image_format, quality):
                raise AnalysisError(f"The image could not be encoded as {image_format}.")
        finally:
            buffer.close()
        return bytes(payload.data())

    if profile is not None:
        try:
            data = encode(profile["format"], profile["quality"])
            media_type = profile["media_type"]
        except AnalysisError:
            fallback_format = "PNG" if model.provider_id == "xai" else "JPEG"
            data = encode(fallback_format, -1 if fallback_format == "PNG" else 99)
            media_type = (
                "image/png" if fallback_format == "PNG" else "image/jpeg"
            )
    else:
        data = encode("PNG", -1)
        media_type = "image/png"
        if len(data) > PNG_SIZE_LIMIT:
            data = encode("JPEG", 92)
            media_type = "image/jpeg"
    return data, media_type, prepared.width(), prepared.height()


class TrafficLightButton(QPushButton):
    DOT_DIAMETER = 13.0
    HALO_DIAMETER = 20.0
    FOCUS_DIAMETER = 16.0
    COLORS = {
        "closeDot": "#ff5f57",
        "minimizeDot": "#febc2e",
        "maximizeDot": "#28c840",
    }

    def __init__(self, color_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setObjectName(color_name)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self._dot_color = QColor(self.COLORS[color_name])
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton#{color_name} {{ background: transparent; border: none; "
            "min-width: 28px; max-width: 28px; min-height: 28px; "
            "max-height: 28px; padding: 0; }"
        )

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0

        def centered_rect(diameter: float) -> QRectF:
            radius = diameter / 2.0
            return QRectF(
                center_x - radius,
                center_y - radius,
                diameter,
                diameter,
            )

        if self.underMouse() or self.hasFocus():
            halo = QColor(self._dot_color)
            halo.setAlpha(55 if self.underMouse() else 38)
            painter.setPen(Qt.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(centered_rect(self.HALO_DIAMETER))

        color = self._dot_color.darker(118) if self.isDown() else self._dot_color
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(centered_rect(self.DOT_DIAMETER))

        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 185), 1.0))
            painter.drawEllipse(centered_rect(self.FOCUS_DIAMETER))


class TitleBar(QFrame):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.drag_offset = QPoint()
        self.setObjectName("titleBar")
        self.setFixedHeight(42)

        self.bar_layout = QHBoxLayout(self)
        self.bar_layout.setContentsMargins(14, 0, 14, 0)
        self.bar_layout.setSpacing(8)

        close_button = TrafficLightButton("closeDot", "Close", self)
        minimize_button = TrafficLightButton("minimizeDot", "Minimize", self)
        maximize_button = TrafficLightButton("maximizeDot", "Maximize or restore", self)
        close_button.clicked.connect(host.close)
        minimize_button.clicked.connect(host.showMinimized)
        maximize_button.clicked.connect(self.toggle_maximized)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(0)
        controls.addWidget(maximize_button)
        controls.addWidget(minimize_button)
        controls.addWidget(close_button)
        self.controls_holder = QWidget()
        self.controls_holder.setFixedWidth(84)
        self.controls_holder.setLayout(controls)

        self.left_spacer = QWidget()
        self.title = QLabel(APP_NAME)
        self.title.setObjectName("windowTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.bar_layout.addWidget(self.left_spacer)
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.title)
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.controls_holder)
        self.set_compact(host.width() < 360)

    def set_compact(self, compact: bool):
        compact = bool(compact)
        self.left_spacer.setFixedWidth(0 if compact else 84)
        self.title.setVisible(not compact)
        self.bar_layout.setContentsMargins(8 if compact else 14, 0, 8 if compact else 14, 0)

    def toggle_maximized(self):
        if self.host.isMaximized():
            self.host.showNormal()
        else:
            self.host.showMaximized()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_maximized()
            event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_offset = (
                event.globalPosition().toPoint()
                - self.host.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and not self.host.isMaximized():
            self.host.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()


class ChevronButton(QPushButton):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.white, 1.4))
        x = self.width() - 18
        y = self.height() // 2 - 1
        painter.drawLine(x - 4, y - 2, x, y + 2)
        painter.drawLine(x, y + 2, x + 4, y - 2)


class ElidedPathLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__("", parent)
        self._full_text = ""
        self._full_tooltip = ""
        self.set_full_text(text)

    def set_full_text(self, value, tooltip=None):
        full_text = str(value or "")
        full_tooltip = full_text if tooltip is None else str(tooltip or "")
        if full_text == self._full_text and full_tooltip == self._full_tooltip:
            return
        self._full_text = full_text
        self._full_tooltip = full_tooltip
        self.setAccessibleName(self._full_text)
        self.setAccessibleDescription(
            self._full_tooltip if self._full_tooltip != self._full_text else ""
        )
        self.setToolTip(self._full_tooltip)
        self._refresh_elision()

    def full_text(self):
        return self._full_text

    def _refresh_elision(self):
        available = max(1, self.contentsRect().width() - 14)
        shown = self.fontMetrics().elidedText(
            self._full_text,
            Qt.ElideMiddle,
            available,
        )
        if shown != self.text():
            super().setText(shown)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_elision()


class EqualWidthTabBar(QTabBar):

    def tabSizeHint(self, index):
        hint = super().tabSizeHint(index)
        if self.count() > 0:
            hint.setWidth(
                max(
                    QTabBar.tabSizeHint(self, tab_index).width()
                    for tab_index in range(self.count())
                )
            )
        return QSize(hint.width(), hint.height())

    def minimumTabSizeHint(self, index):
        hint = super().minimumTabSizeHint(index)
        hint.setWidth(1)
        return hint


class ViewportPage(QWidget):

    def sizeHint(self):
        hint = self.minimumSize().expandedTo(QSize(1, 1))
        viewport = self.parentWidget()
        if viewport is not None:
            hint = hint.expandedTo(viewport.size())
        return hint


def ui_animations_enabled() -> bool:

    application = QApplication.instance()
    if application is not None and bool(application.property("reduceMotion")):
        return False
    if os.name == "nt":
        animations_enabled = wintypes.BOOL()
        try:
            succeeded = ctypes.windll.user32.SystemParametersInfoW(
                0x1042,
                0,
                ctypes.byref(animations_enabled),
                0,
            )
            if succeeded:
                return bool(animations_enabled.value)
        except (AttributeError, OSError):
            pass
    return True


class RoundedScrollBar(QScrollBar):

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._hovered = False
        self.setMouseTracking(True)

    def paintEvent(self, event):
        del event
        if self.maximum() <= self.minimum():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(
            QColor("#686868")
            if self.isSliderDown()
            else QColor("#505050" if self._hovered else "#3b3b3b")
        )

        vertical = self.orientation() == Qt.Vertical
        track = (
            self.rect().adjusted(1, 6, -1, -6)
            if vertical
            else self.rect().adjusted(6, 1, -6, -1)
        )
        track_length = track.height() if vertical else track.width()
        total = self.maximum() - self.minimum() + max(1, self.pageStep())
        handle_length = max(
            28,
            round(track_length * max(1, self.pageStep()) / max(1, total)),
        )
        handle_length = min(track_length, handle_length)
        travel = max(0, track_length - handle_length)
        ratio = (self.value() - self.minimum()) / max(
            1,
            self.maximum() - self.minimum(),
        )
        offset = round(travel * ratio)
        handle = (
            QRect(track.left(), track.top() + offset, track.width(), handle_length)
            if vertical
            else QRect(track.left() + offset, track.top(), handle_length, track.height())
        )
        radius = min(handle.width(), handle.height()) / 2.0
        painter.drawRoundedRect(handle, radius, radius)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.update()


class SmoothScrollController(QObject):

    DURATION_MS = 145

    def __init__(self, scroll_area):
        super().__init__(scroll_area)
        self.scroll_area = scroll_area
        self._animations = {}
        self._animation_cache = {}
        self._targets = {}
        scroll_area.installEventFilter(self)
        scroll_area.viewport().installEventFilter(self)
        for scrollbar in (
            scroll_area.verticalScrollBar(),
            scroll_area.horizontalScrollBar(),
        ):
            scrollbar.installEventFilter(self)

    def _stop(self, scrollbar):
        animation = self._animations.pop(scrollbar, None)
        self._targets.pop(scrollbar, None)
        if animation is not None:
            animation.stop()

    def _animate_to(self, scrollbar, target):
        target = max(scrollbar.minimum(), min(scrollbar.maximum(), int(target)))
        if target == scrollbar.value():
            self._stop(scrollbar)
            return False
        self._stop(scrollbar)
        if not ui_animations_enabled():
            scrollbar.setValue(target)
            return True
        animation = self._animation_cache.get(scrollbar)
        if animation is None:
            animation = QPropertyAnimation(scrollbar, b"value", self)
            animation.finished.connect(
                lambda current=animation, bar=scrollbar: self._finished(bar, current)
            )
            self._animation_cache[scrollbar] = animation
        else:
            animation.stop()
        animation.setDuration(self.DURATION_MS)
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animations[scrollbar] = animation
        self._targets[scrollbar] = target
        animation.start()
        return True

    def _finished(self, scrollbar, animation):
        if self._animations.get(scrollbar) is animation:
            self._animations.pop(scrollbar, None)
            self._targets.pop(scrollbar, None)

    def scroll_by(self, scrollbar, distance):
        current_target = self._targets.get(scrollbar, scrollbar.value())
        return self._animate_to(scrollbar, current_target + int(distance))

    def _handle_wheel(self, event):
        if event.modifiers() & Qt.ControlModifier:
            return False
        pixel = event.pixelDelta()
        angle = event.angleDelta()
        horizontal = bool(event.modifiers() & Qt.ShiftModifier)
        if not horizontal and pixel.x() and not pixel.y():
            horizontal = True
        if not horizontal and angle.x() and not angle.y():
            horizontal = True
        scrollbar = (
            self.scroll_area.horizontalScrollBar()
            if horizontal
            else self.scroll_area.verticalScrollBar()
        )
        delta = pixel.x() if horizontal else pixel.y()
        if not delta:
            delta = angle.x() if horizontal else angle.y()
            if delta:
                distance = -round(delta / 120.0 * max(42, scrollbar.singleStep() * 3))
            else:
                return False
        else:
            distance = -delta
        return self.scroll_by(scrollbar, distance)

    def _handle_key(self, event):
        if event.modifiers() not in (Qt.NoModifier, Qt.KeypadModifier):
            return False
        vertical = self.scroll_area.verticalScrollBar()
        key = event.key()
        if key == Qt.Key_PageUp:
            return self.scroll_by(vertical, -max(1, vertical.pageStep() - 24))
        if key == Qt.Key_PageDown:
            return self.scroll_by(vertical, max(1, vertical.pageStep() - 24))
        if isinstance(self.scroll_area, QTextEdit):
            return False
        if key == Qt.Key_Up:
            return self.scroll_by(vertical, -max(18, vertical.singleStep()))
        if key == Qt.Key_Down:
            return self.scroll_by(vertical, max(18, vertical.singleStep()))
        if key == Qt.Key_Home:
            return self._animate_to(vertical, vertical.minimum())
        if key == Qt.Key_End:
            return self._animate_to(vertical, vertical.maximum())
        return False

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and watched in (
            self.scroll_area.verticalScrollBar(),
            self.scroll_area.horizontalScrollBar(),
        ):
            self._stop(watched)
        elif event.type() == QEvent.Wheel and watched is self.scroll_area.viewport():
            if self._handle_wheel(event):
                event.accept()
                return True
        elif event.type() == QEvent.KeyPress and watched in (
            self.scroll_area,
            self.scroll_area.viewport(),
        ):
            if self._handle_key(event):
                event.accept()
                return True
        return super().eventFilter(watched, event)


class ReachableScrollArea(QScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBar(RoundedScrollBar(Qt.Vertical, self))
        self.setHorizontalScrollBar(RoundedScrollBar(Qt.Horizontal, self))
        self._smooth_scroll = SmoothScrollController(self)

    def ensureWidgetVisible(self, child_widget, xmargin=50, ymargin=50):
        super().ensureWidgetVisible(child_widget, xmargin, ymargin)
        content = self.widget()
        if child_widget is None or content is None:
            return
        try:
            center = child_widget.mapTo(content, child_widget.rect().center())
        except RuntimeError:
            return

        viewport_size = self.viewport().size()
        horizontal = self.horizontalScrollBar()
        vertical = self.verticalScrollBar()
        visible = QRect(
            horizontal.value(),
            vertical.value(),
            viewport_size.width(),
            viewport_size.height(),
        )
        if visible.contains(center):
            return

        if self.horizontalScrollBarPolicy() != Qt.ScrollBarAlwaysOff:
            horizontal.setValue(center.x() - viewport_size.width() // 2)
        vertical.setValue(center.y() - viewport_size.height() // 2)


class SmoothTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBar(RoundedScrollBar(Qt.Vertical, self))
        self.setHorizontalScrollBar(RoundedScrollBar(Qt.Horizontal, self))
        self._smooth_scroll = SmoothScrollController(self)


class AppDialog(QDialog):

    def __init__(self, title: str, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("appDialog")
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._action_layouts = []

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setSizeConstraint(QLayout.SetNoConstraint)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)
        self.surface = QFrame(self)
        self.surface.setObjectName("dialogSurface")
        self.outer_layout.addWidget(self.surface)
        self.content_layout = QVBoxLayout(self.surface)
        self.content_layout.setSizeConstraint(QLayout.SetNoConstraint)
        self.content_layout.setContentsMargins(20, 18, 20, 18)
        self.content_layout.setSpacing(13)

    def register_action_layout(self, layout):
        self._action_layouts.append(layout)

    def showEvent(self, event):
        parent = self.parentWidget()
        screen = QApplication.screenAt(
            parent.frameGeometry().center() if parent is not None else QPoint()
        )
        if screen is None and parent is not None:
            screen = parent.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else QRect()
        requested = self.size()
        if available.isValid():
            compact = (
                available.width() < 520 or available.height() < 420
            )
            margins = (10, 10, 10, 10) if compact else (20, 18, 20, 18)
            self.content_layout.setContentsMargins(*margins)
            self.content_layout.setSpacing(9 if compact else 13)
            stack_actions = available.width() < 300
            for action_layout in self._action_layouts:
                action_layout.setDirection(
                    QBoxLayout.TopToBottom
                    if stack_actions
                    else QBoxLayout.LeftToRight
                )
                action_layout.invalidate()

            self.content_layout.invalidate()
            self.content_layout.activate()

            maximum_width = max(1, available.width() - 8)
            maximum_height = max(1, available.height() - 8)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(maximum_width, maximum_height)
            self.resize(
                min(maximum_width, max(1, requested.width())),
                min(maximum_height, max(1, requested.height())),
            )

        super().showEvent(event)
        if available.isValid():
            self.resize(
                min(self.width(), max(1, available.width() - 8)),
                min(self.height(), max(1, available.height() - 8)),
            )
        if parent is not None:
            target_center = parent.frameGeometry().center()
        elif available.isValid():
            target_center = available.center()
        else:
            return
        x = target_center.x() - self.width() // 2
        y = target_center.y() - self.height() // 2
        if available.isValid():
            x = max(available.left(), min(x, available.right() - self.width() + 1))
            y = max(available.top(), min(y, available.bottom() - self.height() + 1))
        self.move(x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)


class AnimatedDropdown(QWidget):
    changed = Signal(str)

    OPTION_HEIGHT = 32
    OPTION_SPACING = 2
    SURFACE_INSET = 6
    SURFACE_BORDER = 1
    POPUP_HEIGHT_SAFETY = 4
    MAX_POPUP_HEIGHT = 520

    def __init__(self, items, current_index=0, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.items = []
        self._current = ""
        self._animation = None
        self._closing = False
        self._restore_button_focus = False
        self._popup_filter_hosts = ()
        self._popup_application_filter = False
        self.option_buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.button = ChevronButton()
        self.button.setObjectName("dropdownButton")
        self.button.setMinimumHeight(38)
        self.button.setFocusPolicy(Qt.StrongFocus)
        self.button.setAccessibleName("Choose an option")
        self.button.clicked.connect(self.toggle_popup)
        self.button.installEventFilter(self)
        layout.addWidget(self.button)

        self.popup = QFrame(
            self,
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint,
        )
        self.popup.setObjectName("dropdownPopup")
        self.popup.setAttribute(Qt.WA_TranslucentBackground)
        self.popup.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self.popup)
        outer.setContentsMargins(0, 0, 0, 0)
        self.popup_surface = QFrame()
        self.popup_surface.setObjectName("dropdownSurface")
        self.popup_surface.setAttribute(Qt.WA_StyledBackground, True)
        popup_surface_layout = QVBoxLayout(self.popup_surface)
        popup_surface_layout.setContentsMargins(
            self.SURFACE_INSET,
            self.SURFACE_INSET,
            self.SURFACE_INSET,
            self.SURFACE_INSET,
        )
        popup_surface_layout.setSpacing(0)
        self.surface = QWidget()
        self.surface.setObjectName("dropdownOptions")
        self.surface.setAttribute(Qt.WA_StyledBackground, True)
        self.surface_layout = QVBoxLayout(self.surface)
        self.surface_layout.setContentsMargins(0, 0, 0, 0)
        self.surface_layout.setSpacing(self.OPTION_SPACING)
        self.surface.setStyleSheet(
            "QWidget#dropdownOptions { background: transparent; border: none; }"
            "QPushButton#dropdownOption[selected=\"true\"] { "
            "background: #2a2a2a; border: 1px solid #555555; color: #ffffff; }"
            "QPushButton#dropdownOption:focus { "
            "background: #242424; border: 1px solid #858585; color: #ffffff; }"
            "QPushButton#dropdownOption[selected=\"true\"]:focus { "
            "background: #303030; border-color: #ffffff; }"
        )
        self.scroll_area = ReachableScrollArea()
        self.scroll_area.setObjectName("dropdownScroll")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setAttribute(Qt.WA_TranslucentBackground)
        self.scroll_area.verticalScrollBar().setObjectName("dropdownScrollBar")
        self.scroll_area.setWidget(self.surface)
        popup_surface_layout.addWidget(self.scroll_area)
        outer.addWidget(self.popup_surface)
        self.set_items(items, current_index)

    def currentText(self):
        return self._current

    def set_items(self, items, current_index=0):
        self.hide_popup(immediate=True)
        while self.surface_layout.count():
            item = self.surface_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.option_buttons = []
        self.items = list(items) or ["Unavailable"]
        current_index = max(0, min(int(current_index), len(self.items) - 1))
        self._current = self.items[current_index]
        self.button.setText(self._current)
        for value in self.items:
            option = QPushButton(value)
            option.setObjectName("dropdownOption")
            option.setFixedHeight(self.OPTION_HEIGHT)
            option.setCheckable(True)
            option.setAutoExclusive(True)
            option.setFocusPolicy(Qt.StrongFocus)
            option.setAccessibleName(value)
            option.clicked.connect(
                lambda checked=False, selected=value: self.select(selected)
            )
            self.surface_layout.addWidget(option)
            self.option_buttons.append(option)
        content_height = (
            len(self.items) * self.OPTION_HEIGHT
            + max(0, len(self.items) - 1) * self.OPTION_SPACING
        )
        self.surface.setMinimumHeight(content_height)
        self._sync_option_states()

    def select(self, value, emit=True):
        if value not in self.items:
            return False
        previous = self._current
        changed = value != self._current
        self._current = value
        self.button.setText(value)
        if changed:
            self._sync_option_states({previous, value})
        self.hide_popup(restore_focus=True)
        if changed and emit:
            self.changed.emit(value)
        return changed

    def _current_index(self):
        try:
            return self.items.index(self._current)
        except ValueError:
            return 0

    def _focused_index(self):
        focused = QApplication.focusWidget()
        for index, option in enumerate(self.option_buttons):
            if option is focused:
                return index
        return self._current_index()

    def _focus_option(self, index):
        if not self.option_buttons:
            return
        index = max(0, min(int(index), len(self.option_buttons) - 1))
        option = self.option_buttons[index]
        option.setFocus(Qt.PopupFocusReason)
        self.scroll_area.ensureWidgetVisible(option, 8, 8)

    def _sync_option_states(self, values=None):
        for value, option in zip(self.items, self.option_buttons):
            if values is not None and value not in values:
                continue
            selected = value == self._current
            option.setChecked(selected)
            option.setProperty("selected", selected)
            option.setAccessibleDescription(
                "Currently selected" if selected else ""
            )
            option.style().unpolish(option)
            option.style().polish(option)
            option.update()

    def toggle_popup(self):
        if not self.isEnabled():
            return
        if self.popup.isVisible() and not self._closing:
            self.hide_popup()
        else:
            self.show_popup()

    def show_popup(self):
        if not self.isEnabled() or not self.isVisible():
            return
        self._stop_animation()
        self._closing = False
        self._restore_button_focus = False
        calculated_height = (
            len(self.items) * self.OPTION_HEIGHT
            + max(0, len(self.items) - 1) * self.OPTION_SPACING
        )
        self.surface_layout.activate()
        content_height = max(calculated_height, self.surface_layout.sizeHint().height())
        requested_height = (
            content_height
            + 2 * self.SURFACE_INSET
            + 2 * self.SURFACE_BORDER
            + self.POPUP_HEIGHT_SAFETY
        )
        popup_height = min(requested_height, self.MAX_POPUP_HEIGHT)
        popup_width = max(self.width(), 240)
        top_left = self.mapToGlobal(QPoint(0, 0))
        below_y = top_left.y() + self.height() + 4
        screen = QApplication.screenAt(top_left)
        available = screen.availableGeometry() if screen else QRect()
        final_x = top_left.x()
        final_y = below_y
        if available.isValid():
            popup_width = min(popup_width, available.width())
            popup_height = min(popup_height, max(1, available.height() - 8))
            room_below = available.bottom() - below_y + 1
            room_above = top_left.y() - available.top() - 4
            if room_below < popup_height and room_above > room_below:
                final_y = top_left.y() - popup_height - 4
            final_x = max(
                available.left(),
                min(final_x, available.right() - popup_width + 1),
            )
            final_y = max(
                available.top(),
                min(final_y, available.bottom() - popup_height + 1),
            )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
            if popup_height >= requested_height
            else Qt.ScrollBarAsNeeded
        )
        self.popup.setGeometry(final_x, final_y, popup_width, popup_height)
        self._install_popup_filters()
        self.popup.setWindowOpacity(0.0)
        self.popup.show()
        self.popup.raise_()
        self.popup.activateWindow()
        self._focus_option(self._current_index())
        animation = QPropertyAnimation(self.popup, b"windowOpacity", self)
        animation.setDuration(95)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation = animation
        animation.finished.connect(
            lambda current=animation: self._animation_finished(current, False)
        )
        animation.start()

    def hide_popup(self, immediate=False, restore_focus=False):
        if not hasattr(self, "popup"):
            return
        popup_visible = self.popup.isVisible()
        self._stop_animation()
        self._restore_button_focus = bool(restore_focus)
        self._remove_popup_filters()
        if not popup_visible:
            self._closing = False
            self._restore_focus_after_close()
            return
        if immediate:
            self.popup.hide()
            self.popup.setWindowOpacity(1.0)
            self._closing = False
            self._restore_focus_after_close()
            return
        self._closing = True
        animation = QPropertyAnimation(self.popup, b"windowOpacity", self)
        animation.setDuration(65)
        animation.setStartValue(self.popup.windowOpacity())
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InCubic)
        self._animation = animation
        animation.finished.connect(
            lambda current=animation: self._animation_finished(current, True)
        )
        animation.start()

    def _install_popup_filters(self):
        self._remove_popup_filters()
        hosts = []
        current = self
        while current is not None:
            current.installEventFilter(self)
            hosts.append(current)
            current = current.parentWidget()
        self._popup_filter_hosts = tuple(hosts)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)
            self._popup_application_filter = True

    def _remove_popup_filters(self):
        application = QApplication.instance()
        if self._popup_application_filter and application is not None:
            application.removeEventFilter(self)
        self._popup_application_filter = False
        for host in self._popup_filter_hosts:
            try:
                host.removeEventFilter(self)
            except RuntimeError:
                pass
        self._popup_filter_hosts = ()

    def _stop_animation(self):
        if self._animation is None:
            return
        animation = self._animation
        self._animation = None
        animation.stop()
        animation.deleteLater()

    def _animation_finished(self, animation, hide_after):
        if self._animation is animation:
            self._animation = None
        if hide_after:
            self.popup.hide()
            self.popup.setWindowOpacity(1.0)
            self._closing = False
            self._restore_focus_after_close()
        animation.deleteLater()

    def _restore_focus_after_close(self):
        if not self._restore_button_focus:
            return
        self._restore_button_focus = False
        owner = self.window()
        if owner is not None:
            owner.activateWindow()
        self.button.setFocus(Qt.PopupFocusReason)

    def eventFilter(self, watched, event):
        popup = getattr(self, "popup", None)
        if popup is not None and popup.isVisible():
            host_transition_events = (
                QEvent.Move,
                QEvent.Resize,
                QEvent.Hide,
                QEvent.Close,
                QEvent.WindowStateChange,
            )
            if watched in self._popup_filter_hosts and event.type() in host_transition_events:
                self.hide_popup(immediate=True)
            elif (
                watched in self._popup_filter_hosts
                and event.type() == QEvent.EnabledChange
                and not watched.isEnabled()
            ):
                self.hide_popup(immediate=True)

        if popup is not None and event.type() == QEvent.KeyPress:
            key = event.key()
            popup_open = popup.isVisible() and not self._closing

            if not popup_open and watched is self.button and key in (
                Qt.Key_Return,
                Qt.Key_Enter,
                Qt.Key_Space,
                Qt.Key_Up,
                Qt.Key_Down,
                Qt.Key_Home,
                Qt.Key_End,
            ):
                self.show_popup()
                if key == Qt.Key_Home:
                    self._focus_option(0)
                elif key == Qt.Key_End:
                    self._focus_option(len(self.option_buttons) - 1)
                event.accept()
                return True

            if popup_open:
                if key == Qt.Key_Escape:
                    self.hide_popup(restore_focus=True)
                    event.accept()
                    return True

                current_index = self._focused_index()
                if key == Qt.Key_Up:
                    self._focus_option(current_index - 1)
                elif key == Qt.Key_Down:
                    self._focus_option(current_index + 1)
                elif key == Qt.Key_Home:
                    self._focus_option(0)
                elif key == Qt.Key_End:
                    self._focus_option(len(self.option_buttons) - 1)
                elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    self.select(self.items[current_index])
                else:
                    return super().eventFilter(watched, event)
                event.accept()
                return True

        if (
            popup is not None
            and popup.isVisible()
            and event.type() == QEvent.MouseButtonPress
        ):
            global_position = event.globalPosition().toPoint()
            button_rect = QRect(
                self.button.mapToGlobal(QPoint(0, 0)),
                self.button.size(),
            )
            if not self.popup.frameGeometry().contains(
                global_position
            ) and not button_rect.contains(global_position):
                self.hide_popup()
        return super().eventFilter(watched, event)


class AnalysisWorker(QObject):
    finished = Signal(str, str, object, object)
    progress = Signal(int)
    logged = Signal(str)
    result_ready = Signal(object)

    def __init__(
        self,
        image_data: bytes,
        media_type: str,
        api_key: str,
        model,
        effort_label: str,
        passes: int,
        prompt_mode: str,
        extra_guidance: str,
        output_file: Optional[Path],
        source_name: str,
    ):
        super().__init__()
        self.image_data = image_data
        self.media_type = media_type
        self.api_key = api_key
        self.model = model
        self.effort_label = effort_label
        self.passes = passes
        self.prompt_mode = prompt_mode
        self.extra_guidance = extra_guidance
        self.output_file = output_file
        self.source_name = source_name
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def clear_private_payload(self):
        self.api_key = ""
        self.extra_guidance = ""
        self.image_data = b""

    def _safe_message(self, message, fallback="") -> str:
        return redact_secret_text(message, self.api_key) or fallback

    def _emit_safe_log(self, message):
        self.logged.emit(self._safe_message(message))

    @Slot()
    def run(self):
        stats = AnalysisStats(self.passes)
        try:
            result, note, stats = analyse_image(
                self.image_data,
                self.media_type,
                self.api_key,
                self.model,
                self.effort_label,
                self.passes,
                self.prompt_mode,
                self.extra_guidance,
                self.cancel_event,
                self._emit_safe_log,
                self.progress.emit,
                stats,
            )
            check_cancel(self.cancel_event)
            self._emit_safe_log(note)
            self.result_ready.emit(result)
            if self.output_file is None:
                self.progress.emit(100)
                self.finished.emit(
                    "success",
                    "Location found. Report saving is off.",
                    result,
                    stats,
                )
                return
            try:
                write_report(
                    self.output_file,
                    result,
                    self.source_name,
                    self.prompt_mode,
                    self.model,
                    self.effort_label,
                    stats.requested,
                    stats.completed,
                    stats.attempted,
                    stats.usable,
                )
            except Exception:
                warning = (
                    f"Location found, but {self.output_file.name} could not be saved. "
                    "The result is still available in the app."
                )
                self._emit_safe_log(warning)
                self.progress.emit(100)
                self.finished.emit(
                    "success_warning",
                    warning,
                    result,
                    stats,
                )
                return
            self.progress.emit(100)
            self.finished.emit(
                "success",
                f"Saved {self.output_file.name}.",
                result,
                stats,
            )
        except AnalysisCancelled:
            self.finished.emit(
                "cancelled", "Analysis cancelled.", None, stats
            )
        except (AnalysisError, OSError) as error:
            self.finished.emit(
                "failed",
                self._safe_message(error, "The analysis could not be completed."),
                None,
                stats,
            )
        except Exception as error:
            self.finished.emit(
                "failed",
                self._safe_message(error, "The analysis stopped unexpectedly."),
                None,
                stats,
            )
        finally:
            self.clear_private_payload()


class LocationFinder(QMainWindow):
    NORMAL_MINIMUM_WIDTH = 800
    NORMAL_MINIMUM_HEIGHT = 450

    def __init__(self, settings_path=SETTINGS_PATH, testing=False):
        super().__init__()
        self.testing = bool(testing)
        self._adaptive_compact = None
        self._adaptive_layout_key = None
        self._updating_adaptive_layout = False
        self._saved_extra_guidance = None
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            available_width = max(1, available.width())
            available_height = max(1, available.height())
            minimum_width = min(self.NORMAL_MINIMUM_WIDTH, available_width)
            minimum_height = min(self.NORMAL_MINIMUM_HEIGHT, available_height)
            self.setMinimumSize(minimum_width, minimum_height)
            target_width = (
                available_width
                if available_width < self.NORMAL_MINIMUM_WIDTH
                else max(
                    minimum_width,
                    min(1260, available_width - 24),
                )
            )
            target_height = (
                available_height
                if available_height < self.NORMAL_MINIMUM_HEIGHT
                else max(
                    minimum_height,
                    min(800, available_height - 24),
                )
            )
            self.resize(target_width, target_height)
        else:
            self.setMinimumSize(
                self.NORMAL_MINIMUM_WIDTH,
                self.NORMAL_MINIMUM_HEIGHT,
            )
            self.resize(1260, 800)

        if not self.testing:
            try:
                RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        self.settings = QSettings(str(settings_path), QSettings.IniFormat)
        self.source_file: Optional[Path] = None
        self.save_results_enabled = saved_bool(
            self.settings,
            "save_results_enabled",
            True,
        )
        saved_folder = str(self.settings.value("output_folder", "") or "")
        default_output_folder = Path.home() / "Downloads"
        try:
            selected_output_folder = (
                Path(saved_folder) if saved_folder else default_output_folder
            )
        except (OSError, ValueError, TypeError):
            selected_output_folder = default_output_folder
        if self.save_results_enabled:
            try:
                if not selected_output_folder.is_dir():
                    selected_output_folder = default_output_folder
            except (OSError, ValueError):
                selected_output_folder = default_output_folder
        self.output_folder = selected_output_folder
        self.output_file: Optional[Path] = None
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[AnalysisWorker] = None
        self.running = False
        self.last_log_message = ""
        self.last_result: Optional[GeoResult] = None
        self._last_report_context = None
        self._report_needs_save = False
        self._restoring = True
        self._settings_error_reported = False
        self._current_provider_id = ""
        self._pending_keys = {}
        self._providers = direct_providers()
        if not self._providers:
            raise RuntimeError("No supported direct AI providers are available.")
        self._provider_by_label = {
            provider.label: provider for provider in self._providers
        }
        self._model_by_label = {}
        self._accepted_model_labels = {}
        self._confirmed_privacy_models = set()
        self._capture_targets = ()
        self._capture_by_label = {}
        self.dropdowns = []

        self.apply_style()
        self.build_ui()
        self.restore_preferences()
        self._restoring = False
        self.update_note()

    def apply_style(self):
        QApplication.instance().setStyleSheet(
            """
            QWidget {
                color: #f5f5f5;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QFrame#windowFrame {
                background: #070707;
                border: 1px solid #252525;
                border-radius: 14px;
            }
            QFrame#titleBar {
                background: #070707;
                border: none;
                border-bottom: 1px solid #1c1c1c;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }
            QLabel#windowTitle {
                color: #bdbdbd;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#closeDot,
            QPushButton#minimizeDot,
            QPushButton#maximizeDot {
                border: none;
                border-radius: 6px;
                min-height: 13px;
                max-height: 13px;
                min-width: 13px;
                max-width: 13px;
                padding: 0;
            }
            QPushButton#closeDot { background: #ff5f57; }
            QPushButton#minimizeDot { background: #febc2e; }
            QPushButton#maximizeDot { background: #28c840; }
            QPushButton#closeDot:hover,
            QPushButton#minimizeDot:hover,
            QPushButton#maximizeDot:hover {
                border: 1px solid rgba(0, 0, 0, 90);
            }
            QFrame#panel {
                background: #0d0d0d;
                border: 1px solid #242424;
                border-radius: 14px;
            }
            QDialog#appDialog {
                background: transparent;
                border: none;
            }
            QFrame#dialogSurface {
                background: #0d0d0d;
                border: 1px solid #303030;
                border-radius: 14px;
            }
            QLabel#dialogHeading {
                color: #f4f4f4;
                font-family: "Segoe UI";
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#dialogBody {
                color: #d2d2d2;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QLabel#dialogLink { font-family: "Segoe UI"; font-size: 12px; }
            QScrollArea#pageScroll,
            QScrollArea#pageScroll > QWidget > QWidget,
            QWidget#pageContent,
            QScrollArea#dialogScroll,
            QScrollArea#dialogScroll > QWidget > QWidget,
            QWidget#dialogScrollContent,
            QScrollArea#settingsScroll,
            QScrollArea#settingsScroll > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            QTabWidget#leftTabs,
            QTabWidget#leftTabs QTabBar {
                background: transparent;
                border: none;
            }
            QTabWidget#leftTabs::pane {
                background: transparent;
                border: none;
                top: -1px;
            }
            QTabWidget#leftTabs QTabBar::tab {
                background: #111111;
                color: #8d8d8d;
                border: 1px solid #252525;
                border-radius: 8px;
                min-height: 34px;
                padding: 0 13px;
                margin: 0 2px;
                font-size: 12px;
                font-weight: 600;
            }
            QTabWidget#leftTabs QTabBar::tab:selected {
                background: #f4f4f4;
                color: #080808;
                border-color: #f4f4f4;
            }
            QTabWidget#leftTabs QTabBar::tab:hover:!selected {
                background: #191919;
                color: #d0d0d0;
            }
            QLabel#label {
                color: #b8b8b8;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#status { color: #9b9b9b; font-size: 12px; }
            QLabel#note { color: #858585; font-size: 11px; }
            QLabel#warningNote {
                color: #ffb3ad;
                background: #1a0e0d;
                border: 1px solid #4a2421;
                border-radius: 8px;
                padding: 7px 9px;
                font-size: 11px;
            }
            QLabel#mapHeadline {
                color: #f1f1f1;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#mapSubhead { color: #8d959c; font-size: 11px; }
            QLineEdit {
                background: #0a0a0a;
                border: 1px solid #292929;
                border-radius: 10px;
                min-height: 38px;
                padding: 0 11px;
                selection-background-color: #ffffff;
                selection-color: #000000;
            }
            QLineEdit:focus { border: 1px solid #ffffff; }
            QLineEdit:disabled { color: #606060; border-color: #202020; }
            QPushButton {
                background: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 10px;
                min-height: 38px;
                padding: 0 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1d1d1d; border-color: #3a3a3a; }
            QPushButton:pressed { background: #101010; }
            QPushButton:disabled {
                color: #555555;
                background: #101010;
                border-color: #202020;
            }
            QFrame#mapZoomControls QPushButton,
            QFrame#mapLayerControls QPushButton {
                min-height: 0px;
            }
            QPushButton#primary {
                background: #ffffff;
                color: #000000;
                border: none;
                min-height: 42px;
            }
            QPushButton#primary:hover { background: #e7e7e7; }
            QPushButton#primary:disabled { background: #777777; color: #202020; }
            QPushButton#small {
                min-height: 29px;
                max-height: 29px;
                border-radius: 8px;
                padding: 0 10px;
                color: #c2c2c2;
                font-size: 11px;
            }
            QPushButton#saveToggle {
                min-height: 29px;
                max-height: 29px;
                min-width: 52px;
                max-width: 52px;
                border-radius: 15px;
                padding: 0;
                color: #8d8d8d;
                background: #121212;
            }
            QPushButton#saveToggle:checked {
                color: #050505;
                background: #f2f2f2;
                border-color: #f2f2f2;
            }
            QPushButton#saveToggle:disabled { color: #555555; }
            QPushButton#dropdownButton {
                background: #0a0a0a;
                border: 1px solid #292929;
                border-radius: 10px;
                min-height: 38px;
                padding: 0 34px 0 11px;
                text-align: left;
                font-weight: 500;
            }
            QPushButton#dropdownButton:hover {
                background: #101010;
                border-color: #3b3b3b;
            }
            QFrame#dropdownSurface {
                background: #111111;
                border: 1px solid #303030;
                border-radius: 11px;
            }
            QFrame#dropdownPopup { background: transparent; border: none; }
            QScrollArea#dropdownScroll,
            QScrollArea#dropdownScroll QWidget#qt_scrollarea_viewport,
            QWidget#dropdownOptions {
                background: transparent;
                border: none;
            }
            QPushButton#dropdownOption {
                background: transparent;
                border: none;
                border-radius: 7px;
                min-height: 32px;
                padding: 0 10px;
                text-align: left;
                font-weight: 500;
            }
            QPushButton#dropdownOption:hover { background: #242424; }
            QFrame#pathFrame {
                background: #0a0a0a;
                border: 1px solid #292929;
                border-radius: 10px;
            }
            QLabel#pathLabel { color: #d7d7d7; padding-left: 10px; }
            QTextEdit {
                background: #090909;
                color: #c8c8c8;
                border: 1px solid #242424;
                border-radius: 10px;
                padding: 7px;
                font-family: "Segoe UI";
                font-size: 13px;
                selection-background-color: #ffffff;
                selection-color: #000000;
            }
            QTextEdit#activityConsole {
                font-family: "Cascadia Mono", "Consolas";
                font-size: 11px;
            }
            QTextEdit#tipsBox {
                font-family: "Segoe UI";
                font-size: 13px;
                padding: 12px;
            }
            QProgressBar {
                background: #121212;
                border: none;
                border-radius: 3px;
                min-height: 6px;
                max-height: 6px;
            }
            QProgressBar::chunk { background: #ffffff; border-radius: 3px; }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                border: none;
                margin: 6px 1px 6px 1px;
            }
            QScrollBar::handle:vertical {
                background: #3b3b3b;
                border: none;
                border-radius: 4px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover { background: #505050; }
            QScrollBar::handle:vertical:pressed { background: #686868; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
                border: none;
                margin: 1px 6px 1px 6px;
            }
            QScrollBar::handle:horizontal {
                background: #3b3b3b;
                border: none;
                border-radius: 4px;
                min-width: 28px;
            }
            QScrollBar::handle:horizontal:hover { background: #505050; }
            QScrollBar::handle:horizontal:pressed { background: #686868; }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
            }
            QScrollBar#dropdownScrollBar:vertical {
                width: 8px;
                background: transparent;
                border: none;
                margin: 5px 0 5px 2px;
            }
            QScrollBar#dropdownScrollBar::handle:vertical {
                background: #4a4a4a;
                border: none;
                border-radius: 4px;
                min-height: 28px;
            }
            QScrollBar#dropdownScrollBar::handle:vertical:hover {
                background: #626262;
            }
            QScrollBar#dropdownScrollBar::add-line:vertical,
            QScrollBar#dropdownScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar#dropdownScrollBar::add-page:vertical,
            QScrollBar#dropdownScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
            }
            QSizeGrip { background: transparent; }
            QToolTip {
                background: #171717;
                color: #eeeeee;
                border: 1px solid #343434;
                padding: 5px;
            }
            """
        )

    def _new_dropdown(self, items, index=0):
        dropdown = AnimatedDropdown(items, index)
        self.dropdowns.append(dropdown)
        return dropdown

    @staticmethod
    def _add_labeled(layout, label_text, widget):
        column = QVBoxLayout()
        column.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("label")
        column.addWidget(label)
        column.addWidget(widget)
        layout.addLayout(column, 1)
        return label

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        self.window_frame = QFrame()
        self.window_frame.setObjectName("windowFrame")
        outer.addWidget(self.window_frame)
        window_layout = QVBoxLayout(self.window_frame)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)
        self.title_bar = TitleBar(self)
        window_layout.addWidget(self.title_bar)

        content = ViewportPage()
        content.setObjectName("pageContent")
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.page_content = content
        self.page_scroll = ReachableScrollArea()
        self.page_scroll.setObjectName("pageScroll")
        self.page_scroll.setFrameShape(QFrame.NoFrame)
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.page_scroll.viewport().setAutoFillBackground(False)
        self.page_scroll.viewport().setAttribute(Qt.WA_TranslucentBackground)
        self.page_scroll.setWidget(content)
        window_layout.addWidget(self.page_scroll, 1)
        page = QHBoxLayout(content)
        page.setContentsMargins(18, 16, 18, 18)
        page.setSpacing(14)
        self.page_layout = page

        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_panel.setMinimumWidth(390)
        left_panel.setMaximumWidth(485)
        self.left_panel = left_panel
        left_shell = QVBoxLayout(left_panel)
        left_shell.setContentsMargins(10, 10, 10, 10)
        left_shell.setSpacing(8)

        self.left_tabs = QTabWidget()
        self.left_tabs.setObjectName("leftTabs")
        self.left_tabs.setTabBar(EqualWidthTabBar(self.left_tabs))
        self.left_tabs.setDocumentMode(True)
        self.left_tabs.tabBar().setDrawBase(False)
        left_shell.addWidget(self.left_tabs, 1)

        image_tab = QWidget()
        image_shell = QVBoxLayout(image_tab)
        image_shell.setContentsMargins(0, 8, 0, 0)
        image_shell.setSpacing(0)
        self.settings_scroll = ReachableScrollArea()
        self.settings_scroll.setObjectName("settingsScroll")
        self.settings_scroll.setFrameShape(QFrame.NoFrame)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_content = QWidget()
        left_content.setMinimumWidth(0)
        self.settings_scroll.setWidget(left_content)
        image_shell.addWidget(self.settings_scroll)
        left = QVBoxLayout(left_content)
        left.setContentsMargins(5, 3, 15, 8)
        left.setSpacing(9)

        source_label = QLabel("Image input")
        source_label.setObjectName("label")
        left.addWidget(source_label)
        self.source_dropdown = self._new_dropdown(SOURCE_OPTIONS)
        left.addWidget(self.source_dropdown)

        self.monitor_label = QLabel("Monitor to capture")
        self.monitor_label.setObjectName("label")
        left.addWidget(self.monitor_label)
        self.monitor_dropdown = self._new_dropdown(("Detecting monitors...",))
        left.addWidget(self.monitor_dropdown)

        file_label = QLabel("Selected image")
        file_label.setObjectName("label")
        left.addWidget(file_label)
        self.file_label = file_label
        file_row = QHBoxLayout()
        file_row.setSpacing(7)
        file_frame = QFrame()
        file_frame.setObjectName("pathFrame")
        self.file_frame = file_frame
        file_frame.setMinimumHeight(38)
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_path_label = ElidedPathLabel(
            "A screenshot is taken when analysis starts"
        )
        self.file_path_label.setObjectName("pathLabel")
        self.file_path_label.setTextFormat(Qt.PlainText)
        self.file_path_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.file_path_label.setMinimumWidth(0)
        file_layout.addWidget(self.file_path_label)
        self.file_browse_button = QPushButton("Browse")
        self.file_browse_button.setFixedWidth(78)
        self.file_browse_button.clicked.connect(self.choose_file)
        file_row.addWidget(file_frame, 1)
        file_row.addWidget(self.file_browse_button)
        left.addLayout(file_row)

        prompt_label = QLabel("Image type")
        prompt_label.setObjectName("label")
        left.addWidget(prompt_label)
        self.prompt_dropdown = self._new_dropdown(PROMPT_OPTIONS)
        left.addWidget(self.prompt_dropdown)

        guidance_label = QLabel("Extra clue or region hint (optional)")
        guidance_label.setObjectName("label")
        left.addWidget(guidance_label)
        self.extra_guidance_input = QLineEdit()
        self.extra_guidance_input.setPlaceholderText("Example: likely northern Europe")
        left.addWidget(self.extra_guidance_input)

        activity_header = QHBoxLayout()
        activity_header.setSpacing(7)
        activity_label = QLabel("Activity")
        activity_label.setObjectName("label")
        activity_header.addWidget(activity_label, 1)
        self.open_folder_button = QPushButton("Open output")
        self.open_folder_button.setObjectName("small")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("small")
        clear_button.clicked.connect(self.clear_log)
        activity_header.addWidget(self.open_folder_button)
        activity_header.addWidget(clear_button)
        left.addLayout(activity_header)
        self.log_box = SmoothTextEdit()
        self.log_box.setObjectName("activityConsole")
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Progress, clues, errors, and saved reports appear here")
        self.log_box.setFixedHeight(120)
        left.addWidget(self.log_box, 1)

        ai_tab = QWidget()
        ai_shell = QVBoxLayout(ai_tab)
        ai_shell.setContentsMargins(0, 8, 0, 0)
        ai_shell.setSpacing(0)
        self.ai_settings_scroll = ReachableScrollArea()
        self.ai_settings_scroll.setObjectName("settingsScroll")
        self.ai_settings_scroll.setFrameShape(QFrame.NoFrame)
        self.ai_settings_scroll.setWidgetResizable(True)
        self.ai_settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ai_settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        ai_content = QWidget()
        self.ai_settings_scroll.setWidget(ai_content)
        ai_shell.addWidget(self.ai_settings_scroll)
        ai = QVBoxLayout(ai_content)
        ai.setContentsMargins(5, 3, 15, 8)
        ai.setSpacing(9)

        provider_label = QLabel("AI service")
        provider_label.setObjectName("label")
        ai.addWidget(provider_label)
        self.provider_dropdown = self._new_dropdown(
            [provider.label for provider in self._providers]
        )
        ai.addWidget(self.provider_dropdown)

        model_label = QLabel("Image model")
        model_label.setObjectName("label")
        ai.addWidget(model_label)
        initial_models = models_for_provider(self._providers[0].id)
        self._model_by_label = {model.label: model for model in initial_models}
        self.model_dropdown = self._new_dropdown(
            [model.label for model in initial_models],
            [model.id for model in initial_models].index(
                default_model(self._providers[0].id).id
            ),
        )
        ai.addWidget(self.model_dropdown)

        analysis_row = QHBoxLayout()
        analysis_row.setSpacing(9)
        self.effort_dropdown = self._new_dropdown(EFFORT_LABELS, 2)
        self.passes_dropdown = self._new_dropdown(PASS_OPTIONS, 1)
        self._add_labeled(analysis_row, "Analysis effort", self.effort_dropdown)
        self._add_labeled(analysis_row, "Number of AI checks", self.passes_dropdown)
        ai.addLayout(analysis_row)

        self.note_label = QLabel()
        self.note_label.setObjectName("note")
        self.note_label.setTextFormat(Qt.PlainText)
        self.note_label.setWordWrap(True)
        ai.addWidget(self.note_label)

        self.privacy_label = QLabel()
        self.privacy_label.setObjectName("warningNote")
        self.privacy_label.setTextFormat(Qt.PlainText)
        self.privacy_label.setWordWrap(True)
        ai.addWidget(self.privacy_label)

        self.model_details_button = QPushButton("Model, price, and privacy details")
        self.model_details_button.setObjectName("small")
        self.model_details_button.setMinimumWidth(0)
        self.model_details_button.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Preferred,
        )
        self.model_details_button.clicked.connect(self.show_model_details)
        ai.addWidget(self.model_details_button)

        self.key_label = QLabel("API key")
        self.key_label.setObjectName("label")
        ai.addWidget(self.key_label)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.returnPressed.connect(self.save_api_key)
        ai.addWidget(self.api_key_input)
        key_row = QHBoxLayout()
        key_row.setSpacing(7)
        self.save_key_button = QPushButton("Save")
        self.save_key_button.clicked.connect(self.save_api_key)
        self.show_key_button = QPushButton("Show")
        self.show_key_button.clicked.connect(self.toggle_key_visibility)
        self.get_key_button = QPushButton("Get key")
        self.get_key_button.clicked.connect(self.open_key_page)
        key_row.addWidget(self.save_key_button, 1)
        key_row.addWidget(self.show_key_button, 1)
        key_row.addWidget(self.get_key_button, 1)
        ai.addLayout(key_row)
        self.ai_status_label = QLabel("")
        self.ai_status_label.setObjectName("status")
        self.ai_status_label.setTextFormat(Qt.PlainText)
        self.ai_status_label.setWordWrap(True)
        ai.addWidget(self.ai_status_label)
        ai.addStretch(1)

        footer = QWidget()
        self.footer = footer
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 2, 0, 2)
        footer_layout.setSpacing(7)

        save_setting_row = QHBoxLayout()
        save_setting_row.setSpacing(8)
        save_setting_label = QLabel("Save a report after each result")
        save_setting_label.setObjectName("label")
        save_setting_label.setWordWrap(True)
        save_setting_row.addWidget(save_setting_label, 1)
        self.save_result_toggle = QPushButton(
            "On" if self.save_results_enabled else "Off"
        )
        self.save_result_toggle.setObjectName("saveToggle")
        self.save_result_toggle.setCheckable(True)
        self.save_result_toggle.setChecked(self.save_results_enabled)
        self.save_result_toggle.setAccessibleName("Save reports automatically")
        self.save_result_toggle.setAccessibleDescription(
            "When on, every successful location result is saved as a text report."
        )
        self.save_result_toggle.toggled.connect(self.save_result_changed)
        save_setting_row.addWidget(self.save_result_toggle)
        footer_layout.addLayout(save_setting_row)

        self.output_controls = QWidget()
        output_controls_layout = QVBoxLayout(self.output_controls)
        output_controls_layout.setContentsMargins(0, 0, 0, 0)
        output_controls_layout.setSpacing(7)
        output_label = QLabel("Save reports to")
        output_label.setObjectName("label")
        output_controls_layout.addWidget(output_label)
        output_row = QHBoxLayout()
        output_row.setSpacing(7)
        output_frame = QFrame()
        output_frame.setObjectName("pathFrame")
        output_frame.setMinimumHeight(38)
        output_layout = QHBoxLayout(output_frame)
        output_layout.setContentsMargins(0, 0, 0, 0)
        self.output_path_label = ElidedPathLabel(str(self.output_folder))
        self.output_path_label.setObjectName("pathLabel")
        self.output_path_label.setTextFormat(Qt.PlainText)
        self.output_path_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.output_path_label.setMinimumWidth(0)
        output_layout.addWidget(self.output_path_label)
        self.output_browse_button = QPushButton("Browse")
        self.output_browse_button.setFixedWidth(78)
        self.output_browse_button.clicked.connect(self.choose_output_folder)
        output_row.addWidget(output_frame, 1)
        output_row.addWidget(self.output_browse_button)
        output_controls_layout.addLayout(output_row)
        footer_layout.addWidget(self.output_controls)
        self.output_controls.setVisible(self.save_results_enabled)

        self.find_button = QPushButton("Find Location")
        self.find_button.setObjectName("primary")
        self.find_button.clicked.connect(self.find_or_cancel)
        footer_layout.addWidget(self.find_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        footer_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.status_label.setTextFormat(Qt.PlainText)
        footer_layout.addWidget(self.status_label)
        left.addWidget(footer)

        tips_tab = QWidget()
        tips_layout = QVBoxLayout(tips_tab)
        tips_layout.setContentsMargins(5, 10, 5, 5)
        tips_layout.setSpacing(8)
        tips_heading = QLabel("How to get a more accurate result")
        tips_heading.setObjectName("mapHeadline")
        tips_layout.addWidget(tips_heading)
        self.tips_box = SmoothTextEdit()
        self.tips_box.setObjectName("tipsBox")
        self.tips_box.setReadOnly(True)
        self.tips_box.document().setDocumentMargin(4)
        self.tips_box.setHtml(accuracy_tips_html())
        tips_layout.addWidget(self.tips_box, 1)

        self.left_tabs.addTab(image_tab, "Image")
        self.left_tabs.addTab(ai_tab, "AI Settings")
        self.left_tabs.addTab(tips_tab, "Tips")
        self.left_tabs.tabBar().setExpanding(True)
        self.left_tabs.tabBar().setUsesScrollButtons(False)
        self.left_tabs.setElideMode(Qt.ElideNone)
        for label in left_panel.findChildren(QLabel):
            if label.objectName() == "label":
                label.setMinimumWidth(0)
                label.setWordWrap(True)
                label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        map_panel = QFrame()
        map_panel.setObjectName("panel")
        map_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.map_panel = map_panel
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(14, 14, 14, 14)
        map_layout.setSpacing(8)
        map_header = QHBoxLayout()
        map_titles = QVBoxLayout()
        map_titles.setSpacing(2)
        map_headline = QLabel("Interactive location map")
        map_headline.setObjectName("mapHeadline")
        map_headline.setMinimumWidth(0)
        map_headline.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._map_subhead_full = "World view - a pin appears after a result"
        self.map_subhead = QLabel(self._map_subhead_full)
        self.map_subhead.setObjectName("mapSubhead")
        self.map_subhead.setTextFormat(Qt.PlainText)
        self.map_subhead.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.map_subhead.setMinimumWidth(0)
        self.set_map_subhead(self._map_subhead_full)
        map_titles.addWidget(map_headline)
        map_titles.addWidget(self.map_subhead)
        map_header.addLayout(map_titles, 1)
        map_layout.addLayout(map_header)
        self.map_view = WorldMapView(online_enabled=not self.testing)
        self.map_view.layer_changed.connect(self.map_layer_changed)
        map_layout.addWidget(self.map_view, 1)
        map_note = QLabel(
            "Street and satellite details load online. The world map still works offline."
        )
        map_note.setObjectName("mapSubhead")
        map_note.setAlignment(Qt.AlignCenter)
        map_note.setWordWrap(True)
        map_note.setMinimumWidth(0)
        map_note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        map_layout.addWidget(map_note)

        page.addWidget(left_panel)
        page.addWidget(map_panel, 1)

        self._update_adaptive_layout(force=True)

        self.size_grip = QSizeGrip(self.window_frame)
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.setToolTip("Drag to resize")
        adaptive_state = self._adaptive_compact or (False, False)
        self.size_grip.setVisible(not adaptive_state[1])
        self.size_grip.raise_()

        self.source_dropdown.changed.connect(self.source_changed)
        self.monitor_dropdown.changed.connect(self.monitor_changed)
        self.prompt_dropdown.changed.connect(self.persist_preference_change)
        self.provider_dropdown.changed.connect(self.provider_changed)
        self.passes_dropdown.changed.connect(self.preference_changed)
        self.model_dropdown.changed.connect(self.model_changed)
        self.effort_dropdown.changed.connect(self.preference_changed)
        self.extra_guidance_input.editingFinished.connect(
            self.persist_preference_change
        )
        self.left_tabs.currentChanged.connect(self.left_tab_changed)

    def restore_preferences(self):
        saved_source = str(self.settings.value("source", "") or "")
        if saved_source == "Screen capture (all screens)":
            saved_source = "Screen capture"
        if saved_source in SOURCE_OPTIONS:
            self.source_dropdown.select(saved_source, emit=False)
        saved_prompt = str(self.settings.value("prompt_mode", "") or "")
        if saved_prompt == "Normal image":
            saved_prompt = "Regular photo or screenshot"
        if saved_prompt in PROMPT_OPTIONS:
            self.prompt_dropdown.select(saved_prompt, emit=False)
        saved_effort = str(self.settings.value("effort", "") or "")
        if saved_effort in EFFORT_LABELS:
            self.effort_dropdown.select(saved_effort, emit=False)
        saved_passes = str(self.settings.value("passes", "") or "")
        if saved_passes in PASS_OPTIONS:
            self.passes_dropdown.select(saved_passes, emit=False)
        try:
            saved_guidance = load_saved_extra_guidance(self.settings)
        except (OSError, ValueError, UnicodeError):
            saved_guidance = ""
            self.append_log(
                "Saved extra guidance could not be unlocked, so it was not loaded."
            )
        self.extra_guidance_input.setText(saved_guidance)
        self._saved_extra_guidance = str(saved_guidance or "").strip()[:1200]

        saved_provider_id = str(
            self.settings.value("provider", self._providers[0].id)
            or self._providers[0].id
        )
        provider = next(
            (
                candidate
                for candidate in self._providers
                if candidate.id == saved_provider_id
            ),
            self._providers[0],
        )
        self.provider_dropdown.select(provider.label, emit=False)
        self.provider_changed(provider.label)
        saved_monitor_id = str(
            self.settings.value(MONITOR_SETTING_KEY, "") or ""
        )
        self.refresh_capture_targets(saved_monitor_id)
        try:
            map_schema = int(self.settings.value("map/preference_schema", 0) or 0)
        except (TypeError, ValueError):
            map_schema = 0
        if map_schema < MAP_PREFERENCE_SCHEMA_VERSION:
            saved_map_layer = "street"
            self.settings.setValue("map/layer", saved_map_layer)
            self.settings.setValue(
                "map/preference_schema", MAP_PREFERENCE_SCHEMA_VERSION
            )
            self.settings.sync()
        else:
            saved_map_layer = str(
                self.settings.value("map/layer", "street") or "street"
            )
        if saved_map_layer in ("street", "satellite"):
            self.map_view.set_layer(saved_map_layer)
        self.source_changed(self.source_dropdown.currentText())

        if not self.api_key_input.text().strip():
            self.append_log(
                f"Add your {provider.name} API key to get started. "
                "Saved keys are protected for this Windows user."
            )

    def save_preferences(self):
        if self._restoring:
            return True
        model = self.selected_model()
        plain_preferences = {
            "source": self.source_dropdown.currentText(),
            "prompt_mode": self.prompt_dropdown.currentText(),
            "effort": self.effort_dropdown.currentText(),
            "passes": self.passes_dropdown.currentText(),
            "provider": self._current_provider_id,
            f"models/{self._current_provider_id}": model.id,
            "output_folder": str(self.output_folder),
            "save_results_enabled": self.save_results_enabled,
        }
        selected_target = self.selected_capture_target()
        if selected_target is not None:
            plain_preferences[MONITOR_SETTING_KEY] = selected_target.id

        settings_dirty = False
        for key, value in plain_preferences.items():
            if isinstance(value, bool):
                unchanged = saved_bool(self.settings, key, not value) == value
            else:
                unchanged = str(self.settings.value(key, "") or "") == str(value)
            if not unchanged:
                self.settings.setValue(key, value)
                settings_dirty = True

        guidance = self.extra_guidance_input.text().strip()[:1200]
        guidance_synced = False
        save_error = False
        if guidance != self._saved_extra_guidance:
            try:
                save_extra_guidance(self.settings, guidance)
            except OSError:
                save_error = True
            else:
                self._saved_extra_guidance = guidance
                guidance_synced = True
        if settings_dirty and not guidance_synced:
            self.settings.sync()
            if self.settings.status() != QSettings.Status.NoError:
                save_error = True
        if save_error:
            self.status_label.setText("Settings could not be saved")
            if not self._settings_error_reported:
                self.append_log(
                    "Local preferences could not be saved. Check that the app folder "
                    "is writable, then run Installer.bat again if the problem continues."
                )
            self._settings_error_reported = True
            return False
        self._settings_error_reported = False
        return True

    def selected_model(self):
        selected = self._model_by_label.get(self.model_dropdown.currentText())
        if selected is not None:
            return selected
        return default_model(self._current_provider_id or self._providers[0].id)

    def selected_passes(self) -> int:
        return PASSES_BY_LABEL.get(self.passes_dropdown.currentText(), 2)

    def selected_capture_target(self):
        return getattr(self, "_capture_by_label", {}).get(
            self.monitor_dropdown.currentText()
        )

    def refresh_capture_targets(self, preferred_id=""):
        current = self.selected_capture_target()
        requested_id = str(preferred_id or (current.id if current else "") or "")
        try:
            targets = enumerate_capture_targets()
            chosen = resolve_saved_target_from_targets(requested_id, targets)
        except ScreenCaptureError as error:
            self._capture_targets = ()
            self._capture_by_label = {}
            self.monitor_dropdown.set_items(("Monitor list unavailable",), 0)
            self.monitor_dropdown.setEnabled(False)
            self.append_log(str(error))
            return None

        self._capture_targets = targets
        self._capture_by_label = {target.label: target for target in targets}
        index = next(
            (position for position, target in enumerate(targets) if target.id == chosen.id),
            0,
        )
        self.monitor_dropdown.set_items([target.label for target in targets], index)
        self.monitor_dropdown.setEnabled(
            not self.running and self.source_dropdown.currentText() == "Screen capture"
        )
        return targets[index]

    def monitor_changed(self, value=""):
        del value
        target = self.selected_capture_target()
        if target is not None and self.source_dropdown.currentText() == "Screen capture":
            self.file_path_label.set_full_text(
                f"{target.label}; normal Windows cursor excluded",
                "Only this choice is captured. A cursor drawn inside a game can still appear.",
            )
        self.save_preferences()

    def map_layer_changed(self, layer: str):
        if not self._restoring and layer in ("street", "satellite"):
            self.settings.setValue("map/layer", layer)
            self.settings.setValue(
                "map/preference_schema", MAP_PREFERENCE_SCHEMA_VERSION
            )
            self.settings.sync()

    def left_tab_changed(self, index):
        for dropdown in self.dropdowns:
            dropdown.hide_popup(immediate=True)
        if index != 1 and hasattr(self, "ai_status_label"):
            self.ai_status_label.clear()

    @staticmethod
    def _privacy_model_key(model):
        return model.provider_id, model.id

    def _safe_model_label(self, provider_id: str) -> str:
        for label, model in self._model_by_label.items():
            if model.provider_id == provider_id and model_privacy_notice(model) is None:
                return label
        return next(iter(self._model_by_label), "")

    def _show_model_privacy_warning(self, model, notice) -> bool:
        dialog = AppDialog(notice["title"], self)
        dialog.resize(520, 300)
        layout = dialog.content_layout

        heading = QLabel(notice["title"])
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        body_scroll = ReachableScrollArea()
        body_scroll.setObjectName("dialogScroll")
        body_scroll.setFrameShape(QFrame.NoFrame)
        body_scroll.setWidgetResizable(True)
        body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        body_container = QWidget()
        body_container.setObjectName("dialogScrollContent")
        body_container.setMinimumWidth(0)
        body_layout = QVBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 7, 0)
        body_layout.setSpacing(12)

        body = QLabel(notice["message"])
        body.setObjectName("dialogBody")
        body.setTextFormat(Qt.PlainText)
        body.setWordWrap(True)
        body.setMinimumWidth(0)
        body.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body_layout.addWidget(body)

        if notice["link_url"]:
            policy_link = QLabel(
                '<a style="color:#ffffff" href="'
                + html.escape(notice["link_url"], quote=True)
                + '">'
                + html.escape(notice["link_label"])
                + "</a>"
            )
            policy_link.setObjectName("dialogLink")
            policy_link.setTextFormat(Qt.RichText)
            policy_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
            policy_link.setOpenExternalLinks(True)
            policy_link.setWordWrap(True)
            policy_link.setToolTip(notice["link_url"])
            body_layout.addWidget(policy_link)
        body_layout.addStretch(1)
        body_scroll.setWidget(body_container)
        layout.addWidget(body_scroll, 1)

        buttons = QBoxLayout(QBoxLayout.LeftToRight)
        buttons.setSpacing(9)
        buttons.addStretch(1)
        cancel_button = QPushButton(notice["cancel_label"])
        accept_button = QPushButton(notice["accept_label"])
        accept_button.setObjectName("primary")
        accept_button.setDefault(True)
        cancel_button.clicked.connect(dialog.reject)
        accept_button.clicked.connect(dialog.accept)
        buttons.addWidget(cancel_button)
        buttons.addWidget(accept_button)
        layout.addLayout(buttons)
        dialog.register_action_layout(buttons)
        return dialog.exec() == QDialog.Accepted

    def _confirm_model_privacy(self, model) -> bool:
        notice = model_privacy_notice(model)
        if notice is None:
            return True
        key = self._privacy_model_key(model)
        if key in self._confirmed_privacy_models:
            return True
        if not self._show_model_privacy_warning(model, notice):
            return False
        self._confirmed_privacy_models.add(key)
        return True

    def show_model_details(self):
        model = self.selected_model()
        provider = provider_by_id(self._current_provider_id)
        effort = self.effort_dropdown.currentText()
        passes = self.selected_passes()
        cost = estimate_cost(model, passes, effort_label=effort)
        cost_text = f"${cost:.4f}" if cost < 0.01 else f"${cost:.2f}"
        privacy_notice = model_privacy_notice(model)
        sections = [
            model.display_name,
            model.description,
            (
                f"Selected setup: {effort} effort, {passes} AI request"
                f"{'s' if passes != 1 else ''}. Rough model cost: about {cost_text}. "
                "Image fees, reasoning use, promotions, and provider prices can vary."
            ),
            "Provider privacy\n" + provider.privacy_note,
        ]
        if model.pricing_note:
            sections.append("Pricing note\n" + model.pricing_note)
        dialog = AppDialog("Model, price, and privacy details", self)
        dialog.resize(620, 420)
        layout = dialog.content_layout
        heading = QLabel("Model, price, and privacy details")
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        details = SmoothTextEdit()
        details.setObjectName("detailsText")
        details.setReadOnly(True)
        details.setPlainText("\n\n".join(sections))
        layout.addWidget(details, 1)
        if privacy_notice and privacy_notice["link_url"]:
            policy_link = QLabel(
                '<a style="color:#ffffff" href="'
                + html.escape(privacy_notice["link_url"], quote=True)
                + '">'
                + html.escape(privacy_notice["link_label"])
                + "</a>"
            )
            policy_link.setObjectName("dialogLink")
            policy_link.setTextFormat(Qt.RichText)
            policy_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
            policy_link.setOpenExternalLinks(True)
            policy_link.setWordWrap(True)
            policy_link.setToolTip(privacy_notice["link_url"])
            layout.addWidget(policy_link)
        close_button = QPushButton("Close")
        close_button.setObjectName("primary")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def provider_changed(self, label: str):
        provider = self._provider_by_label.get(label, self._providers[0])
        if hasattr(self, "ai_status_label"):
            self.ai_status_label.clear()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.show_key_button.setText("Show")
        old_provider_id = self._current_provider_id
        if old_provider_id:
            self._pending_keys[old_provider_id] = self.api_key_input.text().strip()
        self._current_provider_id = provider.id

        available_models = models_for_provider(provider.id)
        self._model_by_label = {model.label: model for model in available_models}
        saved_model_id = str(
            self.settings.value(f"models/{provider.id}", "") or ""
        )
        try:
            chosen = model_by_id(provider.id, saved_model_id)
        except KeyError:
            chosen = default_model(provider.id)
            if saved_model_id:
                self.settings.setValue(f"models/{provider.id}", chosen.id)
                self.settings.sync()
        index = [model.id for model in available_models].index(chosen.id)
        self.model_dropdown.set_items(
            [model.label for model in available_models],
            index,
        )
        accepted_label = self._accepted_model_labels.get(provider.id, "")
        if accepted_label not in self._model_by_label:
            accepted_label = (
                chosen.label
                if model_privacy_notice(chosen) is None
                else self._safe_model_label(provider.id)
            )
            self._accepted_model_labels[provider.id] = accepted_label

        key = self._pending_keys.get(provider.id)
        migrated = False
        if key is None:
            try:
                key, migrated = load_saved_provider_key(self.settings, provider.id)
            except (OSError, ValueError, UnicodeError):
                key = ""
                self.append_log(
                    f"The saved {provider.name} key could not be unlocked. "
                    "Paste and save it again."
                )
        self.api_key_input.setText(key or "")
        self.api_key_input.setPlaceholderText(provider.api_key_placeholder)
        self.key_label.setText(f"{provider.name} API key")
        self.get_key_button.setToolTip(f"Open {provider.api_key_url}")
        self.provider_dropdown.setToolTip(provider.description)
        if migrated:
            self.append_log(
                "Moved the old Anthropic key into the new protected per-service storage."
            )
        if self._restoring:
            self.update_note()
        else:
            self.model_changed()

    def model_changed(self, value=""):
        del value
        model = self.selected_model()
        provider_id = self._current_provider_id
        previous_label = self._accepted_model_labels.get(
            provider_id,
            self._safe_model_label(provider_id),
        )
        if not self._restoring and not self._confirm_model_privacy(model):
            fallback_label = (
                previous_label
                if previous_label in self._model_by_label
                else self._safe_model_label(provider_id)
            )
            if fallback_label:
                self.model_dropdown.select(fallback_label, emit=False)
            self.ai_status_label.setText(
                "Model change cancelled. The previous model is still selected."
            )
            self.append_log(
                f"Kept the previous model. Nothing was sent to {model.company}."
            )
        else:
            self._accepted_model_labels[provider_id] = self.model_dropdown.currentText()
            self.ai_status_label.clear()
        self.update_note()
        self.save_preferences()

    def preference_changed(self, value=""):
        del value
        self.update_note()
        self.save_preferences()

    def persist_preference_change(self, value=""):

        del value
        self.save_preferences()

    def save_result_changed(self, enabled: bool):
        self.save_results_enabled = bool(enabled)
        self.save_result_toggle.setText("On" if enabled else "Off")
        self.save_result_toggle.setAccessibleDescription(
            "Every successful result is saved as a text report."
            if enabled
            else "Results stay in the app and are not saved as text reports."
        )
        self.output_controls.setVisible(enabled)
        self.output_browse_button.setEnabled(enabled and not self.running)
        if not enabled:
            self._report_needs_save = False
            if self.open_folder_button.text() == "Save report":
                self.open_folder_button.setText("Open output")
                self.open_folder_button.setEnabled(self.output_file is not None)
        self.save_preferences()
        self._update_adaptive_layout(force=True)

    def source_changed(self, source: str):
        using_file = source == "Image file"
        self.file_browse_button.setEnabled(using_file and not self.running)
        self.file_browse_button.setVisible(using_file)
        self.file_label.setVisible(using_file)
        self.file_frame.setVisible(using_file)
        self.file_label.setText("Selected image")
        self.monitor_label.setVisible(not using_file)
        self.monitor_dropdown.setVisible(not using_file)
        self.monitor_dropdown.setEnabled(
            not using_file and not self.running and bool(self._capture_by_label)
        )
        if using_file and self.source_file is not None:
            self._show_selected_image_name()
        elif using_file:
            self.file_path_label.set_full_text(
                EMPTY_IMAGE_LABEL,
                EMPTY_IMAGE_TOOLTIP,
            )
        else:
            self.monitor_changed()
            return
        self.save_preferences()

    def _show_selected_image_name(self):

        if self.source_file is None:
            self.file_path_label.set_full_text(
                EMPTY_IMAGE_LABEL,
                EMPTY_IMAGE_TOOLTIP,
            )
            return
        self.file_path_label.set_full_text(
            self.source_file.name,
            str(self.source_file),
        )

    def update_note(self):
        if not self._model_by_label:
            return
        model = self.selected_model()
        effort = self.effort_dropdown.currentText()
        passes = self.selected_passes()
        cost = estimate_cost(model, passes, effort_label=effort)
        cost_text = f"${cost:.4f}" if cost < 0.01 else f"${cost:.2f}"
        effort_explanation = EFFORT_EXPLANATIONS.get(
            effort,
            "changes how carefully the AI checks the image",
        )
        self.note_label.setText(
            f"{effort} effort {effort_explanation}. This uses {passes} AI request"
            f"{'s' if passes != 1 else ''}. Estimated model cost: about {cost_text}."
        )
        provider = provider_by_id(self._current_provider_id)
        privacy_notice = model_privacy_notice(model)
        if privacy_notice:
            self.privacy_label.setText(
                "This model has special provider retention or privacy terms. "
                "The app asks for your confirmation before it can be used."
            )
            self.privacy_label.show()
        else:
            self.privacy_label.clear()
            self.privacy_label.hide()
        self.model_details_button.setToolTip(
            f"Read the full {provider.name} privacy note and {model.display_name} details."
        )

    def _update_adaptive_layout(self, force=False):
        if (
            self._updating_adaptive_layout
            or not hasattr(self, "page_layout")
            or not hasattr(self, "page_content")
        ):
            return

        narrow = self.width() < self.NORMAL_MINIMUM_WIDTH
        constrained = narrow or self.height() < self.NORMAL_MINIMUM_HEIGHT
        state = (narrow, constrained)
        title_compact = self.width() < 360
        if narrow or constrained:
            desired_map_minimum = 350
        else:
            effective_viewport_width = max(
                self.page_scroll.viewport().width(),
                self.width() - 2,
            )
            desired_map_minimum = max(
                350,
                min(
                    414,
                    effective_viewport_width - 18 - 18 - 14 - 390,
                ),
            )
        layout_key = (narrow, constrained, title_compact, desired_map_minimum)
        if not force and layout_key == self._adaptive_layout_key:
            return

        self._updating_adaptive_layout = True
        try:
            self._adaptive_compact = state
            if hasattr(self, "title_bar"):
                self.title_bar.set_compact(title_compact)

            if narrow:
                self.page_layout.setDirection(QBoxLayout.TopToBottom)
                self.page_layout.setContentsMargins(8, 8, 8, 10)
                self.page_layout.setSpacing(8)
                self.page_layout.setStretch(0, 0)
                self.page_layout.setStretch(1, 0)
                self.left_panel.setMinimumWidth(0)
                self.left_panel.setMaximumWidth(16777215)
                self.map_panel.setMinimumWidth(desired_map_minimum)
                self.left_tabs.setSizePolicy(
                    QSizePolicy.Ignored,
                    QSizePolicy.Expanding,
                )
                self.left_tabs.setElideMode(Qt.ElideRight)
            else:
                self.page_layout.setDirection(QBoxLayout.LeftToRight)
                self.page_layout.setContentsMargins(18, 16, 18, 18)
                self.page_layout.setSpacing(14)
                self.page_layout.setStretch(0, 0)
                self.page_layout.setStretch(1, 1)
                self.left_panel.setMinimumWidth(390)
                self.left_panel.setMaximumWidth(485)
                if constrained:
                    self.map_panel.setMinimumWidth(desired_map_minimum)
                else:
                    self.map_panel.setMinimumWidth(desired_map_minimum)
                self.left_tabs.setSizePolicy(
                    QSizePolicy.Expanding,
                    QSizePolicy.Expanding,
                )
                self.left_tabs.setElideMode(Qt.ElideNone)

            self.page_content.setMinimumSize(0, 0)
            self.page_content.setMaximumSize(16777215, 16777215)
            self.page_layout.invalidate()
            self.page_layout.activate()
            if constrained:
                self.page_content.setMinimumSize(self.page_layout.minimumSize())
            else:
                self.page_content.setMaximumSize(
                    max(1, self.width()),
                    max(1, self.height() - 44),
                )
            self.page_content.updateGeometry()
            self.page_scroll.updateGeometry()
            self._adaptive_layout_key = layout_key
        finally:
            self._updating_adaptive_layout = False

    def set_map_subhead(self, text: str):
        self._map_subhead_full = str(text or "")
        if hasattr(self, "map_subhead"):
            safe_tooltip = html.escape(self._map_subhead_full).replace("\n", "<br>")
            self.map_subhead.setToolTip(f"<qt>{safe_tooltip}</qt>")
            self._refresh_map_subhead()

    def _refresh_map_subhead(self):
        if not hasattr(self, "map_subhead"):
            return
        width = max(100, self.map_subhead.width() - 4)
        shown = self.map_subhead.fontMetrics().elidedText(
            self._map_subhead_full,
            Qt.ElideRight,
            width,
        )
        self.map_subhead.setText(shown)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_adaptive_layout()
        if hasattr(self, "size_grip") and hasattr(self, "window_frame"):
            adaptive_state = self._adaptive_compact or (False, False)
            self.size_grip.setVisible(
                not self.isMaximized() and not adaptive_state[1]
            )
            self.size_grip.move(
                max(0, self.window_frame.width() - self.size_grip.width() - 2),
                max(0, self.window_frame.height() - self.size_grip.height() - 2),
            )
            self.size_grip.raise_()
        self._refresh_map_subhead()

    def _confirm_pending_report(self, next_action: str) -> bool:
        if not self.save_results_enabled or not (
            self._report_needs_save and self.last_result is not None
        ):
            return True
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Unsaved location report")
        message.setText("This location result has not been saved yet.")
        message.setInformativeText(
            f"Save it before {next_action}, discard it, or cancel and keep it open."
        )
        message.setStandardButtons(
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        message.setDefaultButton(QMessageBox.Save)
        message.setEscapeButton(QMessageBox.Cancel)
        choice = message.exec()
        if choice == QMessageBox.Save:
            self.open_output_folder()
            return not self._report_needs_save
        return choice == QMessageBox.Discard

    def choose_file(self):
        start_folder = (
            str(self.source_file.parent)
            if self.source_file is not None
            else str(Path.home() / "Pictures")
        )
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image File",
            start_folder,
            "Image files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff);;All files (*.*)",
        )
        if filename:
            self.set_source_file(Path(filename))

    def set_source_file(self, path: Path):
        if self.running:
            self.append_log("Wait for the current analysis to finish before changing images.")
            return
        try:
            path = path.expanduser().resolve()
            file_info = path.stat()
        except (OSError, ValueError) as error:
            self.status_label.setText("Invalid file")
            self.append_log(f"Could not read that path: {error}")
            return
        if not stat.S_ISREG(file_info.st_mode) or path.suffix.lower() not in IMAGE_EXTENSIONS:
            self.status_label.setText("Choose an image file")
            self.append_log(
                "Choose a valid PNG, JPG, WEBP, BMP, GIF, or TIFF image."
            )
            return
        if file_info.st_size > MAX_IMAGE_BYTES:
            self.status_label.setText("Image is too large")
            self.append_log("Choose an image smaller than 20 MB.")
            return
        if not self._confirm_pending_report("choosing a different image"):
            self.status_label.setText("Unsaved report kept")
            return
        self.source_file = path
        self.source_dropdown.select("Image file")
        self._show_selected_image_name()
        self.output_file = None
        self.last_result = None
        self._last_report_context = None
        self._report_needs_save = False
        self.open_folder_button.setText("Open output")
        self.map_view.clear_location()
        self.set_map_subhead("World view - a pin appears after a result")
        self.open_folder_button.setEnabled(False)
        self.status_label.setText("Ready")
        self.append_log(f"Selected image: {path.name}")
        self.save_preferences()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Result Folder",
            str(self.output_folder),
        )
        if folder:
            try:
                selected_folder = Path(folder).expanduser().resolve()
                if not selected_folder.is_dir():
                    raise OSError("The selected folder is no longer available.")
            except (OSError, TypeError, ValueError) as error:
                self.status_label.setText("Choose an available result folder")
                self.append_log(f"Could not use that result folder: {error}")
                return
            self.output_folder = selected_folder
            self.output_path_label.set_full_text(str(self.output_folder))
            self.save_preferences()

    def save_api_key(self):
        provider = provider_by_id(self._current_provider_id)
        key = self.api_key_input.text().strip()
        self.api_key_input.setText(key)
        try:
            save_provider_key(self.settings, provider.id, key)
        except OSError:
            self.ai_status_label.setText("Could not protect this API key.")
            self.append_log(
                "The API key was not saved because protected settings "
                "could not be updated."
            )
            return
        self._pending_keys[provider.id] = key
        self.ai_status_label.setText(
            "API key saved securely." if key else "Saved API key cleared."
        )
        self.append_log(
            f"Saved the {provider.name} key with Windows per-user encryption."
            if key
            else f"Cleared the stored {provider.name} key."
        )

    def toggle_key_visibility(self):
        hidden = self.api_key_input.echoMode() == QLineEdit.Password
        self.api_key_input.setEchoMode(
            QLineEdit.Normal if hidden else QLineEdit.Password
        )
        self.show_key_button.setText("Hide" if hidden else "Show")

    def open_key_page(self):
        provider = provider_by_id(self._current_provider_id)
        QDesktopServices.openUrl(QUrl(provider.api_key_url))

    def find_or_cancel(self):
        if self.running:
            self.cancel_analysis()
        else:
            self.start_analysis()

    def start_analysis(self):
        provider = provider_by_id(self._current_provider_id)
        model = self.selected_model()
        api_key = self.api_key_input.text().strip()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.show_key_button.setText("Show")
        if not self._confirm_model_privacy(model):
            self.status_label.setText("Analysis cancelled")
            self.append_log(
                f"Cancelled before sending anything to {provider.name}."
            )
            return
        self._accepted_model_labels[provider.id] = self.model_dropdown.currentText()
        if not api_key:
            self.status_label.setText("Add an API key")
            self.append_log(
                f"Paste a {provider.name} API key, then press Save. "
                "Use Get key if you need the provider's key page."
            )
            return

        source_label = self.source_dropdown.currentText()
        from_screen = source_label == "Screen capture"
        if not from_screen and not source_file_is_available(self.source_file):
            self.status_label.setText("Choose an image")
            self.append_log("Choose an image file first.")
            return

        passes = self.selected_passes()
        effort = self.effort_dropdown.currentText()
        prompt_mode = self.prompt_dropdown.currentText()
        extra_guidance = self.extra_guidance_input.text().strip()[:1200]
        capture_target = None
        if from_screen:
            current_target = self.selected_capture_target()
            capture_target = self.refresh_capture_targets(
                current_target.id if current_target is not None else ""
            )
            if capture_target is None:
                self.status_label.setText("Choose an available monitor")
                return
            if capture_target.is_all:
                output_base = "all monitors screen capture"
            else:
                number = capture_target.display_number or 1
                output_base = f"monitor {number} screen capture"
            source_name = "Screen capture - " + capture_target.label
        else:
            output_base = self.source_file.stem
            source_name = self.source_file.name
        output_file = (
            self.output_folder / f"{output_base} location.txt"
            if self.save_results_enabled
            else None
        )
        if output_file is not None:
            try:
                self.output_folder.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=".ai-location-write-check-",
                    suffix=".tmp",
                    dir=self.output_folder,
                    delete=True,
                ) as writable_check:
                    writable_check.write(b"ok")
                    writable_check.flush()
            except OSError as error:
                self.status_label.setText("Choose a writable result folder")
                self.append_log(
                    "The selected result folder is not writable. Choose another folder "
                    f"before using paid AI requests: {error}"
                )
                return
            try:
                output_exists = output_file.exists()
            except (OSError, ValueError) as error:
                self.status_label.setText("Choose an available result folder")
                self.append_log(f"The result path could not be checked: {error}")
                return
            if output_exists:
                choice = QMessageBox.question(
                    self,
                    "Replace result?",
                    f"{output_file.name} already exists. Replace it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if choice != QMessageBox.Yes:
                    self.status_label.setText("Cancelled")
                    return
        if not self._confirm_pending_report("starting a new analysis"):
            self.status_label.setText("Unsaved report kept")
            return

        was_maximized = self.isMaximized()
        if from_screen:
            for dropdown in self.dropdowns:
                dropdown.hide_popup(immediate=True)
            self.hide()
            QApplication.processEvents()
            QThread.msleep(400)
        try:
            upload_profile = image_upload_profile(model, effort, passes)
            image = (
                capture_screen(capture_target.id)
                if from_screen
                else load_image_file(
                    self.source_file,
                    max_long_edge=upload_profile["max_long_edge"],
                    max_visual_tokens=upload_profile["max_visual_tokens"],
                )
            )
            image_data, media_type, width, height = encode_image(
                image,
                model=model,
                effort_label=effort,
                passes=passes,
            )
        except (AnalysisError, OSError, ScreenCaptureError) as error:
            if from_screen:
                self.showMaximized() if was_maximized else self.show()
                self.activateWindow()
            self.status_label.setText("Image preparation failed")
            self.append_log(str(error))
            return
        except Exception as error:
            if from_screen:
                self.showMaximized() if was_maximized else self.show()
                self.activateWindow()
            self.status_label.setText("Image preparation failed")
            self.append_log(f"The image could not be prepared: {error}")
            return
        if from_screen:
            self.showMaximized() if was_maximized else self.show()
            self.raise_()
            self.activateWindow()

        self.output_file = output_file
        self._last_report_context = {
            "source_name": source_name,
            "prompt_mode": prompt_mode,
            "model": model,
            "effort": effort,
            "requested": passes,
        }
        self._report_needs_save = False
        self.open_folder_button.setText("Open output")
        self.last_result = None
        self.last_log_message = ""
        self.log_box.clear()
        self.map_view.clear_location()
        self.set_map_subhead("Analyzing - the map is ready for the result")
        self.open_folder_button.setEnabled(False)
        rough_cost = estimate_cost(model, passes, effort_label=effort)
        rough_text = f"${rough_cost:.4f}" if rough_cost < 0.01 else f"${rough_cost:.2f}"
        self.append_log(f"Input: {source_name}")
        self.append_log(f"Mode: {prompt_mode}")
        self.append_log(f"Service: {provider.display_name}")
        self.append_log(f"Model: {model.display_name}")
        self.append_log(
            f"Prompt tuning: {prompt_profile_identifier(model)}; {prompt_mode}"
        )
        self.append_log(f"Effort and passes: {effort}, {passes}")
        self.append_log(
            f"Prepared image: {width} × {height} {media_type.split('/')[1].upper()}"
        )
        self.append_log(f"Rough model charge estimate: {rough_text}")
        self.append_log(
            f"Report: {output_file}"
            if output_file is not None
            else "Report saving: Off"
        )

        self.worker_thread = QThread(self)
        self.worker = AnalysisWorker(
            image_data,
            media_type,
            api_key,
            model,
            effort,
            passes,
            prompt_mode,
            extra_guidance,
            output_file,
            source_name,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.logged.connect(self.append_log)
        self.worker.result_ready.connect(self.show_location_result)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.thread_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.running = True
        self.find_button.setText("Cancel")
        self.status_label.setText("Finding the location...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(4)
        self.set_controls_enabled(False)
        try:
            self.worker_thread.start()
        except Exception as error:
            failed_worker = self.worker
            failed_thread = self.worker_thread

            if failed_worker is not None:
                failed_worker.cancel()
                failed_worker.clear_private_payload()
            thread_stopped = True
            if failed_thread is not None:
                failed_thread.requestInterruption()
                failed_thread.quit()
                thread_stopped = failed_thread.wait(1000)
            self.output_file = None
            self._last_report_context = None
            self._report_needs_save = False
            if not thread_stopped:
                self.find_button.setText("Stopping...")
                self.find_button.setEnabled(False)
                self.status_label.setText("Stopping after start failure")
                self.set_map_subhead("World view - stopping safely")
                self.append_log(
                    "The analysis worker reported a start failure after launching. "
                    "Waiting for it to stop safely."
                )
                return
            self.worker = None
            self.worker_thread = None
            self.running = False
            for qt_object in (failed_worker, failed_thread):
                if qt_object is not None:
                    try:
                        delete_qt_object(qt_object)
                    except RuntimeError:
                        pass

            self.find_button.setText("Find Location")
            self.find_button.setEnabled(True)
            self.set_controls_enabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("Analysis could not start")
            self.set_map_subhead("World view - analysis did not start")
            detail = str(error).strip()
            self.append_log(
                "Analysis could not start. No AI request was sent."
                + (f" {detail}" if detail else "")
            )

    def set_controls_enabled(self, enabled: bool):
        self.setAcceptDrops(enabled)
        self.left_tabs.tabBar().setEnabled(enabled)
        self.file_browse_button.setEnabled(
            enabled and self.source_dropdown.currentText() == "Image file"
        )
        self.save_result_toggle.setEnabled(enabled)
        self.output_browse_button.setEnabled(
            enabled and self.save_results_enabled
        )
        self.source_dropdown.setEnabled(enabled)
        self.monitor_dropdown.setEnabled(
            enabled
            and self.source_dropdown.currentText() == "Screen capture"
            and bool(self._capture_by_label)
        )
        self.prompt_dropdown.setEnabled(enabled)
        self.provider_dropdown.setEnabled(enabled)
        self.passes_dropdown.setEnabled(enabled)
        self.model_dropdown.setEnabled(enabled)
        self.effort_dropdown.setEnabled(enabled)
        self.extra_guidance_input.setEnabled(enabled)
        self.api_key_input.setEnabled(enabled)
        self.save_key_button.setEnabled(enabled)
        self.show_key_button.setEnabled(enabled)
        self.get_key_button.setEnabled(enabled)

    def cancel_analysis(self):
        if not self.running or self.worker is None:
            return
        self.status_label.setText("Stopping after the current API request...")
        self.find_button.setEnabled(False)
        self.worker.cancel()

    @Slot(int)
    def update_progress(self, value: int):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(100, value)))

    @Slot(object)
    def show_location_result(self, result):
        if result is None:
            return
        self.last_result = result
        self.append_log(f"LOCATION FOUND: {result.location}")
        self.append_log(
            f"Coordinates: {format_coordinate(result.latitude, True)}, "
            f"{format_coordinate(result.longitude, False)}"
        )
        self.append_log(
            f"AI-reported confidence: {result.confidence_percent:.0f}% with about a "
            f"{result.confidence_km:,.0f} km radius."
        )
        self.map_view.set_location(
            result.latitude,
            result.longitude,
            result.location,
            result.confidence_km,
        )
        self.set_map_subhead(
            f"{result.location} - {result.confidence_percent:.0f}% AI-reported confidence"
        )

    @Slot(str, str, object, object)
    def analysis_finished(self, state: str, message: str, result, stats):
        if isinstance(stats, AnalysisStats):
            analysis_stats = stats
        else:
            completed_value = max(0, int(stats or 0))
            requested_value = int(
                (self._last_report_context or {}).get(
                    "requested", completed_value
                )
            )
            analysis_stats = AnalysisStats(
                requested=max(requested_value, completed_value),
                attempted=completed_value,
                completed=completed_value,
                usable=completed_value if result is not None else 0,
            )
        self.progress_bar.setRange(0, 100)
        if state in ("success", "success_warning") and result is not None:
            self.progress_bar.setValue(100)
            self.status_label.setText(
                "Location found - save the report"
                if state == "success_warning"
                else "Done"
            )
            if self.last_result is not result:
                self.show_location_result(result)
            self.append_log(message)
            for clue in result.evidence[:3]:
                self.append_log(f"Evidence: {clue}")
            self.append_log("Finished successfully.")
            self._report_needs_save = (
                self.save_results_enabled and state == "success_warning"
            )
            self.open_folder_button.setText(
                "Save report" if self._report_needs_save else "Open output"
            )
            self.open_folder_button.setEnabled(
                self._report_needs_save or self.output_file is not None
            )
            if self._last_report_context is not None:
                self._last_report_context.update(
                    {
                        "attempted": analysis_stats.attempted,
                        "completed": analysis_stats.completed,
                        "usable": analysis_stats.usable,
                    }
                )
        elif state == "cancelled":
            self.progress_bar.setValue(0)
            self.status_label.setText("Cancelled")
            self.set_map_subhead("World view - analysis was cancelled")
            self.append_log(message)
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText("Analysis failed")
            self.set_map_subhead("World view - no usable result returned")
            self.append_log(message or "The analysis failed.")

    def thread_finished(self):
        self.running = False
        self.worker = None
        self.worker_thread = None
        self.find_button.setText("Find Location")
        self.find_button.setEnabled(True)
        self.set_controls_enabled(True)

    def clear_log(self):
        self.log_box.clear()
        self.last_log_message = ""
        if not self.running:
            self.status_label.setText("Ready")
            self.progress_bar.setValue(0)

    def append_log(self, message: str):
        message = str(message or "").strip()
        if not message or message == self.last_log_message:
            return
        self.last_log_message = message
        cursor = self.log_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        if not self.log_box.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(message)
        self.log_box.setTextCursor(cursor)
        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _choose_report_save_path(self, suggested: Path) -> str:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Location Report",
            str(suggested),
            "Text files (*.txt);;All files (*.*)",
            "",
            QFileDialog.Option.DontConfirmOverwrite,
        )
        return str(filename or "")

    def _confirm_report_overwrite(self, output: Path) -> bool:
        dialog = AppDialog("Replace existing report?", self)
        dialog.resize(440, 210)

        heading = QLabel("Replace existing report?")
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)
        dialog.content_layout.addWidget(heading)

        message = QLabel(
            f'"{output.name}" already exists. Replacing it cannot be undone.'
        )
        message.setObjectName("dialogBody")
        message.setTextFormat(Qt.PlainText)
        message.setWordWrap(True)
        dialog.content_layout.addWidget(message, 1)

        actions = QBoxLayout(QBoxLayout.LeftToRight)
        actions.addStretch(1)
        cancel_button = QPushButton("Cancel")
        replace_button = QPushButton("Replace")
        replace_button.setObjectName("primary")
        cancel_button.clicked.connect(dialog.reject)
        replace_button.clicked.connect(dialog.accept)
        cancel_button.setDefault(True)
        actions.addWidget(cancel_button)
        actions.addWidget(replace_button)
        dialog.content_layout.addLayout(actions)
        dialog.register_action_layout(actions)
        return dialog.exec() == QDialog.Accepted

    def open_output_folder(self):
        if self._report_needs_save and self.last_result is not None:
            suggested = self.output_folder / (
                self.output_file.name if self.output_file else "location result.txt"
            )
            filename = self._choose_report_save_path(suggested)
            if not filename:
                return
            try:
                output = Path(filename)
                if output.suffix.lower() != ".txt":
                    output = output.with_suffix(".txt")
                output = output.expanduser().resolve()
                output_exists = output.exists()
            except (OSError, TypeError, ValueError) as error:
                self.status_label.setText("Report still not saved")
                self.append_log(f"The report path could not be used: {error}")
                return
            if output_exists and not self._confirm_report_overwrite(output):
                self.status_label.setText("Report still not saved")
                self.append_log(
                    f"Save cancelled. Existing {output.name} was not changed."
                )
                return
            context = self._last_report_context or {}
            completed = int(context.get("completed", 1))
            attempted = int(context.get("attempted", completed))
            usable = int(context.get("usable", completed))
            try:
                write_report(
                    output,
                    self.last_result,
                    context.get("source_name", "Image"),
                    context.get("prompt_mode", self.prompt_dropdown.currentText()),
                    context.get("model", self.selected_model()),
                    context.get("effort", self.effort_dropdown.currentText()),
                    int(context.get("requested", completed)),
                    completed,
                    attempted,
                    usable,
                )
            except (AnalysisError, OSError) as error:
                self.status_label.setText("Report still not saved")
                self.append_log(str(error))
                return
            self.output_file = output.resolve()
            self.output_folder = self.output_file.parent
            self.output_path_label.set_full_text(str(self.output_folder))
            self._report_needs_save = False
            self.open_folder_button.setText("Open output")
            self.status_label.setText("Done")
            self.append_log(f"Saved {self.output_file.name}.")
            self.save_preferences()
            return
        folder = self.output_file.parent if self.output_file else self.output_folder
        try:
            folder_available = folder.is_dir()
        except (OSError, TypeError, ValueError):
            folder_available = False
        if not folder_available:
            self.status_label.setText("Output folder is unavailable")
            self.append_log("The output folder no longer exists. Choose another folder.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            self.status_label.setText("Could not open output folder")
            self.append_log("Windows could not open the output folder.")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.running:
            event.ignore()
            return
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if self.running:
            event.ignore()
            return
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                event.ignore()
                return
            self.set_source_file(path)
            event.acceptProposedAction()
            return
        event.ignore()

    def closeEvent(self, event: QCloseEvent):
        if self.running:
            QMessageBox.information(
                self,
                "Analysis in progress",
                "Cancel the analysis and wait for the current API request to finish before closing the app.",
            )
            event.ignore()
            return
        if not self._confirm_pending_report("closing the app"):
            self.status_label.setText("Unsaved report kept")
            event.ignore()
            return
        for dropdown in self.dropdowns:
            dropdown.hide_popup(immediate=True)
        self.save_preferences()
        event.accept()


def run_isolated_runtime_probe() -> None:
    runtime_python = Path(sys.executable).resolve()
    if not runtime_python.is_file():
        raise RuntimeError("The local Python executable was unavailable for the isolation test.")
    runtime_pythonw = runtime_python.with_name("pythonw.exe")
    if not runtime_pythonw.is_file():
        raise RuntimeError("The local windowless Python executable was unavailable for the isolation test.")
    private_packages = Path(sys.prefix).resolve() / "Lib" / "site-packages"
    if APP_DIR not in private_packages.parents or not private_packages.is_dir():
        raise RuntimeError("The private package folder was unavailable for the isolation test.")
    with tempfile.TemporaryDirectory(prefix="fleece-location-isolation-") as temporary:
        temporary_path = Path(temporary)
        injected_path = temporary_path / "injected"
        injected_path.mkdir()
        injection_marker = temporary_path / "injection-loaded.txt"
        (injected_path / "sitecustomize.py").write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['FLEECE_LOCATION_INJECTION_MARKER']).write_text('sitecustomize', encoding='utf-8')\n"
            "raise RuntimeError('PYTHONPATH sitecustomize injection was imported')\n",
            encoding="utf-8",
        )
        (injected_path / "httpx.py").write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['FLEECE_LOCATION_INJECTION_MARKER']).write_text('httpx', encoding='utf-8')\n"
            "raise RuntimeError('PYTHONPATH httpx injection was imported')\n",
            encoding="utf-8",
        )
        result_path = temporary_path / "result.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(injected_path)
        environment["FLEECE_LOCATION_INJECTION_MARKER"] = str(injection_marker)
        probe = (
            "import json, sys\n"
            "from pathlib import Path\n"
            "result_path=Path(sys.argv[1])\n"
            "injected=Path(sys.argv[2]).resolve()\n"
            "expected=Path(sys.argv[3]).resolve()\n"
            "private_packages=Path(sys.argv[4]).resolve()\n"
            "try:\n"
            "    import httpx, PySide6\n"
            "    httpx_module=Path(httpx.__file__).resolve()\n"
            "    pyside_module=Path(PySide6.__file__).resolve()\n"
            "    paths=[Path(value).resolve() for value in sys.path if value]\n"
            "    result={'isolated':sys.flags.isolated == 1, "
            "'private_executable':Path(sys.executable).resolve() == expected, "
            "'pythonpath_rejected':injected not in paths, "
            "'module_injection_rejected':injected not in httpx_module.parents, "
            "'private_httpx':private_packages in httpx_module.parents, "
            "'private_pyside':private_packages in pyside_module.parents}\n"
            "except BaseException as error:\n"
            "    result={'error':type(error).__name__}\n"
            "result_path.write_text(json.dumps(result), encoding='utf-8')\n"
            "raise SystemExit(1 if 'error' in result else 0)"
        )
        try:
            completed = subprocess.run(
                [
                    str(runtime_pythonw),
                    "-I",
                    "-c",
                    probe,
                    str(result_path),
                    str(injected_path),
                    str(runtime_pythonw),
                    str(private_packages),
                ],
                cwd=str(APP_DIR),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("The isolated windowless-runtime probe did not exit promptly.") from error
        except OSError as error:
            raise RuntimeError("The isolated windowless runtime could not start.") from error
        if injection_marker.exists():
            raise RuntimeError("The isolated private runtime loaded an injected PYTHONPATH module.")
        if not result_path.is_file():
            raise RuntimeError(
                f"The isolated windowless-runtime probe exited with code {completed.returncode} without a result."
            )
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("The isolated windowless-runtime probe wrote invalid output.") from error
        if "error" in result:
            error_name = result.get("error")
            if not isinstance(error_name, str) or not error_name.isidentifier():
                error_name = "unknown error"
            raise RuntimeError(
                f"The isolated windowless runtime could not load its private packages ({error_name})."
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"The isolated windowless-runtime probe exited with code {completed.returncode}."
            )
        expected_result = {
            "isolated": True,
            "private_executable": True,
            "pythonpath_rejected": True,
            "module_injection_rejected": True,
            "private_httpx": True,
            "private_pyside": True,
        }
        if result != expected_result:
            raise RuntimeError("The isolated windowless-runtime probe reported an unsafe launch state.")


def write_self_test_output(folder: Path, checks: list[str], label: str) -> int:
    output = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "passed": True,
        "network_requests": 0,
        "real_desktop_captures": 0,
        "providers": len(direct_providers()),
        "model_entries": len(MODELS),
        "checks": checks,
    }
    checks_path = folder / "checks.json"
    checks_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if not checks_path.is_file() or checks_path.stat().st_size < 100:
        raise RuntimeError("The verification result could not be saved.")
    print(f"{APP_NAME} {label} passed ({len(checks)} checks).")
    return 0


def run_install_check(folder: Path) -> int:
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    checks = []

    run_isolated_runtime_probe()
    checks.append("isolated windowless runtime uses private packages and rejects PYTHONPATH injection")

    if not provider_self_test():
        raise RuntimeError("The provider catalog install check did not complete.")
    checks.append(f"{len(MODELS)} curated direct-provider models and offline payloads")

    map_checks = run_map_self_test()
    if not verify_map_asset() or len(map_checks) < 8:
        raise RuntimeError("The offline map install check did not complete.")
    checks.append("detailed street, satellite, and offline map components")

    capture_checks = run_capture_self_tests(include_system_enumeration=False)
    if len(capture_checks) < 6:
        raise RuntimeError("The portable screen-capture install check did not complete.")
    checks.append("portable monitor geometry and cursor-free image encoding")

    prompt_checks = run_prompt_self_tests(MODELS)
    if len(prompt_checks) < 9:
        raise RuntimeError("The model prompt install check did not complete.")
    checks.append("model-specific privacy, safety, and structured-result prompts")

    sample = QImage(640, 360, QImage.Format_RGB32)
    sample.fill(QColor("#101010"))
    image_data, media_type, width, height = encode_image(sample)
    if not image_data or media_type not in {"image/png", "image/jpeg"} or width < 1 or height < 1:
        raise RuntimeError("The local image preparation install check did not complete.")
    checks.append("local image preparation and encoding")

    return write_self_test_output(folder, checks, "install check")


def run_self_test(folder: Path) -> int:
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    checks = []

    if PROVIDER_WARMUP_STARTED:
        raise RuntimeError("Diagnostic startup unexpectedly began provider warmup.")
    warmup_entered = threading.Event()
    warmup_release = threading.Event()
    warmup_calls = []

    def offline_warmup():
        warmup_calls.append("called")
        warmup_entered.set()
        warmup_release.wait(2.0)

    warmup_started_at = time.perf_counter()
    first_warmup_thread = start_provider_runtime_warmup(offline_warmup)
    second_warmup_thread = start_provider_runtime_warmup(offline_warmup)
    warmup_start_elapsed = time.perf_counter() - warmup_started_at
    if (
        first_warmup_thread is None
        or second_warmup_thread is not first_warmup_thread
        or warmup_start_elapsed > 0.1
        or not warmup_entered.wait(1.0)
    ):
        warmup_release.set()
        raise RuntimeError("Provider warmup blocked startup or ran more than once.")
    warmup_release.set()
    first_warmup_thread.join(1.0)
    if first_warmup_thread.is_alive() or warmup_calls != ["called"]:
        raise RuntimeError("Provider warmup did not finish exactly once.")
    checks.append("deferred key-free provider warmup is nonblocking and one-shot")

    run_isolated_runtime_probe()
    checks.append("isolated windowless runtime uses private packages and rejects PYTHONPATH injection")

    if not provider_self_test():
        raise RuntimeError("The provider catalog self-test did not complete.")
    checks.append(
        f"{len(MODELS)} curated direct-provider models and offline payloads"
    )

    map_checks = run_map_self_test()
    if not verify_map_asset() or len(map_checks) < 8:
        raise RuntimeError("The offline map self-test did not complete.")
    checks.append(
        "detailed street and satellite map, fixed controls, exact pin, and offline fallback"
    )

    capture_checks = run_capture_self_tests(include_system_enumeration=True)
    if len(capture_checks) < 4:
        raise RuntimeError("The selected-monitor capture self-test did not complete.")
    checks.append(
        "primary-monitor default, explicit all-monitor choice, and cursor-free capture contract"
    )

    if validated_input_image_dimensions(8000, 8000) != (8000, 8000):
        raise RuntimeError("The safe image pixel boundary was rejected.")
    for unsafe_dimensions in (
        (0, 1),
        (1, 0),
        (MAX_INPUT_IMAGE_PIXELS + 1, 1),
        (True, 1),
    ):
        try:
            validated_input_image_dimensions(*unsafe_dimensions)
        except AnalysisError:
            pass
        else:
            raise RuntimeError("An unsafe image dimension passed validation.")

    scaled_decode_fixture = folder / "scaled-decode-fixture.png"
    scaled_decode_source = QImage(2200, 8, QImage.Format_RGB32)
    scaled_decode_source.fill(QColor("#48627a"))
    if not scaled_decode_source.save(str(scaled_decode_fixture), "PNG"):
        raise RuntimeError("The scaled-decode fixture could not be created.")
    try:
        scaled_decode_result = load_image_file(
            scaled_decode_fixture,
            max_long_edge=1024,
        )
    finally:
        try:
            scaled_decode_fixture.unlink(missing_ok=True)
        except OSError:
            pass
    if (
        scaled_decode_result.isNull()
        or max(scaled_decode_result.width(), scaled_decode_result.height()) != 1024
    ):
        raise RuntimeError("File image scaling did not happen during bounded decode.")

    sample = QImage(4000, 1200, QImage.Format_RGB32)
    sample.fill(QColor("#101010"))
    prepared = scale_for_upload(sample)
    if max(prepared.width(), prepared.height()) != MAX_IMAGE_LONG_EDGE:
        raise RuntimeError("Oversized image scaling failed.")
    image_data, media_type, width, height = encode_image(sample)
    if not image_data or media_type not in {"image/png", "image/jpeg"}:
        raise RuntimeError("In-memory image encoding failed.")
    if max(width, height) != MAX_IMAGE_LONG_EDGE:
        raise RuntimeError("Encoded image dimensions are incorrect.")
    haiku = model_by_id("anthropic", "claude-haiku-4-5-20251001")
    haiku_sample = QImage(1920, 1080, QImage.Format_RGB32)
    haiku_sample.fill(QColor("#68788a"))
    haiku_sample.setText("Location", "private-metadata-probe")
    fast_data, fast_media, fast_width, fast_height = encode_image(
        haiku_sample,
        model=haiku,
        effort_label="Low",
        passes=1,
    )
    if fast_media not in {"image/webp", "image/jpeg"} or not fast_data:
        raise RuntimeError("Fast image encoding failed.")
    if max(fast_width, fast_height) > HAIKU_MAX_IMAGE_LONG_EDGE:
        raise RuntimeError("Haiku fast image edge scaling failed.")
    if image_visual_tokens(fast_width, fast_height) > HAIKU_MAX_VISUAL_TOKENS:
        raise RuntimeError("Haiku fast image token scaling failed.")
    if b"private-metadata-probe" in fast_data:
        raise RuntimeError("Image metadata was not removed before upload.")
    xai_fast_data, xai_fast_media, _, _ = encode_image(
        haiku_sample,
        model=default_model("xai"),
        effort_label="Low",
        passes=1,
    )
    if not xai_fast_data or xai_fast_media != "image/jpeg":
        raise RuntimeError("xAI fast image compatibility failed.")

    for catalog_model in MODELS:
        for effort_label in EFFORT_LABELS:
            previous_quality = 0
            for requested_passes in (1, 2, 3):
                profile = image_upload_profile(
                    catalog_model,
                    effort_label,
                    requested_passes,
                )
                expected_quality = min(
                    99,
                    UPLOAD_QUALITY_BY_EFFORT[effort_label]
                    + requested_passes
                    - 1,
                )
                if (
                    profile["quality"] != expected_quality
                    or profile["quality"] < previous_quality
                    or (
                        catalog_model.provider_id == "xai"
                        and profile["format"] != "JPEG"
                    )
                    or (
                        catalog_model.provider_id != "xai"
                        and profile["format"] != "WEBP"
                    )
                ):
                    raise RuntimeError("An image upload profile is inconsistent.")
                previous_quality = profile["quality"]
                is_haiku = catalog_model.id == "claude-haiku-4-5-20251001"
                if is_haiku and (
                    profile["max_long_edge"] != HAIKU_MAX_IMAGE_LONG_EDGE
                    or profile["max_visual_tokens"] != HAIKU_MAX_VISUAL_TOKENS
                ):
                    raise RuntimeError("A Haiku setting lost its upload limits.")
                if not is_haiku and (
                    profile["max_long_edge"]
                    != MAX_IMAGE_LONG_EDGE_BY_EFFORT[effort_label]
                    or profile["max_visual_tokens"] is not None
                ):
                    raise RuntimeError(
                        "A non-Haiku setting lost its effort-aware image limit."
                    )

    deep_data, deep_media, deep_width, deep_height = encode_image(
        haiku_sample,
        model=haiku,
        effort_label="Ultra",
        passes=3,
    )
    if (
        not deep_data
        or deep_media != "image/webp"
        or max(deep_width, deep_height) > HAIKU_MAX_IMAGE_LONG_EDGE
        or image_visual_tokens(deep_width, deep_height) > HAIKU_MAX_VISUAL_TOKENS
        or b"private-metadata-probe" in deep_data
    ):
        raise RuntimeError("Deep Haiku image preparation was not bounded or private.")

    quality_sample = QImage(384, 216, QImage.Format_RGB32)
    quality_painter = QPainter(quality_sample)
    for x in range(quality_sample.width()):
        quality_painter.fillRect(
            x,
            0,
            1,
            quality_sample.height(),
            QColor(
                24 + (x * 151 // quality_sample.width()),
                42 + (x * 119 // quality_sample.width()),
                68 + (x * 91 // quality_sample.width()),
            ),
        )
    for index in range(42):
        quality_painter.setPen(
            QPen(
                QColor(
                    (index * 47) % 256,
                    (index * 79) % 256,
                    (index * 113) % 256,
                ),
                1 + index % 3,
            )
        )
        x = (index * 61) % quality_sample.width()
        y = (index * 37) % quality_sample.height()
        quality_painter.drawLine(
            x,
            0,
            quality_sample.width() - 1 - x,
            quality_sample.height() - 1,
        )
        quality_painter.drawRect(x, y, 18 + index % 40, 10 + index % 24)
    quality_painter.setPen(QColor("#ffffff"))
    for index in range(8):
        quality_painter.drawText(
            12 + (index % 4) * 92,
            28 + (index // 4) * 108,
            f"ROAD A{index + 1} NORTH",
        )
    quality_painter.end()
    quality_sample.setText("Private", "metadata-quality-probe")

    def encoded_quality_metrics(reference: QImage, encoded: bytes):
        decoded = QImage.fromData(encoded)
        if decoded.isNull() or decoded.size() != reference.size():
            raise RuntimeError("An encoded quality fixture could not be decoded.")
        squared_error = 0
        channel_count = 0
        source_edges = 0
        decoded_edges = 0
        for y in range(reference.height()):
            previous_source = None
            previous_decoded = None
            for x in range(reference.width()):
                source_color = reference.pixelColor(x, y)
                decoded_color = decoded.pixelColor(x, y)
                for source_value, decoded_value in (
                    (source_color.red(), decoded_color.red()),
                    (source_color.green(), decoded_color.green()),
                    (source_color.blue(), decoded_color.blue()),
                ):
                    squared_error += (source_value - decoded_value) ** 2
                    channel_count += 1
                source_luma = (
                    source_color.red() * 299
                    + source_color.green() * 587
                    + source_color.blue() * 114
                ) // 1000
                decoded_luma = (
                    decoded_color.red() * 299
                    + decoded_color.green() * 587
                    + decoded_color.blue() * 114
                ) // 1000
                if (
                    previous_source is not None
                    and abs(source_luma - previous_source) >= 40
                ):
                    source_edges += abs(source_luma - previous_source)
                    decoded_edges += abs(decoded_luma - previous_decoded)
                previous_source = source_luma
                previous_decoded = decoded_luma
        mean_squared_error = squared_error / max(1, channel_count)
        psnr = (
            99.0
            if mean_squared_error == 0
            else 10.0 * math.log10((255.0**2) / mean_squared_error)
        )
        return psnr, decoded_edges / max(1, source_edges)

    representative_settings = (
        ("Low", 1),
        ("Medium", 2),
        ("High", 3),
        ("Ultra", 3),
    )
    for provider_id in DIRECT_PROVIDER_ORDER:
        representative_model = default_model(provider_id)
        for effort_label, requested_passes in representative_settings:
            encoded, encoded_media, _, _ = encode_image(
                quality_sample,
                model=representative_model,
                effort_label=effort_label,
                passes=requested_passes,
            )
            expected_media = (
                "image/jpeg" if provider_id == "xai" else "image/webp"
            )
            psnr, edge_ratio = encoded_quality_metrics(quality_sample, encoded)
            if (
                not encoded
                or encoded_media != expected_media
                or b"metadata-quality-probe" in encoded
                or psnr < 21.5
                or edge_ratio < 0.82
            ):
                raise RuntimeError(
                    "An all-setting image encode lost privacy, fidelity, or compatibility."
                )
    checks.append(
        "safe header validation, scaled file decode, and all-setting metadata-free "
        "encoding with effort-aware image limits and quality floors"
    )

    prompt_checks = run_prompt_self_tests(MODELS)
    if len(prompt_checks) < 9:
        raise RuntimeError("The per-model prompt self-test did not complete.")
    openai_model = model_by_id("openai", "gpt-5.6-sol")
    claude_model = model_by_id("anthropic", "claude-opus-5")
    geoguessr_prompt = build_analysis_prompt(
        openai_model,
        "GeoGuessr screenshot",
        "Ultra",
        3,
        3,
        [],
        "Check Norway carefully",
    )
    normal_prompt = build_analysis_prompt(
        claude_model,
        "Regular photo or screenshot",
        "Low",
        1,
        1,
        [],
        "",
    )
    if geoguessr_prompt == normal_prompt:
        raise RuntimeError("Model-specific image modes reused the same prompt.")
    if prompt_profile_identifier(openai_model) == prompt_profile_identifier(claude_model):
        raise RuntimeError("Different AI families reused the same prompt profile.")
    checks.append(
        f"{len(MODELS)}-model prompt coverage with separate regular and GeoGuessr tuning"
    )

    sample_payload = {
        "found": True,
        "location": "Bergen \u2014 Vestland, Norway",
        "country": "Norway",
        "region": "Vestland",
        "city": "Bergen",
        "latitude": 60.3913,
        "longitude": 5.3221,
        "confidence_km": 12,
        "confidence_percent": 82,
        "evidence": [
            "Mountainous \u2013 coastal terrain matches western Norway.",
            "Architecture and road design are consistent with Bergen.",
        ],
        "alternatives": [
            {
                "location": "Stavanger, Norway",
                "latitude": 58.97,
                "longitude": 5.73,
                "reason": "Similar west-coast terrain \u2014 and construction.",
            }
        ],
        "error": "",
    }
    result = result_from_payload(sample_payload)
    if result.location != "Bergen - Vestland, Norway" or result.confidence_percent != 82:
        raise RuntimeError("Structured location parsing failed.")
    result_text = " ".join(
        [result.location, *result.evidence]
        + [item.get("reason", "") for item in result.alternatives]
    )
    if "\u2013" in result_text or "\u2014" in result_text:
        raise RuntimeError("AI-returned dash characters were not normalized.")
    try:
        result_from_payload({**sample_payload, "latitude": 200})
    except AnalysisError:
        pass
    else:
        raise RuntimeError("Invalid coordinates were accepted.")
    checks.append("structured result parsing, calibration, evidence, and alternatives")

    original_model_call = globals()["call_vision_model"]
    seed_barrier = threading.Barrier(2)
    orchestration_lock = threading.Lock()
    active_calls = 0
    maximum_active_calls = 0
    prepared_image_ids = []
    orchestration_prompts = []
    repeated_cache_flags = []

    def concurrent_model_call(*args, **kwargs):
        nonlocal active_calls, maximum_active_calls
        prompt = args[4]
        with orchestration_lock:
            active_calls += 1
            maximum_active_calls = max(maximum_active_calls, active_calls)
            prepared_image_ids.append(id(args[2]))
            orchestration_prompts.append(prompt)
            repeated_cache_flags.append(kwargs.get("cache_repeated_input"))
        try:
            if "Pass 1 of 3" in prompt:
                seed_barrier.wait(2.0)
                return {
                    "found": False,
                    "error": "First independent seed was inconclusive.",
                }
            if "Pass 2 of 3" in prompt:
                seed_barrier.wait(2.0)
                return {
                    **sample_payload,
                    "location": "Oslo, Norway",
                    "city": "Oslo",
                    "region": "Oslo",
                    "latitude": 59.9139,
                    "longitude": 10.7522,
                }
            return dict(sample_payload)
        finally:
            with orchestration_lock:
                active_calls -= 1

    orchestration_log = []
    globals()["call_vision_model"] = concurrent_model_call
    try:
        recovered_result, _, recovery_stats = analyse_image(
            b"offline-self-test-image",
            "image/png",
            "not-a-real-key",
            default_model(direct_providers()[0].id),
            "Medium",
            3,
            "Regular photo or screenshot",
            "",
            log_callback=orchestration_log.append,
        )
    finally:
        globals()["call_vision_model"] = original_model_call
    if recovered_result.location != result.location:
        raise RuntimeError("A later usable AI check did not recover the result.")
    if (
        recovery_stats.attempted,
        recovery_stats.completed,
        recovery_stats.usable,
    ) != (3, 3, 2):
        raise RuntimeError("AI-check attempt/completion tracking is incorrect.")
    final_prompts = [
        prompt for prompt in orchestration_prompts if "Pass 3 of 3" in prompt
    ]
    if (
        maximum_active_calls != 2
        or active_calls != 0
        or len(prepared_image_ids) != 3
        or len(set(prepared_image_ids)) != 1
        or repeated_cache_flags != [True, True, True]
        or len(final_prompts) != 1
        or "Oslo" not in final_prompts[0]
        or not any(
            "independent contrarian seed" in prompt
            for prompt in orchestration_prompts
        )
        or sum("API call completed" in message for message in orchestration_log) != 3
        or not any("Total analysis time:" in message for message in orchestration_log)
    ):
        raise RuntimeError("Three-check parallel orchestration is incorrect.")

    sequential_clock = [0.0]
    sequential_active = 0
    sequential_maximum_active = 0
    sequential_prompts = []
    sequential_prepared_ids = []
    sequential_log = []

    def sequential_model_call(*args, **kwargs):
        nonlocal sequential_active, sequential_maximum_active
        sequential_active += 1
        sequential_maximum_active = max(
            sequential_maximum_active,
            sequential_active,
        )
        sequential_prompts.append(args[4])
        sequential_prepared_ids.append(id(args[2]))
        sequential_clock[0] += 0.4 if len(sequential_prompts) == 1 else 0.6
        sequential_active -= 1
        return dict(sample_payload)

    globals()["call_vision_model"] = sequential_model_call
    try:
        _, _, sequential_stats = analyse_image(
            b"offline-sequential-image",
            "image/png",
            "not-a-real-key",
            default_model("openai"),
            "Medium",
            2,
            "Regular photo or screenshot",
            "",
            log_callback=sequential_log.append,
            clock_callback=lambda: sequential_clock[0],
        )
    finally:
        globals()["call_vision_model"] = original_model_call
    if (
        sequential_maximum_active != 1
        or sequential_active != 0
        or len(set(sequential_prepared_ids)) != 1
        or len(sequential_prompts) != 2
        or "Bergen" not in sequential_prompts[1]
        or (
            sequential_stats.attempted,
            sequential_stats.completed,
            sequential_stats.usable,
        )
        != (2, 2, 2)
        or not any(
            "Pass 1 API call completed in 0.4 seconds." == message
            for message in sequential_log
        )
        or not any(
            "Pass 2 API call completed in 0.6 seconds." == message
            for message in sequential_log
        )
        or not any(
            "Total analysis time: 1.0 seconds." == message
            for message in sequential_log
        )
    ):
        raise RuntimeError("Two-check sequential review or timing is incorrect.")

    cancellation_started = threading.Event()
    cancellation_event = threading.Event()
    cancellation_lock = threading.Lock()
    cancellation_active = 0
    cancellation_started_count = 0
    cancellation_stats = AnalysisStats(3)
    cancellation_errors = []

    def cancelled_model_call(*args, **kwargs):
        nonlocal cancellation_active, cancellation_started_count
        del args
        with cancellation_lock:
            cancellation_active += 1
            cancellation_started_count += 1
            if cancellation_started_count == 2:
                cancellation_started.set()
        try:
            deadline = time.monotonic() + 2.0
            while not kwargs["cancel_event"].is_set() and time.monotonic() < deadline:
                time.sleep(0.002)
            raise ProviderRequestError("Analysis was cancelled.", "cancelled")
        finally:
            with cancellation_lock:
                cancellation_active -= 1

    def run_cancelled_analysis():
        try:
            analyse_image(
                b"offline-cancellation-image",
                "image/png",
                "not-a-real-key",
                default_model("google"),
                "High",
                3,
                "GeoGuessr screenshot",
                "",
                cancel_event=cancellation_event,
                stats=cancellation_stats,
            )
        except Exception as error:
            cancellation_errors.append(error)

    globals()["call_vision_model"] = cancelled_model_call
    cancellation_thread = threading.Thread(target=run_cancelled_analysis)
    cancellation_thread.start()
    if not cancellation_started.wait(1.0):
        cancellation_event.set()
        cancellation_thread.join(2.0)
        globals()["call_vision_model"] = original_model_call
        raise RuntimeError("Both independent cancellation fixtures did not start.")
    cancellation_event.set()
    cancellation_thread.join(2.0)
    globals()["call_vision_model"] = original_model_call
    if (
        cancellation_thread.is_alive()
        or cancellation_active != 0
        or len(cancellation_errors) != 1
        or not isinstance(cancellation_errors[0], AnalysisCancelled)
        or (cancellation_stats.attempted, cancellation_stats.completed)
        != (2, 0)
    ):
        raise RuntimeError("Parallel cancellation left work running or bad stats.")
    checks.append(
        "parallel independent seeds, sequential review, reused image, timing, and clean cancellation"
    )

    for rejected_category in ("request_configuration", "request"):
        rejected_attempts = []
        rejected_log = []
        rejection_barrier = threading.Barrier(2)
        rejection_lock = threading.Lock()

        def rejected_model_call(*args, **kwargs):
            del args, kwargs
            with rejection_lock:
                rejected_attempts.append(rejected_category)
            try:
                rejection_barrier.wait(1.0)
            except threading.BrokenBarrierError:
                pass
            raise ProviderRequestError(
                "The provider rejected this deterministic test request.",
                rejected_category,
                status_code=400,
            )

        globals()["call_vision_model"] = rejected_model_call
        try:
            try:
                analyse_image(
                    b"offline-self-test-image",
                    "image/png",
                    "not-a-real-key",
                    default_model(direct_providers()[0].id),
                    "Ultra",
                    3,
                    "Regular photo or screenshot",
                    "",
                    log_callback=rejected_log.append,
                )
            except AnalysisError:
                pass
            else:
                raise RuntimeError(
                    "A deterministic provider rejection was treated as usable."
                )
        finally:
            globals()["call_vision_model"] = original_model_call
        if not 1 <= len(rejected_attempts) <= 2 or any(
            "Pass 3 of 3" in message for message in rejected_log
        ):
            raise RuntimeError(
                "A deterministic provider rejection launched final adjudication."
            )
    checks.append("deterministic provider rejections stop before final adjudication")

    if APP_MUTEX_NAMES != (
        r"Global\FleeceAILocationFinderApp",
        r"Local\FleeceAILocationFinderApp",
    ) or APP_MUTEX_NAME not in APP_MUTEX_NAMES:
        raise RuntimeError("The app/installer mutex contract changed.")
    if SETUP_LOCK_DIR != RUNTIME_DIR / "setup.lock":
        raise RuntimeError("The setup-lock contract changed.")
    checks.append("single-instance app and setup lock contract")

    if NATIVE_KERNEL32 is not None:
        test_mutex_name = (
            rf"Local\FleeceAILocationFinderSelfTest-{os.getpid()}-{threading.get_ident()}"
        )
        first_status, first_handle = _try_create_named_mutex(test_mutex_name)
        try:
            second_status, second_handle = _try_create_named_mutex(test_mutex_name)
            if second_handle:
                NATIVE_KERNEL32.CloseHandle(second_handle)
            if first_status != "acquired" or not first_handle or second_status != "exists":
                raise RuntimeError("The app-instance mutex did not reject a duplicate.")
        finally:
            if first_handle:
                NATIVE_KERNEL32.CloseHandle(first_handle)
    checks.append("duplicate app-instance mutex is rejected")

    with tempfile.TemporaryDirectory(prefix="fleece-location-self-test-") as temporary:
        temporary_path = Path(temporary)
        settings_path = temporary_path / "settings.ini"
        settings = QSettings(str(settings_path), QSettings.IniFormat)
        save_provider_key(settings, "xai", "synthetic-x-provider-fixture-1-not-a-key")
        save_provider_key(settings, "openai", "synthetic-openai-fixture-2-not-a-key")
        save_extra_guidance(settings, "private self-test clue")
        settings.sync()
        reopened = QSettings(str(settings_path), QSettings.IniFormat)
        xai_key, xai_migrated = load_saved_provider_key(reopened, "xai")
        openai_key, openai_migrated = load_saved_provider_key(reopened, "openai")
        if xai_key != "synthetic-x-provider-fixture-1-not-a-key" or openai_key != "synthetic-openai-fixture-2-not-a-key":
            raise RuntimeError("Protected per-service key round-trip failed.")
        if xai_migrated or openai_migrated:
            raise RuntimeError("A current provider key was treated as legacy data.")
        if load_saved_extra_guidance(reopened) != "private self-test clue":
            raise RuntimeError("Protected extra-guidance round-trip failed.")
        xai_protected = str(
            reopened.value(_provider_key_setting("xai"), "") or ""
        )
        openai_protected = str(
            reopened.value(_provider_key_setting("openai"), "") or ""
        )
        guidance_protected = str(
            reopened.value("extra_guidance_protected", "") or ""
        )
        if not all(
            value.startswith(PROTECTED_SECRET_PREFIX)
            for value in (xai_protected, openai_protected, guidance_protected)
        ):
            raise RuntimeError("A protected preference lacks the current format marker.")
        readable_settings = settings_path.read_bytes()
        if any(
            secret in readable_settings
            for secret in (
                b"synthetic-x-provider-fixture-1-not-a-key",
                b"synthetic-openai-fixture-2-not-a-key",
                b"private self-test clue",
            )
        ):
            raise RuntimeError("A protected preference was stored as readable text.")

        swapped_path = temporary_path / "provider-swap.ini"
        swapped = QSettings(str(swapped_path), QSettings.IniFormat)
        swapped.setValue(_provider_key_setting("openai"), xai_protected)
        swapped.sync()
        try:
            load_saved_provider_key(swapped, "openai")
        except OSError as error:
            error_text = str(error)
            if "synthetic-x-provider-fixture-1-not-a-key" in error_text or xai_protected in error_text:
                raise RuntimeError("A provider-bound decrypt error exposed key material.")
        else:
            raise RuntimeError("A protected key could be moved to another provider.")

        corrupt_path = temporary_path / "corrupt.ini"
        corrupt = QSettings(str(corrupt_path), QSettings.IniFormat)
        corrupt_value = PROTECTED_SECRET_PREFIX + "not-valid-base64!"
        corrupt.setValue(_provider_key_setting("google"), corrupt_value)
        corrupt.sync()
        try:
            load_saved_provider_key(corrupt, "google")
        except OSError as error:
            if corrupt_value in str(error):
                raise RuntimeError("A corrupt protected value leaked through an error.")
        else:
            raise RuntimeError("Corrupt protected key data was accepted.")
        if str(corrupt.value(_provider_key_setting("google"), "")) != corrupt_value:
            raise RuntimeError("Corrupt key data was silently deleted.")

        markerless_path = temporary_path / "markerless.ini"
        markerless = QSettings(str(markerless_path), QSettings.IniFormat)
        markerless_secret = "synthetic-markerless-secret-check-not-used"
        markerless_value = PROTECTED_SECRET_PREFIX + base64.b64encode(
            _protect_dpapi_payload(
                markerless_secret,
                _secret_entropy(_provider_key_purpose("google")),
            )
        ).decode("ascii")
        markerless.setValue(_provider_key_setting("google"), markerless_value)
        markerless.sync()
        try:
            load_saved_provider_key(markerless, "google")
        except OSError as error:
            if markerless_secret in str(error) or markerless_value in str(error):
                raise RuntimeError("A malformed cleartext envelope leaked in an error.")
        else:
            raise RuntimeError("A protected value without its plaintext marker was accepted.")

        legacy_bound_path = temporary_path / "legacy-provider-ciphertext.ini"
        legacy_bound = QSettings(
            str(legacy_bound_path),
            QSettings.IniFormat,
        )
        legacy_bound_secret = "synthetic-x-provider-fixture-3-not-a-key"
        legacy_bound_value = base64.b64encode(
            _protect_dpapi_payload(legacy_bound_secret, None)
        ).decode("ascii")
        legacy_bound.setValue(
            _provider_key_setting("xai"),
            legacy_bound_value,
        )
        legacy_bound.sync()
        upgraded_key, single_key_migration = load_saved_provider_key(
            legacy_bound,
            "xai",
        )
        upgraded_value = str(
            legacy_bound.value(_provider_key_setting("xai"), "") or ""
        )
        if (
            upgraded_key != legacy_bound_secret
            or single_key_migration
            or not upgraded_value.startswith(PROTECTED_SECRET_PREFIX)
            or upgraded_value == legacy_bound_value
        ):
            raise RuntimeError("Legacy provider ciphertext was not upgraded safely.")

        try:
            save_provider_key(settings, "openrouter", "synthetic-rejected-key")
        except ValueError:
            pass
        else:
            raise RuntimeError("An unknown provider received a key setting.")

        legacy_path = temporary_path / "legacy.ini"
        legacy = QSettings(str(legacy_path), QSettings.IniFormat)
        legacy_anthropic_fixture = "sk" + "-ant-synthetic-fixture-not-a-key"
        legacy.setValue("api_key", legacy_anthropic_fixture)
        legacy.sync()
        migrated_key, migrated = load_saved_provider_key(legacy, "anthropic")
        if migrated_key != legacy_anthropic_fixture or not migrated:
            raise RuntimeError("Legacy Anthropic key migration failed.")
        if legacy_anthropic_fixture.encode("ascii") in legacy_path.read_bytes():
            raise RuntimeError("The migrated legacy API key remained readable.")

        obsolete_path = temporary_path / "obsolete-openrouter.ini"
        obsolete = QSettings(str(obsolete_path), QSettings.IniFormat)
        obsolete.setValue("provider", "openrouter")
        obsolete.setValue("api_key", "synthetic-openai-fixture-5-not-a-key")
        obsolete.sync()
        obsolete_key, obsolete_migrated = load_saved_provider_key(
            obsolete,
            "anthropic",
        )
        obsolete.sync()
        if obsolete_key or obsolete_migrated:
            raise RuntimeError("An obsolete OpenRouter key migrated into Anthropic.")
        if obsolete.value(_provider_key_setting("anthropic"), ""):
            raise RuntimeError("An obsolete key was stored under Anthropic.")
        obsolete_bytes = obsolete_path.read_bytes()
        if b"synthetic-openai-fixture-5-not-a-key" in obsolete_bytes:
            raise RuntimeError("An obsolete plaintext provider key was not removed.")

        worker_key = "synthetic-worker-secret-check-not-used"
        worker_logs = []
        worker_finishes = []
        original_analysis = globals()["analyse_image"]

        def offline_secret_failure(*args, **kwargs):
            log_callback = args[9] if len(args) > 9 else kwargs["log"]
            log_callback("Provider diagnostic included " + worker_key)
            raise AnalysisError("Provider rejected " + worker_key)

        globals()["analyse_image"] = offline_secret_failure
        worker = AnalysisWorker(
            b"offline-secret-redaction-image",
            "image/png",
            worker_key,
            default_model(direct_providers()[0].id),
            "Medium",
            1,
            "Regular photo or screenshot",
            "",
            None,
            "offline image.png",
        )
        worker.logged.connect(worker_logs.append)
        worker.finished.connect(
            lambda status, message, result_value, stats: worker_finishes.append(
                (status, message, result_value, stats)
            )
        )
        try:
            worker.run()
        finally:
            globals()["analyse_image"] = original_analysis
        emitted_worker_text = "\n".join(worker_logs) + "\n" + "\n".join(
            entry[1] for entry in worker_finishes
        )
        if (
            worker_key in emitted_worker_text
            or worker.api_key
            or worker.extra_guidance
            or worker.image_data
        ):
            raise RuntimeError("A finished worker retained or emitted private inputs.")
        if (
            REDACTED_SECRET not in emitted_worker_text
            or not worker_finishes
            or worker_finishes[-1][0] != "failed"
        ):
            raise RuntimeError("Worker key redaction did not preserve safe diagnostics.")
        checks.append(
            "purpose-bound DPAPI keys, guidance, migration, corruption handling, and log redaction"
        )

        report_path = temporary_path / "result.txt"
        model = default_model(direct_providers()[0].id)
        write_report(
            report_path,
            result,
            r"C:\Users\Private Person\Pictures\synthetic self-test image.png",
            "GeoGuessr screenshot",
            model,
            "High",
            3,
            3,
            3,
            2,
        )
        report = report_path.read_text(encoding="utf-8")
        if (
            "Bergen" not in report
            or "Evidence:" not in report
            or "3 attempted / 3 completed / 2 usable / 3 requested" not in report
        ):
            raise RuntimeError("The local result report is incomplete.")
        if "Private Person" in report or "synthetic self-test image.png" not in report:
            raise RuntimeError("The report exposed a private source path.")
        if "\u2013" in report or "\u2014" in report:
            raise RuntimeError("The report reintroduced an en dash or em dash.")

        failed_report_path = temporary_path / "failed-report.txt"
        original_fdopen = os.fdopen
        original_os_close = os.close
        closed_descriptors = []

        def failing_fdopen(*args, **kwargs):
            del args, kwargs
            raise OSError("synthetic fdopen failure")

        def tracked_os_close(descriptor):
            closed_descriptors.append(descriptor)
            return original_os_close(descriptor)

        os.fdopen = failing_fdopen
        os.close = tracked_os_close
        try:
            try:
                write_report(
                    failed_report_path,
                    result,
                    "offline.png",
                    "Regular photo or screenshot",
                    model,
                    "Low",
                    1,
                    1,
                    1,
                    1,
                )
            except AnalysisError:
                pass
            else:
                raise RuntimeError("A failed report descriptor open was accepted.")
        finally:
            os.fdopen = original_fdopen
            os.close = original_os_close
        leftover_failed_reports = list(
            temporary_path.glob(f".{failed_report_path.name}.*.tmp")
        )
        if (
            len(closed_descriptors) != 1
            or failed_report_path.exists()
            or leftover_failed_reports
        ):
            raise RuntimeError("A failed atomic report leaked a descriptor or temp file.")
        checks.append("atomic local report without private input-folder paths")

        save_off_startup_settings = temporary_path / "save-off-startup.ini"
        save_off_settings = QSettings(
            str(save_off_startup_settings),
            QSettings.IniFormat,
        )
        untouched_output_folder = Path(r"Z:\Fleece-Save-Off-Must-Not-Touch")
        save_off_settings.setValue("save_results_enabled", False)
        save_off_settings.setValue("output_folder", str(untouched_output_folder))
        save_off_settings.sync()
        original_path_is_dir = Path.is_dir
        touched_disabled_folder = []

        def guarded_path_is_dir(candidate):
            if candidate == untouched_output_folder:
                touched_disabled_folder.append(candidate)
                raise RuntimeError("Disabled report folder was touched.")
            return original_path_is_dir(candidate)

        Path.is_dir = guarded_path_is_dir
        save_off_window = None
        try:
            save_off_window = LocationFinder(
                settings_path=save_off_startup_settings,
                testing=True,
            )
        finally:
            Path.is_dir = original_path_is_dir
        if (
            touched_disabled_folder
            or save_off_window.save_results_enabled
            or save_off_window.output_folder != untouched_output_folder
        ):
            raise RuntimeError("Persisted Save Off touched its report folder at startup.")
        save_off_window.close()
        save_off_window.deleteLater()

        legacy_model_path = temporary_path / "legacy-model-selection.ini"
        legacy_model_settings = QSettings(
            str(legacy_model_path),
            QSettings.IniFormat,
        )
        legacy_model_settings.setValue("provider", "xai")
        legacy_model_settings.setValue("models/xai", "grok-4.5")
        legacy_model_settings.sync()
        legacy_model_window = LocationFinder(
            settings_path=legacy_model_path,
            testing=True,
        )
        expected_xai_default = default_model("xai")
        migrated_model_id = str(
            legacy_model_window.settings.value("models/xai", "") or ""
        )
        if (
            legacy_model_window.selected_model().id != expected_xai_default.id
            or migrated_model_id != expected_xai_default.id
        ):
            raise RuntimeError("A retired saved model was not migrated to its replacement.")
        legacy_model_window.close()
        legacy_model_window.deleteLater()

        ui_settings = temporary_path / "ui.ini"
        stale_map_settings = QSettings(str(ui_settings), QSettings.IniFormat)
        stale_map_settings.setValue("map/layer", "satellite")
        stale_map_settings.sync()
        window = LocationFinder(settings_path=ui_settings, testing=True)
        available = QApplication.primaryScreen().availableGeometry()
        initial_size = window.size()
        if (
            initial_size.width() > available.width()
            or initial_size.height() > available.height()
        ):
            raise RuntimeError("Initial window geometry exceeded the logical desktop.")
        window.resize(860, 520)
        window.show()
        QApplication.processEvents()

        traffic_buttons = {
            button.objectName(): button
            for button in window.findChildren(TrafficLightButton)
        }
        expected_traffic_geometry = {
            "maximizeDot": (0, 6, 28, 28),
            "minimizeDot": (28, 6, 28, 28),
            "closeDot": (56, 6, 28, 28),
        }
        if set(traffic_buttons) != set(expected_traffic_geometry) or any(
            traffic_buttons[name].geometry().getRect() != geometry
            for name, geometry in expected_traffic_geometry.items()
        ):
            raise RuntimeError("The traffic-light hit targets moved or changed size.")
        if (
            TrafficLightButton.DOT_DIAMETER,
            TrafficLightButton.HALO_DIAMETER,
            TrafficLightButton.FOCUS_DIAMETER,
        ) != (13.0, 20.0, 16.0):
            raise RuntimeError("The traffic-light dot or glow size changed.")

        def traffic_alpha_centroid(button, hovered=False):
            button.clearFocus()
            button.setAttribute(Qt.WA_UnderMouse, hovered)
            button.update()
            image = button.grab().toImage()
            weighted_pixels = []
            for y in range(image.height()):
                for x in range(image.width()):
                    alpha = image.pixelColor(x, y).alpha()
                    if alpha:
                        weighted_pixels.append((x, y, alpha))
            if not weighted_pixels:
                raise RuntimeError("A traffic-light button did not paint its dot.")
            total_alpha = sum(alpha for _, _, alpha in weighted_pixels)
            return (
                sum(x * alpha for x, _, alpha in weighted_pixels) / total_alpha,
                sum(y * alpha for _, y, alpha in weighted_pixels) / total_alpha,
                (image.width() - 1) / 2.0,
                (image.height() - 1) / 2.0,
            )

        for traffic_button in traffic_buttons.values():
            center_x, center_y, target_x, target_y = traffic_alpha_centroid(
                traffic_button
            )
            if abs(center_x - target_x) > 0.08 or abs(center_y - target_y) > 0.08:
                raise RuntimeError("A traffic-light dot is not centered in its hit target.")
        center_x, center_y, target_x, target_y = traffic_alpha_centroid(
            traffic_buttons["closeDot"],
            hovered=True,
        )
        traffic_buttons["closeDot"].setAttribute(Qt.WA_UnderMouse, False)
        if abs(center_x - target_x) > 0.08 or abs(center_y - target_y) > 0.08:
            raise RuntimeError("A traffic-light hover glow is not centered on its dot.")

        class _VanishingImagePath:
            suffix = ".png"

            def expanduser(self):
                return self

            def resolve(self):
                return self

            @staticmethod
            def is_file():
                return True

            @staticmethod
            def stat():
                raise FileNotFoundError("The selected image disappeared.")

        previous_source = window.source_file
        previous_result = window.last_result
        window.set_source_file(_VanishingImagePath())
        if (
            window.source_file is not previous_source
            or window.last_result is not previous_result
            or window.status_label.text() != "Invalid file"
        ):
            raise RuntimeError("A disappearing image changed the current app state.")
        window.status_label.setText("Ready")

        class _UnavailableImagePath:
            @staticmethod
            def is_file():
                raise OSError("The drive disconnected.")

        if source_file_is_available(_UnavailableImagePath()):
            raise RuntimeError("An unavailable image path was treated as usable.")

        window.source_dropdown.select("Image file")
        if (
            window.file_path_label.full_text() != EMPTY_IMAGE_LABEL
            or window.file_path_label.toolTip() != EMPTY_IMAGE_TOOLTIP
            or "..." in window.file_path_label.full_text()
        ):
            raise RuntimeError("The empty image chooser has awkward or unclear wording.")
        selected_image_folder = temporary_path / "private-folder-not-for-display"
        selected_image_folder.mkdir()
        selected_image_path = selected_image_folder / "street-view-test-image.png"
        selected_image = QImage(32, 24, QImage.Format_RGB32)
        selected_image.fill(QColor("#49657a"))
        if not selected_image.save(str(selected_image_path), "PNG"):
            raise RuntimeError("Could not create the selected-image UI fixture.")
        configured_report_folder = temporary_path / "chosen-report-folder"
        window.output_folder = configured_report_folder
        window.output_path_label.set_full_text(str(configured_report_folder))
        window.save_preferences()
        window.set_source_file(selected_image_path)
        if (
            window.source_file != selected_image_path.resolve()
            or window.file_path_label.full_text() != selected_image_path.name
            or window.file_path_label.accessibleName() != selected_image_path.name
            or window.file_path_label.toolTip() != str(selected_image_path.resolve())
            or str(selected_image_folder) in window.file_path_label.full_text()
            or window.output_folder != configured_report_folder
            or Path(str(window.settings.value("output_folder", "")))
            != configured_report_folder
        ):
            raise RuntimeError(
                "A selected image exposed or replaced the configured report folder."
            )
        window.source_dropdown.select("Screen capture")
        if "cursor excluded" not in window.file_path_label.full_text():
            raise RuntimeError("Screen-capture input lost its clear monitor description.")
        window.source_dropdown.select("Image file")
        if window.file_path_label.full_text() != selected_image_path.name:
            raise RuntimeError("Returning to Image file did not restore its filename.")

        original_guidance_save = globals()["save_extra_guidance"]
        guidance_save_calls = []

        def counted_guidance_save(settings, guidance):
            guidance_save_calls.append(guidance)
            return original_guidance_save(settings, guidance)

        globals()["save_extra_guidance"] = counted_guidance_save
        try:
            for _ in range(100):
                window.persist_preference_change()
            if guidance_save_calls:
                raise RuntimeError(
                    "Unchanged controls repeatedly re-encrypted optional guidance."
                )
            window.extra_guidance_input.setText("private performance test clue")
            window.persist_preference_change()
            for _ in range(100):
                window.preference_changed()
            if guidance_save_calls != ["private performance test clue"]:
                raise RuntimeError("Changed guidance was not encrypted exactly once.")
        finally:
            globals()["save_extra_guidance"] = original_guidance_save

        class FailingSettingsProbe:
            def __init__(self):
                self.values = {}

            def value(self, key, default=None):
                return self.values.get(key, default)

            def setValue(self, key, value):
                self.values[key] = value

            @staticmethod
            def sync():
                return None

            @staticmethod
            def status():
                return QSettings.Status.AccessError

        real_settings = window.settings
        window.settings = FailingSettingsProbe()
        window._settings_error_reported = False
        try:
            if window.save_preferences():
                raise RuntimeError("A settings write failure was reported as successful.")
            if (
                window.status_label.text() != "Settings could not be saved"
                or "Local preferences could not be saved" not in window.log_box.toPlainText()
            ):
                raise RuntimeError("A settings write failure was hidden from the user.")
        finally:
            window.settings = real_settings
            window._settings_error_reported = False

        if tuple(provider.id for provider in window._providers) != DIRECT_PROVIDER_ORDER:
            raise RuntimeError("The UI did not show exactly the four direct AI services.")
        if window._current_provider_id != DIRECT_PROVIDER_ORDER[0]:
            raise RuntimeError("The first direct AI service was not selected.")
        if len(window._model_by_label) != len(
            models_for_provider(DIRECT_PROVIDER_ORDER[0])
        ):
            raise RuntimeError("The direct provider's complete model list was not shown.")
        if window.left_tabs.count() != 3 or [
            window.left_tabs.tabText(index) for index in range(window.left_tabs.count())
        ] != ["Image", "AI Settings", "Tips"]:
            raise RuntimeError("The Image, AI Settings, and Tips categories are incorrect.")
        if window.log_box.parentWidget() is None or not window.log_box.isVisible():
            raise RuntimeError("The Activity console is missing from the Image category.")
        tips_text = window.tips_box.toPlainText()
        if any(
            heading not in tips_text
            for heading in (
                "Regular photos and screenshots",
                "GeoGuessr",
                "Settings",
            )
        ) or tips_text.count("1. ") < 3:
            raise RuntimeError("The accuracy tips are not clearly grouped and numbered.")
        tab_bar = window.left_tabs.tabBar()
        tab_widths = [
            tab_bar.tabRect(index).width() for index in range(tab_bar.count())
        ]
        if tab_bar.drawBase() or max(tab_widths) - min(tab_widths) > 1:
            raise RuntimeError("The category tabs are unequal or still draw a base line.")

        if (
            not window.save_results_enabled
            or not window.save_result_toggle.isChecked()
            or not window.output_controls.isVisible()
        ):
            raise RuntimeError("Report saving did not default to a clear enabled state.")
        window.save_result_toggle.setChecked(False)
        QApplication.processEvents()
        if (
            window.save_results_enabled
            or window.output_controls.isVisible()
            or window.output_browse_button.isEnabled()
            or saved_bool(window.settings, "save_results_enabled", True)
        ):
            raise RuntimeError("Turning report saving off left save controls or state active.")
        window.last_result = result
        window._report_needs_save = True
        if not window._confirm_pending_report("running the next safe test"):
            raise RuntimeError("Disabled report saving still warned about an unsaved report.")
        window._report_needs_save = False

        original_analyse_image = globals()["analyse_image"]
        original_worker_write_report = globals()["write_report"]
        globals()["analyse_image"] = lambda *args, **kwargs: (
            result,
            "The offline checks agree.",
            AnalysisStats(requested=1, attempted=1, completed=1, usable=1),
        )
        no_save_finished = []
        no_save_results = []
        result_delivery_order = []
        try:
            no_save_worker = AnalysisWorker(
                b"offline-image",
                "image/png",
                "not-a-real-key",
                model,
                "Low",
                1,
                "Regular photo or screenshot",
                "",
                None,
                "offline.png",
            )
            no_save_worker.result_ready.connect(no_save_results.append)
            no_save_worker.finished.connect(
                lambda state, message, returned, stats: no_save_finished.append(
                    (state, message, returned, stats)
                )
            )
            no_save_worker.run()

            globals()["write_report"] = (
                lambda *args, **kwargs: result_delivery_order.append("report write")
            )
            ordered_worker = AnalysisWorker(
                b"offline-image",
                "image/png",
                "not-a-real-key",
                model,
                "Low",
                1,
                "Regular photo or screenshot",
                "",
                temporary_path / "ordered-report.txt",
                "offline.png",
            )
            ordered_worker.result_ready.connect(
                lambda returned: result_delivery_order.append("result ready")
            )
            ordered_worker.run()
        finally:
            globals()["analyse_image"] = original_analyse_image
            globals()["write_report"] = original_worker_write_report
        if (
            no_save_results != [result]
            or len(no_save_finished) != 1
            or no_save_finished[0][0] != "success"
            or "saving is off" not in no_save_finished[0][1].casefold()
            or no_save_worker.api_key
            or no_save_worker.extra_guidance
            or no_save_worker.image_data
        ):
            raise RuntimeError("A no-save analysis did not return its result cleanly.")
        if result_delivery_order[:2] != ["result ready", "report write"]:
            raise RuntimeError("A result was not delivered before report file work began.")

        window.clear_log()
        window.map_view.clear_location()
        window.show_location_result(result)
        if (
            "LOCATION FOUND: Bergen - Vestland, Norway"
            not in window.log_box.toPlainText()
            or window.map_view.current_location != (result.latitude, result.longitude)
        ):
            raise RuntimeError("A successful result did not reach Activity and the map immediately.")
        window.map_view.clear_location()
        window.last_result = None
        window.clear_log()
        window.save_result_toggle.setChecked(True)
        QApplication.processEvents()
        if (
            not window.save_results_enabled
            or not window.output_controls.isVisible()
            or not saved_bool(window.settings, "save_results_enabled", False)
        ):
            raise RuntimeError("Turning report saving back on was not restored or persisted.")

        window.left_tabs.setCurrentIndex(1)
        QApplication.processEvents()
        if window.footer.isVisible() or window.find_button.isVisible():
            raise RuntimeError("The Image-only save footer leaked into AI Settings.")
        window.effort_dropdown.show_popup()
        QApplication.processEvents()
        effort_scrollbar = window.effort_dropdown.scroll_area.verticalScrollBar()
        popup_image = window.effort_dropdown.popup.grab().toImage()
        last_effort_option = window.effort_dropdown.option_buttons[-1]
        last_top_left = last_effort_option.mapTo(
            window.effort_dropdown.scroll_area.viewport(),
            QPoint(0, 0),
        )
        last_bottom_right = last_top_left + QPoint(
            last_effort_option.width() - 1,
            last_effort_option.height() - 1,
        )
        if (
            effort_scrollbar.isVisible()
            or popup_image.pixelColor(0, 0).alpha() != 0
            or not window.effort_dropdown.scroll_area.viewport().rect().contains(
                last_bottom_right
            )
        ):
            raise RuntimeError("A short dropdown is square or shows a needless scrollbar.")
        window.effort_dropdown.hide_popup(immediate=True)

        original_position = window.pos()
        window.effort_dropdown.show_popup()
        QApplication.processEvents()
        window.move(original_position + QPoint(1, 0))
        QApplication.processEvents()
        if window.effort_dropdown.popup.isVisible():
            raise RuntimeError("A dropdown remained open after its owner moved.")
        window.move(original_position)

        window.effort_dropdown.show_popup()
        QApplication.processEvents()
        window.resize(861, 520)
        QApplication.processEvents()
        if window.effort_dropdown.popup.isVisible():
            raise RuntimeError("A dropdown remained open after its owner resized.")
        window.resize(860, 520)

        window.effort_dropdown.show_popup()
        QApplication.processEvents()
        window.effort_dropdown.setEnabled(False)
        QApplication.processEvents()
        if window.effort_dropdown.popup.isVisible():
            raise RuntimeError("A disabled dropdown kept its popup open.")
        window.effort_dropdown.setEnabled(True)

        window.effort_dropdown.show_popup()
        QApplication.processEvents()
        QApplication.sendEvent(window, QEvent(QEvent.WindowStateChange))
        if window.effort_dropdown.popup.isVisible():
            raise RuntimeError("A minimized owner could leave a dropdown floating.")

        transition_host = QWidget()
        transition_layout = QVBoxLayout(transition_host)
        transition_dropdown = AnimatedDropdown(("One", "Two"), parent=transition_host)
        transition_layout.addWidget(transition_dropdown)
        transition_host.resize(260, 80)
        transition_host.show()
        QApplication.processEvents()
        transition_dropdown.show_popup()
        QApplication.processEvents()
        transition_host.hide()
        QApplication.processEvents()
        if transition_dropdown.popup.isVisible():
            raise RuntimeError("A hidden owner left its dropdown popup visible.")
        transition_host.show()
        QApplication.processEvents()
        transition_dropdown.show_popup()
        QApplication.processEvents()
        transition_host.close()
        QApplication.processEvents()
        if transition_dropdown.popup.isVisible():
            raise RuntimeError("A closed owner left its dropdown popup visible.")
        if (
            transition_dropdown._popup_filter_hosts
            or transition_dropdown._popup_application_filter
        ):
            raise RuntimeError("Dropdown lifecycle filters were not removed symmetrically.")
        transition_host.deleteLater()

        long_dropdown = AnimatedDropdown(
            [f"Option {index}" for index in range(1, 18)],
            parent=window,
        )
        long_dropdown.setGeometry(20, 50, 240, 40)
        long_dropdown.show()
        long_dropdown.show_popup()
        QApplication.processEvents()
        long_scrollbar = long_dropdown.scroll_area.verticalScrollBar()
        long_popup_image = long_dropdown.popup.grab().toImage()
        if (
            not long_scrollbar.isVisible()
            or long_scrollbar.geometry().right()
            >= long_dropdown.scroll_area.width()
            or long_popup_image.pixelColor(0, 0).alpha() != 0
        ):
            raise RuntimeError("A long dropdown scrollbar escaped its rounded surface.")
        long_dropdown.hide_popup(immediate=True)
        long_dropdown.hide()
        long_dropdown.deleteLater()

        window.left_tabs.setCurrentIndex(2)
        QApplication.processEvents()
        if window.footer.isVisible() or window.output_browse_button.isVisible():
            raise RuntimeError("The Image-only save footer leaked into Tips.")
        tips_scrollbar = window.tips_box.verticalScrollBar()
        if tips_scrollbar.maximum() <= 0:
            raise RuntimeError("The Tips scrollbar lacks a usable scroll range.")
        original_animation_check = globals()["ui_animations_enabled"]
        try:
            globals()["ui_animations_enabled"] = lambda: True
            tips_scrollbar.setValue(0)
            animated_target = min(80, tips_scrollbar.maximum())
            window.tips_box._smooth_scroll.scroll_by(
                tips_scrollbar,
                animated_target,
            )
            active_animation = window.tips_box._smooth_scroll._animations.get(
                tips_scrollbar
            )
            if (
                active_animation is None
                or int(active_animation.endValue()) != animated_target
            ):
                raise RuntimeError("Scrollable text did not start smooth movement.")
            deadline = time.monotonic() + 1.0
            while (
                tips_scrollbar in window.tips_box._smooth_scroll._animations
                and time.monotonic() < deadline
            ):
                QApplication.processEvents()
            if tips_scrollbar.value() != animated_target:
                raise RuntimeError("Smooth scrolling did not reach its requested position.")

            cached_animation = (
                window.tips_box._smooth_scroll._animation_cache.get(tips_scrollbar)
            )
            window.tips_box._smooth_scroll.scroll_by(
                tips_scrollbar,
                -animated_target,
            )
            if (
                cached_animation is None
                or window.tips_box._smooth_scroll._animations.get(tips_scrollbar)
                is not cached_animation
            ):
                raise RuntimeError("Repeated scrolling allocated a new animation.")
            window.tips_box._smooth_scroll._stop(tips_scrollbar)
            tips_scrollbar.setValue(animated_target)

            globals()["ui_animations_enabled"] = lambda: False
            immediate_target = min(animated_target + 30, tips_scrollbar.maximum())
            window.tips_box._smooth_scroll._animate_to(
                tips_scrollbar,
                immediate_target,
            )
            if (
                tips_scrollbar.value() != immediate_target
                or tips_scrollbar in window.tips_box._smooth_scroll._animations
            ):
                raise RuntimeError("Reduced motion did not make scrolling immediate.")
        finally:
            window.tips_box._smooth_scroll._stop(tips_scrollbar)
            globals()["ui_animations_enabled"] = original_animation_check
        window.left_tabs.setCurrentIndex(0)
        QApplication.processEvents()
        if not window.footer.isVisible() or not window.find_button.isVisible():
            raise RuntimeError("The save footer is missing from the Image category.")
        image_page = window.left_tabs.widget(0)
        image_layout = image_page.layout()
        if (
            image_layout is None
            or image_layout.count() != 1
            or image_layout.itemAt(0).widget() is not window.settings_scroll
            or not window.settings_scroll.widget().isAncestorOf(window.footer)
            or window.footer.geometry().top() <= window.log_box.geometry().bottom()
            or window.settings_scroll.verticalScrollBar().maximum() <= 0
        ):
            raise RuntimeError(
                "The Image controls and footer are not one continuous scroll page."
            )

        def assert_widget_reachable(widget, inner_scroll=None):
            if not widget.isVisible() or widget.width() <= 0 or widget.height() <= 0:
                return
            if inner_scroll is not None:
                inner_scroll.ensureWidgetVisible(widget, 0, 0)
            window.page_scroll.ensureWidgetVisible(widget, 0, 0)
            QApplication.processEvents()
            viewport = (
                inner_scroll.viewport()
                if inner_scroll is not None
                else window.page_scroll.viewport()
            )
            center = widget.mapTo(viewport, widget.rect().center())
            if not viewport.rect().contains(center):
                raise RuntimeError(
                    f"Compact layout could not scroll to {widget.objectName() or widget.__class__.__name__}."
                )

        original_minimum = window.minimumSize()
        window.setMinimumSize(240, 320)
        for compact_size in (
            (800, 450),
            (800, 449),
            (960, 500),
            (680, 380),
            (240, 320),
        ):
            window.resize(*compact_size)
            QApplication.processEvents()
            QApplication.processEvents()
            if (window.width(), window.height()) != compact_size:
                raise RuntimeError("The app cannot fit a supported compact desktop area.")
            if (
                window.settings_scroll.viewport().height() < 100
                or window.map_view.width() < 320
                or window.map_view.height() < 240
            ):
                raise RuntimeError("Compact layout content became unreachable or clipped.")
            if compact_size == (800, 449):
                panel_gap = (
                    window.map_panel.geometry().left()
                    - window.left_panel.geometry().right()
                    - 1
                )
                map_bounds = QRect(
                    0,
                    0,
                    window.map_panel.width(),
                    window.map_panel.height(),
                )
                if (
                    window.page_layout.direction() != QBoxLayout.LeftToRight
                    or panel_gap != 14
                    or not window.page_content.rect().contains(
                        window.left_panel.geometry()
                    )
                    or not window.page_content.rect().contains(
                        window.map_panel.geometry()
                    )
                    or not map_bounds.contains(window.map_view.geometry())
                    or window.page_scroll.verticalScrollBar().maximum() <= 0
                    or window.page_scroll.horizontalScrollBar().maximum() != 0
                ):
                    raise RuntimeError(
                        "The 800x449 boundary overflowed its contained two-column layout."
                    )
            if compact_size[0] < window.NORMAL_MINIMUM_WIDTH:
                if window.page_layout.direction() != QBoxLayout.TopToBottom:
                    raise RuntimeError("A narrow desktop did not reflow to one column.")
                if window.page_scroll.verticalScrollBar().maximum() <= 0:
                    raise RuntimeError("A short desktop lacks a usable page scroll range.")

                window.left_tabs.setCurrentIndex(0)
                QApplication.processEvents()
                for widget in (
                    window.source_dropdown,
                    window.monitor_dropdown,
                    window.prompt_dropdown,
                    window.extra_guidance_input,
                    window.log_box,
                ):
                    assert_widget_reachable(widget, window.settings_scroll)
                for widget in (
                    window.save_result_toggle,
                    window.output_path_label,
                    window.output_browse_button,
                    window.find_button,
                    window.progress_bar,
                    window.status_label,
                ):
                    assert_widget_reachable(widget, window.settings_scroll)

                window.left_tabs.setCurrentIndex(1)
                QApplication.processEvents()
                for widget in (
                    window.provider_dropdown,
                    window.model_dropdown,
                    window.effort_dropdown,
                    window.passes_dropdown,
                    window.note_label,
                    window.model_details_button,
                    window.api_key_input,
                    window.save_key_button,
                    window.show_key_button,
                    window.get_key_button,
                ):
                    assert_widget_reachable(widget, window.ai_settings_scroll)

                window.left_tabs.setCurrentIndex(2)
                QApplication.processEvents()
                assert_widget_reachable(window.tips_box)
                window.left_tabs.setCurrentIndex(0)
                QApplication.processEvents()

        window.setMinimumSize(original_minimum)
        window.resize(860, 520)
        QApplication.processEvents()
        QApplication.processEvents()
        if (
            window.page_scroll.horizontalScrollBar().isVisible()
            or window.page_scroll.verticalScrollBar().isVisible()
        ):
            raise RuntimeError("Normal desktop geometry gained an outer scrollbar.")

        for controls, buttons in (
            (
                window.map_view._controls,
                (
                    window.map_view._zoom_out_button,
                    window.map_view._zoom_in_button,
                    window.map_view._world_button,
                ),
            ),
            (
                window.map_view._layer_controls,
                (
                    window.map_view._street_button,
                    window.map_view._satellite_button,
                ),
            ),
        ):
            if any(
                abs(button.y() - (controls.height() - button.geometry().bottom() - 1))
                > 1
                for button in buttons
            ):
                raise RuntimeError("Global app styling vertically displaced map controls.")
        if str(window.settings.value("map/layer", "")) != "street":
            raise RuntimeError("The legacy map preference was not migrated to Street.")
        if int(window.settings.value("map/preference_schema", 0) or 0) != MAP_PREFERENCE_SCHEMA_VERSION:
            raise RuntimeError("The map preference migration was not recorded.")
        capture_target = window.selected_capture_target()
        if capture_target is None or capture_target.is_all or not capture_target.primary:
            raise RuntimeError("Screen capture did not default to only the primary monitor.")
        all_target = next(
            (target for target in window._capture_targets if target.is_all),
            None,
        )
        if all_target is None:
            raise RuntimeError("The explicit All monitors capture choice is missing.")
        window.monitor_dropdown.select(all_target.label)
        if str(window.settings.value(MONITOR_SETTING_KEY, "")) != ALL_MONITORS_ID:
            raise RuntimeError("The selected monitor preference was not saved.")
        window.monitor_dropdown.select(capture_target.label)
        window.map_view.show_satellite()
        if str(window.settings.value("map/layer", "")) != "satellite":
            raise RuntimeError("The Street or Satellite map preference was not saved.")
        window.map_view.show_street()
        if not window.find_button.isVisible() or window.find_button.height() < 40:
            raise RuntimeError("The fixed Find Location action was clipped or hidden.")
        if any(dropdown.button.height() < 38 for dropdown in window.dropdowns):
            raise RuntimeError("A compact layout clipped a dropdown control.")
        window.left_tabs.setCurrentIndex(1)
        window.api_key_input.setText("not-a-real-visible-key")
        window.toggle_key_visibility()
        window.provider_dropdown.select(provider_by_id("openai").label)
        QApplication.processEvents()
        if window._current_provider_id != "openai" or len(window._model_by_label) != 3:
            raise RuntimeError("Direct-provider switching did not rebuild the model list.")
        if window.api_key_input.echoMode() != QLineEdit.Password:
            raise RuntimeError("Provider switching exposed the next API key.")
        window.provider_dropdown.select(provider_by_id("anthropic").label)
        fable = model_by_id("anthropic", "claude-fable-5")
        previous_label = window.model_dropdown.currentText()
        original_privacy_dialog = window._show_model_privacy_warning
        window._show_model_privacy_warning = lambda selected, notice: False
        window.model_dropdown.select(fable.label)
        if window.model_dropdown.currentText() != previous_label:
            raise RuntimeError("Cancelling a privacy warning did not keep the safe model.")
        window._show_model_privacy_warning = lambda selected, notice: True
        window.model_dropdown.select(fable.label)
        window._show_model_privacy_warning = original_privacy_dialog
        if window.model_dropdown.currentText() != fable.label:
            raise RuntimeError("Accepting a privacy warning did not select the model.")
        notice = model_privacy_notice(fable)
        if notice is None or not notice["link_url"].startswith("https://"):
            raise RuntimeError("The model privacy warning lacks an official link.")

        compact_dialog = AppDialog("Compact dialog check", window)
        compact_dialog.resize(620, 420)
        compact_heading = QLabel("Compact dialog check")
        compact_heading.setObjectName("dialogHeading")
        compact_heading.setWordWrap(True)
        compact_dialog.content_layout.addWidget(compact_heading)
        compact_body = QTextEdit()
        compact_body.setReadOnly(True)
        compact_body.setPlainText("Scrollable details\n\n" * 20)
        compact_dialog.content_layout.addWidget(compact_body, 1)
        compact_actions = QBoxLayout(QBoxLayout.LeftToRight)
        compact_actions.addStretch(1)
        compact_cancel = QPushButton("Cancel")
        compact_accept = QPushButton("Use model")
        compact_accept.setObjectName("primary")
        compact_actions.addWidget(compact_cancel)
        compact_actions.addWidget(compact_accept)
        compact_dialog.content_layout.addLayout(compact_actions)
        compact_dialog.register_action_layout(compact_actions)
        compact_dialog.show()
        QApplication.processEvents()
        dialog_available = compact_dialog.screen().availableGeometry()
        if not dialog_available.contains(compact_dialog.frameGeometry()):
            raise RuntimeError("A frameless dialog escaped the logical desktop.")
        for action in (compact_cancel, compact_accept):
            action_center = action.mapToGlobal(action.rect().center())
            if not dialog_available.contains(action_center):
                raise RuntimeError("A compact dialog action became unreachable.")
        if compact_body.viewport().height() <= 0:
            raise RuntimeError("Compact dialog details lost their scrollable region.")
        compact_dialog.close()

        window.effort_dropdown.select("Ultra")
        window.passes_dropdown.select(PASS_OPTIONS[2])
        if window.selected_passes() != 3 or window.effort_dropdown.currentText() != "Ultra":
            raise RuntimeError("Effort and pass selectors were not independent.")
        window.set_controls_enabled(False)
        if window.acceptDrops():
            raise RuntimeError("Drag and drop remained active during analysis.")
        window.set_controls_enabled(True)

        start_failure_image = QImage(24, 16, QImage.Format_RGB32)
        start_failure_image.fill(QColor("#345678"))
        start_failure_path = temporary_path / "worker-start-check.png"
        if not start_failure_image.save(str(start_failure_path), "PNG"):
            raise RuntimeError("Could not create the offline worker-start fixture.")
        window.set_source_file(start_failure_path)
        window.api_key_input.setText("not-a-real-key")
        window.save_result_toggle.setChecked(False)
        real_output_folder = window.output_folder

        class NoSaveFolderGuard:
            def __truediv__(self, value):
                del value
                raise RuntimeError("Report path was touched while saving was off.")

            def mkdir(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("Report folder was checked while saving was off.")

        window.output_folder = NoSaveFolderGuard()
        worker_globals = window.start_analysis.__globals__
        original_qthread = worker_globals["QThread"]
        original_analysis_worker = worker_globals["AnalysisWorker"]
        cleanup_snapshots = []

        class CleanupProbeWorker(original_analysis_worker):
            def clear_private_payload(self):
                super().clear_private_payload()
                cleanup_snapshots.append(
                    (self.api_key, self.extra_guidance, self.image_data)
                )

        class FailingStartThread(original_qthread):
            def start(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("mocked worker start failure")

        worker_globals["AnalysisWorker"] = CleanupProbeWorker
        worker_globals["QThread"] = FailingStartThread
        try:
            window.start_analysis()
        finally:
            worker_globals["QThread"] = original_qthread
            worker_globals["AnalysisWorker"] = original_analysis_worker
            window.output_folder = real_output_folder
            window.save_result_toggle.setChecked(True)
        if (
            window.running
            or window.worker is not None
            or window.worker_thread is not None
            or window.find_button.text() != "Find Location"
            or not window.find_button.isEnabled()
            or not window.left_tabs.tabBar().isEnabled()
            or window.progress_bar.value() != 0
            or window.status_label.text() != "Analysis could not start"
            or "No AI request was sent" not in window.log_box.toPlainText()
            or cleanup_snapshots != [("", "", b"")]
        ):
            raise RuntimeError(
                "A QThread.start failure wedged the UI or retained private payloads."
            )

        partial_start_seen = threading.Event()
        partial_start_release = threading.Event()

        class BlockingStartProbeWorker(original_analysis_worker):
            @Slot()
            def run(self):
                partial_start_seen.set()
                partial_start_release.wait(5)
                self.clear_private_payload()
                self.finished.emit(
                    "cancelled",
                    "Analysis cancelled.",
                    None,
                    AnalysisStats(self.passes),
                )

        class PartiallyFailingStartThread(original_qthread):
            def run(self):
                partial_start_seen.set()
                partial_start_release.wait(5)

            def start(self, *args, **kwargs):
                super().start(*args, **kwargs)
                if not partial_start_seen.wait(2):
                    raise RuntimeError("mocked worker did not launch")
                raise RuntimeError("mocked partial worker start failure")

        active_partial_thread = None
        worker_globals["AnalysisWorker"] = BlockingStartProbeWorker
        worker_globals["QThread"] = PartiallyFailingStartThread
        try:
            window.start_analysis()
            active_partial_thread = window.worker_thread
            active_partial_worker = window.worker
            if (
                not window.running
                or active_partial_worker is None
                or active_partial_thread is None
                or active_partial_worker.api_key
                or active_partial_worker.extra_guidance
                or active_partial_worker.image_data
                or window.find_button.text() != "Stopping..."
                or window.find_button.isEnabled()
                or window.status_label.text() != "Stopping after start failure"
            ):
                raise RuntimeError(
                    "A partially started analysis worker was deleted or retained private payloads."
                )
        finally:
            worker_globals["QThread"] = original_qthread
            worker_globals["AnalysisWorker"] = original_analysis_worker
            partial_start_release.set()
            if active_partial_thread is not None:
                active_partial_thread.quit()
                active_partial_thread.wait(3000)
            QApplication.processEvents()
        if (
            window.running
            or window.worker is not None
            or window.worker_thread is not None
            or window.find_button.text() != "Find Location"
            or not window.find_button.isEnabled()
        ):
            raise RuntimeError(
                "A partially started analysis worker did not clean up safely."
            )

        window.append_log("<b>model text must stay plain</b>")
        if "<b>model text must stay plain</b>" not in window.log_box.toPlainText():
            raise RuntimeError("Model-controlled activity text rendered as rich text.")
        window.map_view.set_location(
            result.latitude,
            result.longitude,
            result.location,
            result.confidence_km,
        )
        QApplication.processEvents()
        window._last_report_context = {
            "source_name": "synthetic.png",
            "prompt_mode": "GeoGuessr screenshot",
            "model": model,
            "effort": "High",
            "requested": 3,
        }
        window.analysis_finished(
            "success_warning",
            "The report could not be saved during this safe test.",
            result,
            AnalysisStats(requested=3, attempted=3, completed=3, usable=2),
        )
        if (
            not window._report_needs_save
            or window.last_result is not result
            or window._last_report_context.get("usable") != 2
        ):
            raise RuntimeError("A report save warning discarded the usable result.")

        normalized_report = temporary_path / "normalized-report.txt"
        sentinel_report = b"existing report must remain byte-for-byte unchanged\r\n"
        normalized_report.write_bytes(sentinel_report)
        confirmation_targets = []
        original_choose_report = window._choose_report_save_path
        original_confirm_overwrite = window._confirm_report_overwrite
        window._choose_report_save_path = lambda suggested: str(
            temporary_path / "normalized-report"
        )
        window._confirm_report_overwrite = (
            lambda output: confirmation_targets.append(output) or False
        )
        try:
            window.open_output_folder()
        finally:
            window._choose_report_save_path = original_choose_report
            window._confirm_report_overwrite = original_confirm_overwrite
        if (
            confirmation_targets != [normalized_report]
            or normalized_report.read_bytes() != sentinel_report
            or not window._report_needs_save
            or window.last_result is not result
            or window.status_label.text() != "Report still not saved"
        ):
            raise RuntimeError(
                "Cancelling a normalized-name overwrite changed an existing report."
            )

        pending_actions = []
        original_confirm = window._confirm_pending_report
        window._confirm_pending_report = (
            lambda action: pending_actions.append(action) or False
        )
        blocked_close = QCloseEvent()
        window.closeEvent(blocked_close)
        window._confirm_pending_report = original_confirm
        if blocked_close.isAccepted() or pending_actions != ["closing the app"]:
            raise RuntimeError("An unsaved warning-path report did not block closing.")
        window._report_needs_save = False
        window.output_file = None
        window.output_folder = temporary_path / "missing-output-folder"
        window.clear_log()
        window.open_output_folder()
        if (
            window.status_label.text() != "Output folder is unavailable"
            or "no longer exists" not in window.log_box.toPlainText()
        ):
            raise RuntimeError("A missing output folder failed without a useful message.")
        window.close()
        checks.append(
            "filename-only image display, change-aware protected settings, reused scroll animations, smooth accessible scrolling, exact dropdown sizing, optional report saving, immediate Activity result and map pin, informed model privacy, and guarded save recovery"
        )

    return write_self_test_output(folder, checks, "self-test")


def screenshot_app(output_path) -> int:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fleece-location-screenshot-") as temporary:
        settings_path = Path(temporary) / "settings.ini"
        window = LocationFinder(settings_path=settings_path, testing=True)
        window.resize(1260, 800)
        window.output_path_label.set_full_text(r"C:\Users\You\Downloads")
        sample_result = GeoResult(
            location="Bergen, Vestland, Norway",
            country="Norway",
            region="Vestland",
            city="Bergen",
            latitude=60.3913,
            longitude=5.3221,
            confidence_km=18,
            confidence_percent=84,
            evidence=[
                "Mountainous coastal terrain and road design point to western Norway.",
                "Architecture and vegetation fit the Bergen area.",
            ],
            alternatives=[],
        )
        window.last_result = sample_result
        window.map_view.set_location(
            sample_result.latitude,
            sample_result.longitude,
            sample_result.location,
            sample_result.confidence_km,
        )
        window.set_map_subhead(
            "Bergen, Vestland, Norway - 84% AI-reported confidence"
        )
        window.status_label.setText("Ready")
        window.append_log(
            "Choose a screenshot or image, then select effort and the number of AI checks."
        )
        window.append_log("The normal mouse cursor is left out of screen captures.")
        window.show()
        QApplication.processEvents()
        QApplication.processEvents()
        if not window.grab().save(str(output_path), "PNG"):
            raise OSError(f"Could not save screenshot to {output_path}")
        window.close()
    print(f"Saved {output_path}")
    return 0


def main() -> int:
    if os.name != "nt":
        show_native_error("AI Location Finder supports 64-bit Windows only.")
        return 1
    diagnostic_mode = any(
        option in sys.argv for option in ("--install-check", "--self-test", "--screenshot")
    )
    if diagnostic_mode:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        system_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        if system_fonts.is_dir():
            os.environ.setdefault("QT_QPA_FONTDIR", str(system_fonts))
    else:
        if not acquire_app_mutex():
            show_native_error("AI Location Finder is already open.")
            return 1
        if SETUP_LOCK_DIR.is_dir():
            show_native_error(
                "AI Location Finder setup is currently running.\n\n"
                "Let Installer.bat finish, then open the app again."
            )
            return 1

    try:
        set_dpi_context = ctypes.windll.user32.SetProcessDpiAwarenessContext
        set_dpi_context(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "fleece.ai-location-finder"
        )
    except (AttributeError, OSError):
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Fleece")
    sys.excepthook = sys.__excepthook__ if diagnostic_mode else handle_unhandled_exception

    if "--install-check" in sys.argv:
        index = sys.argv.index("--install-check")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--install-check needs an output folder")
        return run_install_check(Path(sys.argv[index + 1]))
    if "--self-test" in sys.argv:
        index = sys.argv.index("--self-test")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--self-test needs an output folder")
        return run_self_test(Path(sys.argv[index + 1]))
    if "--screenshot" in sys.argv:
        index = sys.argv.index("--screenshot")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--screenshot needs an output PNG path")
        return screenshot_app(sys.argv[index + 1])

    window = LocationFinder()
    window.show()
    QTimer.singleShot(100, start_provider_runtime_warmup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
