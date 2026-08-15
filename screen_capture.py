
from __future__ import annotations

import ctypes
import os
import operator
import re
import sys
from contextlib import contextmanager
from ctypes import wintypes
from dataclasses import dataclass
from typing import Iterable, Iterator

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage


ALL_MONITORS_ID = "all"
PRIMARY_MONITOR_ID = "primary"
MONITOR_SETTING_KEY = "capture/monitor_id"
_MONITOR_ID_PREFIX = "monitor:"
_MONITORINFOF_PRIMARY = 0x00000001
_SRCCOPY = 0x00CC0020
_CAPTUREBLT = 0x40000000
_DIB_RGB_COLORS = 0
_BI_RGB = 0
_HGDI_ERROR = ctypes.c_void_p(-1).value
_SIGNED_INT_MIN = -(2**31)
_SIGNED_INT_MAX = 2**31 - 1


class ScreenCaptureError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MonitorInfo:

    id: str
    label: str
    device_name: str | None
    left: int
    top: int
    width: int
    height: int
    primary: bool = False
    display_number: int | None = None
    is_all: bool = False

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("A monitor ID cannot be empty.")
        if self.width < 1 or self.height < 1:
            raise ValueError("A monitor must have a positive width and height.")
        if self.is_all and self.id != ALL_MONITORS_ID:
            raise ValueError("The all-monitors target must use the all ID.")

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def physical_rect(self) -> tuple[int, int, int, int]:

        return self.left, self.top, self.width, self.height

    @property
    def bounds(self) -> tuple[int, int, int, int]:

        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True, slots=True)
class _MonitorRecord:
    device_name: str
    left: int
    top: int
    right: int
    bottom: int
    primary: bool


def _require_windows() -> None:
    if os.name != "nt":
        raise ScreenCaptureError("Screen capture is supported on Windows only.")


def _windows_error(message: str) -> ScreenCaptureError:
    code = ctypes.get_last_error()
    if code:
        detail = ctypes.FormatError(code).strip()
        return ScreenCaptureError(f"{message} Windows error {code}: {detail}")
    return ScreenCaptureError(message)


@contextmanager
def _physical_pixel_context() -> Iterator[None]:

    if os.name != "nt":
        yield
        return

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    set_context = getattr(user32, "SetThreadDpiAwarenessContext", None)
    previous = None
    if set_context is not None:
        set_context.argtypes = (ctypes.c_void_p,)
        set_context.restype = ctypes.c_void_p
        previous = set_context(ctypes.c_void_p(-4))
        if not previous:
            previous = set_context(ctypes.c_void_p(-3))
    try:
        yield
    finally:
        if set_context is not None and previous:
            set_context(previous)


def _display_number(device_name: str) -> int | None:
    match = re.search(r"DISPLAY(\d+)$", device_name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _monitor_id(device_name: str) -> str:
    return f"{_MONITOR_ID_PREFIX}{device_name.casefold()}"


def _records_to_monitors(records: Iterable[_MonitorRecord]) -> tuple[MonitorInfo, ...]:
    records = tuple(records)
    if not records:
        raise ScreenCaptureError("Windows did not report any active monitors.")

    seen_ids: set[str] = set()
    prepared: list[tuple[_MonitorRecord, int | None, str]] = []
    for record in records:
        width = record.right - record.left
        height = record.bottom - record.top
        if width < 1 or height < 1:
            raise ScreenCaptureError(
                f"Windows reported an invalid rectangle for {record.device_name}."
            )
        monitor_id = _monitor_id(record.device_name)
        if monitor_id in seen_ids:
            raise ScreenCaptureError(
                f"Windows reported the monitor {record.device_name} more than once."
            )
        seen_ids.add(monitor_id)
        prepared.append((record, _display_number(record.device_name), monitor_id))

    prepared.sort(
        key=lambda item: (
            item[1] is None,
            item[1] if item[1] is not None else 0,
            item[0].top,
            item[0].left,
            item[0].device_name.casefold(),
        )
    )

    monitors: list[MonitorInfo] = []
    used_numbers = {number for _, number, _ in prepared if number is not None}
    fallback_number = 1
    for record, number, monitor_id in prepared:
        if number is None:
            while fallback_number in used_numbers:
                fallback_number += 1
            number = fallback_number
            used_numbers.add(number)
            fallback_number += 1
        width = record.right - record.left
        height = record.bottom - record.top
        primary_text = " (Primary)" if record.primary else ""
        monitors.append(
            MonitorInfo(
                id=monitor_id,
                label=f"Monitor {number}{primary_text} - {width} x {height}",
                device_name=record.device_name,
                left=record.left,
                top=record.top,
                width=width,
                height=height,
                primary=record.primary,
                display_number=number,
            )
        )
    return tuple(monitors)


def _enumerate_monitor_records() -> tuple[_MonitorRecord, ...]:
    _require_windows()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hmonitor_type = wintypes.HANDLE

    class MonitorInfoExW(ctypes.Structure):
        _fields_ = (
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
            ("szDevice", wintypes.WCHAR * 32),
        )

    monitor_callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        hmonitor_type,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )
    user32.EnumDisplayMonitors.argtypes = (
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        monitor_callback_type,
        wintypes.LPARAM,
    )
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    user32.GetMonitorInfoW.argtypes = (
        hmonitor_type,
        ctypes.POINTER(MonitorInfoExW),
    )
    user32.GetMonitorInfoW.restype = wintypes.BOOL

    records: list[_MonitorRecord] = []
    callback_error: list[ScreenCaptureError] = []

    @monitor_callback_type
    def collect_monitor(monitor, _monitor_dc, _rect, _data):
        info = MonitorInfoExW()
        info.cbSize = ctypes.sizeof(MonitorInfoExW)
        ctypes.set_last_error(0)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            callback_error.append(_windows_error("A monitor's details could not be read."))
            return False
        rect = info.rcMonitor
        records.append(
            _MonitorRecord(
                device_name=str(info.szDevice),
                left=int(rect.left),
                top=int(rect.top),
                right=int(rect.right),
                bottom=int(rect.bottom),
                primary=bool(info.dwFlags & _MONITORINFOF_PRIMARY),
            )
        )
        return True

    with _physical_pixel_context():
        ctypes.set_last_error(0)
        succeeded = user32.EnumDisplayMonitors(None, None, collect_monitor, 0)
    if callback_error:
        raise callback_error[0]
    if not succeeded:
        raise _windows_error("The active monitors could not be listed.")
    return tuple(records)


def enumerate_monitors() -> tuple[MonitorInfo, ...]:

    return _records_to_monitors(_enumerate_monitor_records())


def _all_monitors_target(monitors: tuple[MonitorInfo, ...]) -> MonitorInfo:
    if not monitors:
        raise ScreenCaptureError("Windows did not report any active monitors.")
    left = min(monitor.left for monitor in monitors)
    top = min(monitor.top for monitor in monitors)
    right = max(monitor.right for monitor in monitors)
    bottom = max(monitor.bottom for monitor in monitors)
    width = right - left
    height = bottom - top
    return MonitorInfo(
        id=ALL_MONITORS_ID,
        label=f"All monitors - {width} x {height}",
        device_name=None,
        left=left,
        top=top,
        width=width,
        height=height,
        is_all=True,
    )


def enumerate_capture_targets() -> tuple[MonitorInfo, ...]:

    monitors = enumerate_monitors()
    return (*monitors, _all_monitors_target(monitors))


def primary_monitor(monitors: tuple[MonitorInfo, ...] | None = None) -> MonitorInfo:

    active = enumerate_monitors() if monitors is None else monitors
    for monitor in active:
        if monitor.primary:
            return monitor
    if active:
        return active[0]
    raise ScreenCaptureError("Windows did not report any active monitors.")


def resolve_capture_target_from_targets(
    target: str | MonitorInfo | None,
    candidates: tuple[MonitorInfo, ...],
) -> MonitorInfo:

    if not candidates:
        raise ScreenCaptureError("Windows did not report any active monitors.")
    requested_id = PRIMARY_MONITOR_ID if target is None else (
        target.id if isinstance(target, MonitorInfo) else str(target)
    )
    requested_key = requested_id.casefold()
    monitors = tuple(item for item in candidates if not item.is_all)
    if requested_key == PRIMARY_MONITOR_ID:
        return primary_monitor(monitors)
    for candidate in candidates:
        if candidate.id.casefold() == requested_key:
            return candidate
    raise ScreenCaptureError(
        "The selected monitor is no longer connected. Choose another monitor and try again."
    )


def resolve_saved_target_from_targets(
    saved_id: str | None,
    candidates: tuple[MonitorInfo, ...],
) -> MonitorInfo:

    try:
        return resolve_capture_target_from_targets(saved_id, candidates)
    except ScreenCaptureError:
        return resolve_capture_target_from_targets(PRIMARY_MONITOR_ID, candidates)


def resolve_capture_target(
    target: str | MonitorInfo | None = None,
) -> MonitorInfo:

    candidates = enumerate_capture_targets()
    return resolve_capture_target_from_targets(target, candidates)


def resolve_saved_target(saved_id: str | None) -> MonitorInfo:

    candidates = enumerate_capture_targets()
    return resolve_saved_target_from_targets(saved_id, candidates)


def _validated_capture_geometry(
    left: int,
    top: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int, int]:

    try:
        left = operator.index(left)
        top = operator.index(top)
        width = operator.index(width)
        height = operator.index(height)
    except TypeError as error:
        raise ScreenCaptureError("The selected capture rectangle was invalid.") from error
    if width < 1 or height < 1:
        raise ScreenCaptureError("The selected capture rectangle is empty.")
    if not _SIGNED_INT_MIN <= left <= _SIGNED_INT_MAX:
        raise ScreenCaptureError("The selected monitor starts outside Windows capture limits.")
    if not _SIGNED_INT_MIN <= top <= _SIGNED_INT_MAX:
        raise ScreenCaptureError("The selected monitor starts outside Windows capture limits.")
    if width > _SIGNED_INT_MAX or height > _SIGNED_INT_MAX:
        raise ScreenCaptureError("The selected monitor is too large to capture safely.")
    if not _SIGNED_INT_MIN <= left + width <= _SIGNED_INT_MAX:
        raise ScreenCaptureError("The selected monitor extends outside Windows capture limits.")
    if not _SIGNED_INT_MIN <= top + height <= _SIGNED_INT_MAX:
        raise ScreenCaptureError("The selected monitor extends outside Windows capture limits.")
    if width > sys.maxsize // 4 // height:
        raise ScreenCaptureError("The selected monitor image is too large for memory.")
    return left, top, width, height, width * height * 4


def _copy_capture_buffer(
    address: int,
    width: int,
    height: int,
    byte_count: int,
) -> QImage:

    try:
        pixels = (ctypes.c_ubyte * byte_count).from_address(address)
        pixel_view = memoryview(pixels).cast("B")
        try:
            image = QImage(
                pixel_view,
                width,
                height,
                width * 4,
                QImage.Format.Format_RGB32,
            ).copy()
        finally:
            pixel_view.release()
    except (MemoryError, OverflowError, OSError, ValueError) as error:
        raise ScreenCaptureError(
            "There was not enough memory to copy the selected monitor image."
        ) from error
    if image.isNull():
        raise ScreenCaptureError("The captured monitor image was empty.")
    return image


def _capture_rectangle(left: int, top: int, width: int, height: int) -> QImage:
    _require_windows()
    left, top, width, height, byte_count = _validated_capture_geometry(
        left, top, width, height
    )

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = (
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        )

    class RgbQuad(ctypes.Structure):
        _fields_ = (
            ("rgbBlue", wintypes.BYTE),
            ("rgbGreen", wintypes.BYTE),
            ("rgbRed", wintypes.BYTE),
            ("rgbReserved", wintypes.BYTE),
        )

    class BitmapInfo(ctypes.Structure):
        _fields_ = (
            ("bmiHeader", BitmapInfoHeader),
            ("bmiColors", RgbQuad * 1),
        )

    user32.GetDC.argtypes = (wintypes.HWND,)
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = (wintypes.HWND, wintypes.HDC)
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.CreateCompatibleDC.argtypes = (wintypes.HDC,)
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = (
        wintypes.HDC,
        ctypes.POINTER(BitmapInfo),
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.HANDLE,
        wintypes.DWORD,
    )
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = (wintypes.HDC, wintypes.HGDIOBJ)
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.BitBlt.argtypes = (
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
    )
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.DeleteObject.argtypes = (wintypes.HGDIOBJ,)
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = (wintypes.HDC,)
    gdi32.DeleteDC.restype = wintypes.BOOL

    info = BitmapInfo()
    info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = _BI_RGB

    image: QImage | None = None
    screen_dc = None
    memory_dc = None
    bitmap = None
    previous = None
    bitmap_selected = False
    with _physical_pixel_context():
        ctypes.set_last_error(0)
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            raise _windows_error("The desktop could not be opened for capture.")
        try:
            ctypes.set_last_error(0)
            memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not memory_dc:
                raise _windows_error("The screen-capture buffer could not be created.")

            bits = ctypes.c_void_p()
            ctypes.set_last_error(0)
            bitmap = gdi32.CreateDIBSection(
                screen_dc,
                ctypes.byref(info),
                _DIB_RGB_COLORS,
                ctypes.byref(bits),
                None,
                0,
            )
            if not bitmap or not bits.value:
                raise _windows_error("The screen-capture bitmap could not be created.")

            ctypes.set_last_error(0)
            previous = gdi32.SelectObject(memory_dc, bitmap)
            if not previous or int(previous) == _HGDI_ERROR:
                raise _windows_error("The screen-capture bitmap could not be selected.")
            bitmap_selected = True

            ctypes.set_last_error(0)
            if not gdi32.BitBlt(
                memory_dc,
                0,
                0,
                width,
                height,
                screen_dc,
                left,
                top,
                _SRCCOPY | _CAPTUREBLT,
            ):
                raise _windows_error("The selected monitor image could not be copied.")

            image = _copy_capture_buffer(bits.value, width, height, byte_count)
        finally:
            if bitmap_selected and previous and memory_dc:
                gdi32.SelectObject(memory_dc, previous)
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            if screen_dc:
                user32.ReleaseDC(None, screen_dc)

    if image is None or image.isNull():
        raise ScreenCaptureError("The captured monitor image was empty.")
    return image


def capture_screen(
    target: str | MonitorInfo | None = None,
) -> QImage:

    current = resolve_capture_target(target)
    return _capture_rectangle(*current.physical_rect)


def capture_virtual_screen() -> QImage:

    return capture_screen(ALL_MONITORS_ID)


def image_to_png_bytes(image: QImage) -> bytes:

    if image.isNull():
        raise ScreenCaptureError("An empty image cannot be encoded.")
    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise ScreenCaptureError("The PNG memory buffer could not be opened.")
    try:
        if not image.save(buffer, "PNG"):
            raise ScreenCaptureError("The captured image could not be encoded as PNG.")
        return bytes(buffer.data())
    finally:
        buffer.close()


def capture_screen_png(
    target: str | MonitorInfo | None = None,
) -> bytes:

    return image_to_png_bytes(capture_screen(target))


def safe_enumeration_test() -> tuple[MonitorInfo, ...]:

    targets = enumerate_capture_targets()
    if len(targets) < 2 or not targets[-1].is_all:
        raise AssertionError("The All monitors choice or active monitor is missing.")
    ids = [target.id.casefold() for target in targets]
    if len(ids) != len(set(ids)):
        raise AssertionError("Monitor IDs are not unique.")
    if not any(target.primary for target in targets[:-1]):
        raise AssertionError("Windows did not identify a primary monitor.")
    for target in targets:
        if target.width < 1 or target.height < 1:
            raise AssertionError("A capture target has invalid dimensions.")
    return targets


def run_self_tests(include_system_enumeration: bool = True) -> tuple[str, ...]:

    checks: list[str] = []
    synthetic = _records_to_monitors(
        (
            _MonitorRecord(r"\\.\DISPLAY2", -2560, 0, 0, 1440, False),
            _MonitorRecord(r"\\.\DISPLAY1", 0, 0, 1920, 1080, True),
        )
    )
    assert [monitor.display_number for monitor in synthetic] == [1, 2]
    assert synthetic[0].label == "Monitor 1 (Primary) - 1920 x 1080"
    assert synthetic[1].physical_rect == (-2560, 0, 2560, 1440)
    assert synthetic[0].id != synthetic[1].id
    assert primary_monitor(synthetic) == synthetic[0]
    checks.append("synthetic monitor ordering, labels, IDs, and rectangles")

    combined = _all_monitors_target(synthetic)
    assert combined.id == ALL_MONITORS_ID
    assert combined.is_all
    assert combined.physical_rect == (-2560, 0, 4480, 1440)
    checks.append("virtual desktop union with a negative monitor origin")

    snapshot = (*synthetic, combined)
    assert resolve_capture_target_from_targets(synthetic[1].id, snapshot) == synthetic[1]
    assert resolve_capture_target_from_targets(ALL_MONITORS_ID, snapshot) == combined
    assert resolve_saved_target_from_targets("monitor:missing", snapshot) == synthetic[0]
    original_enumerator = globals()["enumerate_capture_targets"]
    enumeration_calls = 0

    def fixed_snapshot():
        nonlocal enumeration_calls
        enumeration_calls += 1
        return snapshot

    globals()["enumerate_capture_targets"] = fixed_snapshot
    try:
        assert resolve_saved_target("monitor:missing") == synthetic[0]
    finally:
        globals()["enumerate_capture_targets"] = original_enumerator
    assert enumeration_calls == 1
    checks.append("single-snapshot target resolution and primary fallback")

    geometry = _validated_capture_geometry(-2560, -1440, 4480, 2520)
    assert geometry == (-2560, -1440, 4480, 2520, 4480 * 2520 * 4)
    for invalid_geometry in (
        (0.5, 0, 1920, 1080),
        (0, 0, 0, 1080),
        (_SIGNED_INT_MAX, 0, 2, 1),
    ):
        try:
            _validated_capture_geometry(*invalid_geometry)
        except ScreenCaptureError:
            continue
        raise AssertionError(f"Unsafe capture geometry was accepted: {invalid_geometry}")
    checks.append("signed Win32 geometry and allocation-overflow guards")

    raw_pixels = (ctypes.c_ubyte * 16)(*([0, 0, 255, 0] * 4))
    copied = _copy_capture_buffer(ctypes.addressof(raw_pixels), 2, 2, 16)
    raw_pixels[2] = 0
    assert not copied.isNull() and copied.size().width() == 2 and copied.size().height() == 2
    assert copied.pixelColor(0, 0).name() == "#ff0000"
    checks.append("single-copy owned image transfer from a synthetic DIB buffer")

    sample = QImage(3, 2, QImage.Format.Format_RGB32)
    sample.fill(0xFF123456)
    encoded = image_to_png_bytes(sample)
    assert encoded.startswith(b"\x89PNG\r\n\x1a\n")
    decoded = QImage.fromData(encoded, "PNG")
    assert not decoded.isNull() and decoded.width() == 3 and decoded.height() == 2
    checks.append("in-memory QImage to PNG encoding")

    if include_system_enumeration and os.name == "nt":
        safe_enumeration_test()
        checks.append("safe active-monitor enumeration without desktop capture")
    return tuple(checks)


if __name__ == "__main__":
    completed = run_self_tests()
    print(f"screen_capture.py passed {len(completed)} checks:")
    for completed_check in completed:
        print(f"- {completed_check}")
