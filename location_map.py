"""Detailed online map with an instant, verified offline fallback.

The street layer uses OpenStreetMap's standard raster tile service. Runtime
requests are limited to the tiles visible in the interactive viewport, carry a
named application user agent, and use Qt's HTTP-aware disk cache. The module
does not prefetch tiles or offer bulk/offline downloads.

The satellite layer uses Esri's public World Imagery service together with the
public transportation and place-label reference services. These classic raster
services are deprecated by Esri and can be withdrawn, so the street layer and
the bundled Natural Earth map remain fully functional fallbacks.

Official references:
https://operations.osmfoundation.org/policies/tiles/
https://esri.github.io/esri-leaflet/api-reference/layers/basemap-layer.html
https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9
https://doc.qt.io/qt-6/qnetworkdiskcache.html

The bundled fallback is mechanically rendered from Natural Earth Vector
v5.1.2 Admin-0 Countries and Lakes data. Natural Earth data is public domain:
https://www.naturalearthdata.com/about/terms-of-use/
"""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import math
from pathlib import Path
import sys
import time
from typing import Optional

import shiboken6

from PySide6.QtCore import (
    QBuffer,
    QIODevice,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QStandardPaths,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QImage,
    QImageReader,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QResizeEvent,
    QShowEvent,
    QWheelEvent,
)
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkDiskCache,
    QNetworkReply,
    QNetworkRequest,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


MODULE_DIR = Path(__file__).resolve().parent
MAP_ASSET_PATH = MODULE_DIR / "assets" / "world_map.png"
MAP_ASSET_SHA256 = "95eea18d4483e463a4d9d6c4a1b6198f926e790f4ad1844e727fb00ce42224fa"
MAP_ASSET_WIDTH = 3600
MAP_ASSET_HEIGHT = 1800
MAP_SCENE_RECT = QRectF(0.0, 0.0, float(MAP_ASSET_WIDTH), float(MAP_ASSET_HEIGHT))
MAP_SOURCE_URL = "https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2"
MAP_TERMS_URL = "https://www.naturalearthdata.com/about/terms-of-use/"

OSM_TILE_POLICY_URL = "https://operations.osmfoundation.org/policies/tiles/"
OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
OSM_FIX_MAP_URL = "https://www.openstreetmap.org/fixthemap"
ESRI_IMAGERY_ITEM_URL = (
    "https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9"
)
ESRI_CLASSIC_BASEMAP_DOCS_URL = (
    "https://esri.github.io/esri-leaflet/api-reference/layers/basemap-layer.html"
)

LAYER_STREET = "street"
LAYER_SATELLITE = "satellite"
VALID_LAYERS = frozenset((LAYER_STREET, LAYER_SATELLITE))

MIN_ZOOM = 1.0
MAX_ZOOM = 19.0
ZOOM_STEP = 1.0
RESULT_MIN_ZOOM = 2.5
RESULT_MAX_ZOOM = 6.0
RESULT_FRAME_WIDTH_KM = 1800.0
RESULT_FRAME_HEIGHT_KM = 1200.0
TILE_SIZE = 256
WEB_MERCATOR_MAX_LATITUDE = 85.05112878
EARTH_RADIUS_KM = 6371.0088
MAX_MEMORY_TILES = 256
MAX_PENDING_TILES = 72
MAX_FAILED_TILES = 512
FAILED_TILE_RETRY_SECONDS = 30.0
NETWORK_TIMEOUT_MS = 12_000
NETWORK_CACHE_BYTES = 256 * 1024 * 1024
MAX_TILE_PAYLOAD_BYTES = 4 * 1024 * 1024
MAP_USER_AGENT = "AI-Location-Finder/1.0 (+https://fleece.lol)"
TILE_REQUEST_DEBOUNCE_MS = 90
CONTROL_FRAME_PADDING = 4
CONTROL_BUTTON_GAP = 3
CONTROL_BUTTON_HEIGHT = 34
ZOOM_BUTTON_WIDTH = 36
WORLD_BUTTON_WIDTH = 58
LAYER_BUTTON_WIDTH = 72

_ALLOWED_TILE_HOSTS = frozenset(
    (
        "tile.openstreetmap.org",
        "services.arcgisonline.com",
    )
)
_TILE_REDIRECT_POLICY = QNetworkRequest.ManualRedirectPolicy

TileKey = tuple[str, int, int, int, str]


def _qt_object_token(qt_object) -> int:
    """Return one identity for a Qt object even if PySide creates another wrapper."""

    if not shiboken6.isValid(qt_object):
        return id(qt_object)
    try:
        pointer = shiboken6.getCppPointer(qt_object)
    except (RuntimeError, TypeError):
        pointer = ()
    return int(pointer[0]) if pointer else id(qt_object)


def _validated_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as error:
        raise ValueError("Latitude and longitude must be numbers.") from error

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Latitude and longitude must be finite numbers.")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    return latitude, longitude


def _validated_layer(layer: str) -> str:
    layer = str(layer or "").strip().lower()
    if layer not in VALID_LAYERS:
        raise ValueError(f"Unknown map layer: {layer or '(empty)'}")
    return layer


def coordinate_to_scene(latitude: float, longitude: float) -> QPointF:
    """Project WGS84 coordinates onto the equirectangular fallback map."""

    latitude, longitude = _validated_coordinates(latitude, longitude)
    return QPointF(
        (longitude + 180.0) / 360.0 * MAP_SCENE_RECT.width(),
        (90.0 - latitude) / 180.0 * MAP_SCENE_RECT.height(),
    )


def _mercator_project(latitude: float, longitude: float, zoom: float) -> QPointF:
    """Project WGS84 coordinates to global Web Mercator pixels."""

    latitude, longitude = _validated_coordinates(latitude, longitude)
    latitude = max(-WEB_MERCATOR_MAX_LATITUDE, min(WEB_MERCATOR_MAX_LATITUDE, latitude))
    world_size = TILE_SIZE * (2.0 ** float(zoom))
    sin_latitude = math.sin(math.radians(latitude))
    x = (longitude + 180.0) / 360.0 * world_size
    y = (
        0.5
        - math.log((1.0 + sin_latitude) / (1.0 - sin_latitude)) / (4.0 * math.pi)
    ) * world_size
    return QPointF(x, y)


def _mercator_unproject(x: float, y: float, zoom: float) -> tuple[float, float]:
    """Convert global Web Mercator pixels back to WGS84 coordinates."""

    world_size = TILE_SIZE * (2.0 ** float(zoom))
    x = float(x) % world_size
    y = max(0.0, min(world_size, float(y)))
    longitude = x / world_size * 360.0 - 180.0
    latitude = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / world_size))))
    return latitude, longitude


def _regional_result_zoom(
    latitude: float,
    viewport_width: float,
    viewport_height: float,
) -> float:
    """Return a regional result zoom fitted to the current viewport."""

    latitude, _ = _validated_coordinates(latitude, 0.0)
    mercator_latitude = max(
        -WEB_MERCATOR_MAX_LATITUDE,
        min(WEB_MERCATOR_MAX_LATITUDE, latitude),
    )
    width = max(1.0, float(viewport_width))
    height = max(1.0, float(viewport_height))
    pixels_per_km = min(
        width / RESULT_FRAME_WIDTH_KM,
        height / RESULT_FRAME_HEIGHT_KM,
    )
    local_circumference_km = (
        2.0
        * math.pi
        * EARTH_RADIUS_KM
        * max(0.01, math.cos(math.radians(mercator_latitude)))
    )
    fitted_world_pixels = max(
        1.0,
        local_circumference_km * pixels_per_km,
    )
    fitted_zoom = math.log2(fitted_world_pixels / float(TILE_SIZE))
    return max(RESULT_MIN_ZOOM, min(RESULT_MAX_ZOOM, fitted_zoom))


def verify_map_asset(asset_path: Path | str = MAP_ASSET_PATH) -> bool:
    """Return whether *asset_path* is the expected Natural Earth map."""

    path = Path(asset_path)
    try:
        if not path.is_file() or path.stat().st_size < 100_000:
            return False
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest.lower() != MAP_ASSET_SHA256:
            return False

        reader = QImageReader(str(path))
        if not reader.canRead() or bytes(reader.format()).lower() != b"png":
            return False
        if reader.size().width() != MAP_ASSET_WIDTH:
            return False
        if reader.size().height() != MAP_ASSET_HEIGHT:
            return False
        if "Natural Earth Vector v5.1.2" not in reader.text("Source"):
            return False
        return "public domain" in reader.text("License").lower()
    except (OSError, ValueError):
        return False


def _fallback_pixmap() -> QPixmap:
    """Create a low-detail world map if the bundled image is unavailable."""

    width = 1440
    height = 720
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor("#080c11"))

    def point(longitude: float, latitude: float) -> QPointF:
        return QPointF(
            (longitude + 180.0) / 360.0 * width,
            (90.0 - latitude) / 180.0 * height,
        )

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#17212a"), 1.0))
    for longitude in range(-150, 180, 30):
        x = point(longitude, 0.0).x()
        painter.drawLine(QPointF(x, 0.0), QPointF(x, float(height)))
    for latitude in range(-60, 90, 30):
        y = point(0.0, latitude).y()
        painter.drawLine(QPointF(0.0, y), QPointF(float(width), y))

    continents = [
        [
            (-168, 70), (-140, 58), (-130, 50), (-120, 35), (-105, 25),
            (-90, 18), (-78, 9), (-60, 25), (-52, 48), (-78, 60),
            (-110, 72), (-140, 72),
        ],
        [
            (-82, 12), (-70, 7), (-58, -5), (-48, -24), (-55, -38),
            (-68, -55), (-76, -40), (-78, -18),
        ],
        [
            (-10, 36), (5, 58), (38, 70), (85, 74), (145, 60),
            (170, 52), (145, 36), (120, 18), (102, 4), (78, 8),
            (58, 23), (38, 31), (20, 34), (10, 42),
        ],
        [
            (-18, 35), (5, 36), (32, 30), (48, 10), (40, -12),
            (27, -34), (10, -36), (-3, -20), (-10, 4),
        ],
        [(112, -11), (132, -12), (153, -27), (145, -42), (122, -40), (113, -27)],
        [(-55, 59), (-28, 70), (-22, 82), (-48, 84), (-70, 76)],
        [
            (-180, -72), (-120, -70), (-60, -76), (0, -72),
            (60, -75), (120, -70), (180, -73), (180, -90), (-180, -90),
        ],
    ]
    painter.setPen(QPen(QColor("#46525d"), 1.4))
    painter.setBrush(QColor("#283139"))
    for coordinates in continents:
        painter.drawPolygon(QPolygonF([point(lon, lat) for lon, lat in coordinates]))

    painter.setPen(QColor("#7c8791"))
    painter.drawText(
        QRectF(0.0, 12.0, float(width), 34.0),
        Qt.AlignHCenter | Qt.AlignTop,
        "Offline map detail unavailable",
    )
    painter.end()
    return QPixmap.fromImage(image)


def _tile_url(key: TileKey) -> QUrl:
    layer, zoom, x, y, kind = key
    layer = _validated_layer(layer)
    if layer == LAYER_STREET:
        if kind != "base":
            raise ValueError("The street layer has no overlay tile kind.")
        return QUrl(f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png")

    services = {
        "base": "World_Imagery",
        "transport": "Reference/World_Transportation",
        "labels": "Reference/World_Boundaries_and_Places",
    }
    service = services.get(kind)
    if service is None:
        raise ValueError(f"Unknown satellite tile kind: {kind}")
    return QUrl(
        "https://services.arcgisonline.com/ArcGIS/rest/services/"
        f"{service}/MapServer/tile/{zoom}/{y}/{x}"
    )


def _decode_tile_pixmap(data: bytes) -> Optional[QPixmap]:
    """Decode one provider tile after validating its header and exact dimensions."""

    if not 80 <= len(data) <= MAX_TILE_PAYLOAD_BYTES:
        return None
    buffer = QBuffer()
    buffer.setData(data)
    if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
        return None
    try:
        reader = QImageReader(buffer)
        reader.setDecideFormatFromContent(True)
        if not reader.canRead():
            return None
        if bytes(reader.format()).lower() not in (b"png", b"jpeg", b"jpg"):
            return None
        if reader.size() != QSize(TILE_SIZE, TILE_SIZE):
            return None
        image = reader.read()
        if image.isNull() or image.size() != QSize(TILE_SIZE, TILE_SIZE):
            return None
        pixmap = QPixmap.fromImage(image)
        return None if pixmap.isNull() else pixmap
    finally:
        buffer.close()


class _MapSymbolButton(QPushButton):
    """Draw a crisp zoom symbol without depending on font glyph placement."""

    def __init__(self, symbol: str, parent=None):
        if symbol not in ("-", "+"):
            raise ValueError("Map symbol buttons support only plus and minus.")
        super().__init__("", parent)
        self._symbol = symbol

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor("#eceff2") if self.isEnabled() else QColor("#818b95")
        pen = QPen(color, 2.2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        if self.isDown():
            center += QPointF(0.0, 1.0)
        half_length = 5.5
        painter.drawLine(
            QPointF(center.x() - half_length, center.y()),
            QPointF(center.x() + half_length, center.y()),
        )
        if self._symbol == "+":
            painter.drawLine(
                QPointF(center.x(), center.y() - half_length),
                QPointF(center.x(), center.y() + half_length),
            )
        painter.end()


class WorldMapView(QWidget):
    """Interactive street and satellite map with a local fallback underneath."""

    detail_ready_changed = Signal(bool)
    layer_changed = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        asset_path: Path | str = MAP_ASSET_PATH,
        online_enabled: Optional[bool] = None,
    ):
        super().__init__(parent)
        self._asset_path = Path(asset_path)
        self._asset_valid = verify_map_asset(self._asset_path)
        self._map_pixmap = (
            QPixmap(str(self._asset_path)) if self._asset_valid else _fallback_pixmap()
        )
        if self._map_pixmap.isNull():
            self._map_pixmap = _fallback_pixmap()
            self._asset_valid = False

        if online_enabled is None:
            online_enabled = not any(
                flag in sys.argv for flag in ("--self-test", "--screenshot")
            )
        self._online_enabled = bool(online_enabled)
        self._online_ready = False
        self._live_detail_seen = False
        self._failure_fallback_active = False
        self._closing = False
        self._active_layer = LAYER_STREET
        self._center_latitude = 0.0
        self._center_longitude = 0.0
        self._zoom = MIN_ZOOM
        self._location: Optional[tuple[float, float]] = None
        self._location_name = ""
        self._coordinate_label = ""
        self._location_label_text = ""
        self._confidence_km: Optional[float] = None
        self._drag_position: Optional[QPointF] = None

        self._tiles: OrderedDict[TileKey, QPixmap] = OrderedDict()
        self._pending: dict[TileKey, QNetworkReply] = {}
        self._pending_by_reply_id: dict[int, TileKey] = {}
        self._failed_until: dict[TileKey, float] = {}
        self._network_request_count = 0
        self._network_manager: Optional[QNetworkAccessManager] = None
        self._network_cache: Optional[QNetworkDiskCache] = None
        self._desired_tile_keys: list[TileKey] = []
        self._tile_request_timer = QTimer(self)
        self._tile_request_timer.setSingleShot(True)
        self._tile_request_timer.setInterval(TILE_REQUEST_DEBOUNCE_MS)
        self._tile_request_timer.timeout.connect(self._dispatch_tile_requests)
        self._tile_retry_timer = QTimer(self)
        self._tile_retry_timer.setSingleShot(True)
        self._tile_retry_timer.timeout.connect(self._retry_failed_visible_tiles)
        if self._online_enabled:
            self._build_network()

        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setStyleSheet(
            "WorldMapView { background: #080c11; border: 1px solid #252b32; "
            "border-radius: 12px; }"
        )
        self._build_overlays()
        self.reset_world()

    @property
    def online_enabled(self) -> bool:
        return self._online_enabled

    @property
    def using_fallback(self) -> bool:
        return self._should_draw_offline_map()

    @property
    def detail_ready(self) -> bool:
        return self._online_ready

    @property
    def map_asset_valid(self) -> bool:
        return self._asset_valid

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    @property
    def active_layer(self) -> str:
        return self._active_layer

    @property
    def has_location(self) -> bool:
        return self._location is not None

    @property
    def current_location(self) -> Optional[tuple[float, float]]:
        return self._location

    @property
    def network_request_count(self) -> int:
        return self._network_request_count

    @property
    def privacy_summary(self) -> str:
        if not self._online_enabled:
            return "Offline map mode makes no tile requests."
        provider = "OpenStreetMap" if self._active_layer == LAYER_STREET else "Esri"
        return (
            f"Only the visible map area is requested from {provider}. "
            "No image, AI prompt, API key, or analysis report is sent to the map provider."
        )

    def _build_network(self):
        manager = QNetworkAccessManager(self)
        manager.setTransferTimeout(NETWORK_TIMEOUT_MS)
        manager.setStrictTransportSecurityEnabled(True)
        manager.setAutoDeleteReplies(False)
        manager.finished.connect(self._network_reply_finished)

        cache = QNetworkDiskCache(manager)
        cache_root = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
        cache_path = str(
            Path(cache_root or str(MODULE_DIR / ".runtime"))
            / "fleece.lol"
            / "AI Location Finder"
            / "map-tiles"
        )
        cache.setCacheDirectory(cache_path)
        cache.setMaximumCacheSize(NETWORK_CACHE_BYTES)
        manager.setCache(cache)
        self._network_manager = manager
        self._network_cache = cache

    def _build_overlays(self):
        self._controls = QFrame(self)
        self._controls.setObjectName("mapZoomControls")

        self._zoom_out_button = _MapSymbolButton("-", self._controls)
        self._zoom_out_button.setAccessibleName("Zoom map out")
        self._zoom_out_button.setToolTip("Zoom out")
        self._zoom_out_button.clicked.connect(self.zoom_out)
        self._zoom_in_button = _MapSymbolButton("+", self._controls)
        self._zoom_in_button.setAccessibleName("Zoom map in")
        self._zoom_in_button.setToolTip("Zoom in")
        self._zoom_in_button.clicked.connect(self.zoom_in)
        self._world_button = QPushButton("World", self._controls)
        self._world_button.setAccessibleName("Show the whole world")
        self._world_button.setToolTip("Show the whole world")
        self._world_button.clicked.connect(self.reset_world)
        zoom_frame_height = CONTROL_BUTTON_HEIGHT + 2 * CONTROL_FRAME_PADDING
        zoom_frame_width = (
            2 * CONTROL_FRAME_PADDING
            + 2 * ZOOM_BUTTON_WIDTH
            + WORLD_BUTTON_WIDTH
            + 2 * CONTROL_BUTTON_GAP
        )
        self._controls.setFixedSize(zoom_frame_width, zoom_frame_height)
        zoom_x = CONTROL_FRAME_PADDING
        for button in (self._zoom_out_button, self._zoom_in_button):
            button.setFixedSize(ZOOM_BUTTON_WIDTH, CONTROL_BUTTON_HEIGHT)
            button.move(zoom_x, CONTROL_FRAME_PADDING)
            zoom_x += ZOOM_BUTTON_WIDTH + CONTROL_BUTTON_GAP
        self._world_button.setFixedSize(WORLD_BUTTON_WIDTH, CONTROL_BUTTON_HEIGHT)
        self._world_button.move(zoom_x, CONTROL_FRAME_PADDING)

        self._layer_controls = QFrame(self)
        self._layer_controls.setObjectName("mapLayerControls")
        self._street_button = QPushButton("Street", self._layer_controls)
        self._satellite_button = QPushButton("Satellite", self._layer_controls)
        layer_frame_height = CONTROL_BUTTON_HEIGHT + 2 * CONTROL_FRAME_PADDING
        layer_frame_width = (
            2 * CONTROL_FRAME_PADDING
            + 2 * LAYER_BUTTON_WIDTH
            + CONTROL_BUTTON_GAP
        )
        self._layer_controls.setFixedSize(layer_frame_width, layer_frame_height)
        layer_x = CONTROL_FRAME_PADDING
        for button in (self._street_button, self._satellite_button):
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setFixedSize(LAYER_BUTTON_WIDTH, CONTROL_BUTTON_HEIGHT)
            button.move(layer_x, CONTROL_FRAME_PADDING)
            layer_x += LAYER_BUTTON_WIDTH + CONTROL_BUTTON_GAP
        self._street_button.setChecked(True)
        self._street_button.setToolTip(
            "Detailed roads, buildings, landmarks, and place labels from OpenStreetMap"
        )
        self._satellite_button.setToolTip(
            "Esri satellite imagery with road, transportation, and place labels"
        )
        self._street_button.clicked.connect(
            lambda checked: checked and self.set_layer(LAYER_STREET)
        )
        self._satellite_button.clicked.connect(
            lambda checked: checked and self.set_layer(LAYER_SATELLITE)
        )

        controls_style = (
            "QFrame#mapZoomControls, QFrame#mapLayerControls { "
            "background: rgba(8, 12, 17, 238); border: 1px solid #3a434d; "
            "border-radius: 9px; }"
            "QFrame#mapZoomControls QPushButton, QFrame#mapLayerControls QPushButton { "
            "background: #141a21; color: #f0f2f4; border: none; "
            "border-radius: 6px; padding: 0; min-height: 34px; max-height: 34px; "
            "font-family: 'Segoe UI'; "
            "font-size: 11px; font-weight: 600; }"
            "QFrame#mapZoomControls QPushButton:hover, "
            "QFrame#mapLayerControls QPushButton:hover { background: #222b34; }"
            "QFrame#mapZoomControls QPushButton:pressed, "
            "QFrame#mapLayerControls QPushButton:pressed { background: #0d1218; }"
            "QFrame#mapLayerControls QPushButton:checked { background: #f2f3f4; "
            "color: #090d12; }"
            "QFrame#mapZoomControls QPushButton:disabled { color: #68737e; "
            "background: #0e141a; }"
        )
        self._controls.setStyleSheet(controls_style)
        self._layer_controls.setStyleSheet(controls_style)

        self._location_label = QLabel(self)
        self._location_label.setObjectName("mapLocation")
        self._location_label.setTextFormat(Qt.PlainText)
        self._location_label.setWordWrap(False)
        self._location_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._location_label.setStyleSheet(
            "QLabel#mapLocation { background: rgba(8, 12, 17, 232); color: #f4f5f6; "
            "border: 1px solid #303841; border-radius: 7px; padding: 6px 9px; "
            "font: 600 11px 'Segoe UI'; }"
        )
        self._location_label.hide()

        self._status_label = QLabel(self)
        self._status_label.setObjectName("mapStatus")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._status_label.setStyleSheet(
            "QLabel#mapStatus { background: rgba(8, 12, 17, 225); color: #c6ced6; "
            "border: 1px solid #303841; border-radius: 7px; padding: 5px 8px; "
            "font: 10px 'Segoe UI'; }"
        )

        self._attribution_label = QLabel(self)
        self._attribution_label.setObjectName("mapAttribution")
        self._attribution_label.setTextFormat(Qt.RichText)
        self._attribution_label.setOpenExternalLinks(True)
        self._attribution_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self._attribution_label.setWordWrap(True)
        self._attribution_label.setStyleSheet(
            "QLabel#mapAttribution { background: rgba(8, 12, 17, 225); "
            "color: #aeb7c0; border: 1px solid #29313a; border-radius: 6px; "
            "padding: 3px 6px; font: 9px 'Segoe UI'; }"
            "QLabel#mapAttribution a { color: #d3d9df; text-decoration: none; }"
        )
        self._update_overlay_texts()

    def _update_overlay_texts(self):
        if self._should_draw_offline_map():
            self._attribution_label.setText(
                f"Natural Earth, public domain | <a href='{MAP_TERMS_URL}'>terms</a>"
            )
        elif self._active_layer == LAYER_STREET:
            self._attribution_label.setText(
                f"<a href='{OSM_COPYRIGHT_URL}'>© OpenStreetMap contributors</a>"
            )
        else:
            self._attribution_label.setText(
                "<a href='https://www.esri.com/'>Esri</a>, Vantor, Earthstar "
                "Geographics, HERE, Garmin, OpenStreetMap contributors, and the "
                "GIS User Community"
            )

        if not self._online_enabled:
            self._status_label.setText("Offline map")
            self._status_label.show()
        elif self._online_ready:
            self._status_label.hide()
        else:
            layer_name = (
                "street details"
                if self._active_layer == LAYER_STREET
                else "satellite details"
            )
            unavailable = (
                self._failure_fallback_active
                or self._visible_base_unavailable()
            )
            self._status_label.setText(
                "Online details unavailable, showing offline map"
                if unavailable
                else f"Loading {layer_name}..."
            )
            self._status_label.show()
        self._attribution_label.setToolTip(self.privacy_summary)
        self._layout_overlays()

    def _layout_overlays(self):
        if not hasattr(self, "_controls"):
            return
        viewport = self.rect()
        margin = 10
        self._controls.move(margin, margin)

        layer_x = viewport.width() - self._layer_controls.width() - margin
        layer_y = margin
        if layer_x <= self._controls.geometry().right() + 8:
            layer_x = margin
            layer_y = self._controls.geometry().bottom() + 8
        self._layer_controls.move(max(margin, layer_x), layer_y)

        max_attribution_width = max(180, min(560, viewport.width() - 2 * margin))
        self._attribution_label.setMaximumWidth(max_attribution_width)
        self._attribution_label.adjustSize()
        self._attribution_label.move(
            max(margin, viewport.width() - self._attribution_label.width() - margin),
            max(margin, viewport.height() - self._attribution_label.height() - margin),
        )

        if not self._status_label.isHidden():
            self._status_label.adjustSize()
            self._status_label.move(
                max(margin, (viewport.width() - self._status_label.width()) // 2),
                max(
                    margin,
                    self._attribution_label.geometry().top()
                    - self._status_label.height()
                    - 7,
                ),
            )

        if not self._location_label.isHidden():
            location_width = max(180, min(380, viewport.width() - 2 * margin))
            self._location_label.setMaximumWidth(location_width)
            available_text_width = max(120, location_width - 24)
            visible_name = self._location_label.fontMetrics().elidedText(
                self._location_name,
                Qt.ElideRight,
                available_text_width,
            )
            self._location_label.setText(
                f"{visible_name}\n{self._coordinate_label}"
                if visible_name
                else self._coordinate_label
            )
            self._location_label.adjustSize()
            bottom_limit = self._attribution_label.geometry().top() - 8
            if not self._status_label.isHidden():
                bottom_limit = min(bottom_limit, self._status_label.geometry().top() - 8)
            self._location_label.move(
                margin,
                max(
                    self._layer_controls.geometry().bottom() + 8,
                    bottom_limit - self._location_label.height(),
                ),
            )

        for overlay in (
            self._controls,
            self._layer_controls,
            self._location_label,
            self._status_label,
            self._attribution_label,
        ):
            overlay.raise_()

    def coordinate_to_scene(self, latitude: float, longitude: float) -> QPointF:
        return coordinate_to_scene(latitude, longitude)

    def set_location(
        self,
        latitude: float,
        longitude: float,
        label: str = "",
        confidence_km: Optional[float] = None,
    ):
        latitude, longitude = _validated_coordinates(latitude, longitude)
        self._location = (latitude, longitude)
        self._center_latitude = latitude
        self._center_longitude = longitude
        self._zoom = self._result_zoom_for_viewport(latitude)

        try:
            confidence = float(confidence_km) if confidence_km is not None else None
        except (TypeError, ValueError):
            confidence = None
        self._confidence_km = (
            confidence
            if confidence is not None and math.isfinite(confidence) and confidence > 0.0
            else None
        )

        display_label = " ".join(str(label or "").split())
        coordinate_label = f"{latitude:.5f}, {longitude:.5f}"
        self._location_name = display_label
        self._coordinate_label = coordinate_label
        self._location_label_text = (
            f"{display_label}\n{coordinate_label}" if display_label else coordinate_label
        )
        self._location_label.setText(self._location_label_text)
        self._location_label.setToolTip(self._location_label_text)
        self._location_label.show()
        self._prepare_view_change()

    def clear_location(self):
        self._location = None
        self._location_name = ""
        self._coordinate_label = ""
        self._location_label_text = ""
        self._location_label.setToolTip("")
        self._confidence_km = None
        self._location_label.hide()
        self.reset_world()

    def _minimum_zoom_for_viewport(self) -> float:
        """Return the lowest zoom that keeps one world covering the viewport."""

        largest_dimension = max(1.0, float(self.width()), float(self.height()))
        fit_zoom = math.log2(largest_dimension / float(TILE_SIZE))
        return max(MIN_ZOOM, min(MAX_ZOOM, fit_zoom))

    def _result_zoom_for_viewport(self, latitude: float) -> float:
        fitted_zoom = _regional_result_zoom(latitude, self.width(), self.height())
        return max(self._minimum_zoom_for_viewport(), fitted_zoom)

    def _bounded_world_center(self, center: QPointF, zoom: float) -> QPointF:
        """Clamp a global-pixel center so no edge can expose empty map space."""

        world_size = TILE_SIZE * (2.0 ** float(zoom))
        width = max(1.0, float(self.width()))
        height = max(1.0, float(self.height()))

        x = float(center.x())
        y = float(center.y())
        if not math.isfinite(x):
            x = world_size / 2.0
        if not math.isfinite(y):
            y = world_size / 2.0

        if world_size <= width:
            x = world_size / 2.0
        else:
            half_width = width / 2.0
            x = max(half_width, min(world_size - half_width, x))

        if world_size <= height:
            y = world_size / 2.0
        else:
            half_height = height / 2.0
            y = max(half_height, min(world_size - half_height, y))
        return QPointF(x, y)

    def _set_center_from_world(self, center: QPointF, zoom: Optional[float] = None):
        selected_zoom = self._zoom if zoom is None else float(zoom)
        bounded = self._bounded_world_center(center, selected_zoom)
        self._center_latitude, self._center_longitude = _mercator_unproject(
            bounded.x(), bounded.y(), selected_zoom
        )

    def _constrain_view(self):
        """Normalize zoom and center after every state or viewport change."""

        minimum_zoom = self._minimum_zoom_for_viewport()
        if not math.isfinite(self._zoom):
            self._zoom = minimum_zoom
        self._zoom = max(minimum_zoom, min(MAX_ZOOM, float(self._zoom)))

        if not math.isfinite(self._center_latitude):
            self._center_latitude = 0.0
        if not math.isfinite(self._center_longitude):
            self._center_longitude = 0.0
        self._center_latitude = max(
            -WEB_MERCATOR_MAX_LATITUDE,
            min(WEB_MERCATOR_MAX_LATITUDE, float(self._center_latitude)),
        )
        self._center_longitude = max(
            -180.0, min(180.0, float(self._center_longitude))
        )
        center = _mercator_project(
            self._center_latitude, self._center_longitude, self._zoom
        )
        self._set_center_from_world(center)

    def reset_world(self):
        self._center_latitude = 0.0
        self._center_longitude = 0.0
        self._zoom = self._minimum_zoom_for_viewport()
        self._prepare_view_change()

    def set_layer(self, layer: str):
        layer = _validated_layer(layer)
        if layer == self._active_layer:
            return
        self._active_layer = layer
        self._street_button.setChecked(layer == LAYER_STREET)
        self._satellite_button.setChecked(layer == LAYER_SATELLITE)
        self._prepare_view_change()
        self.layer_changed.emit(layer)

    def show_street(self):
        self.set_layer(LAYER_STREET)

    def show_satellite(self):
        self.set_layer(LAYER_SATELLITE)

    def zoom_in(self):
        self._set_zoom(self._zoom + ZOOM_STEP)

    def zoom_out(self):
        self._set_zoom(self._zoom - ZOOM_STEP)

    def _set_zoom(self, value: float, anchor: Optional[QPointF] = None):
        try:
            requested = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(requested):
            return
        target = max(self._minimum_zoom_for_viewport(), min(MAX_ZOOM, requested))
        if math.isclose(target, self._zoom, abs_tol=1e-9):
            return

        if anchor is None:
            anchor = QPointF(self.width() / 2.0, self.height() / 2.0)
        else:
            anchor = QPointF(
                max(0.0, min(float(self.width()), float(anchor.x()))),
                max(0.0, min(float(self.height()), float(anchor.y()))),
            )
        old_center = _mercator_project(
            self._center_latitude, self._center_longitude, self._zoom
        )
        screen_offset = anchor - QPointF(self.width() / 2.0, self.height() / 2.0)
        anchored_world = old_center + screen_offset
        anchor_latitude, anchor_longitude = _mercator_unproject(
            anchored_world.x(), anchored_world.y(), self._zoom
        )

        self._zoom = target
        new_anchor_world = _mercator_project(anchor_latitude, anchor_longitude, target)
        new_center = new_anchor_world - screen_offset
        self._set_center_from_world(new_center, target)
        self._prepare_view_change()

    def _prepare_view_change(self):
        self._constrain_view()
        self._retire_nonvisible_pending()
        self._prune_failed_tiles()
        self._failure_fallback_active = self._visible_base_unavailable()
        was_ready = self._online_ready
        self._online_ready = self._has_cached_visible_base_tile()
        if was_ready != self._online_ready:
            self.detail_ready_changed.emit(self._online_ready)
        self._zoom_out_button.setEnabled(
            self._zoom > self._minimum_zoom_for_viewport() + 1e-6
        )
        self._zoom_in_button.setEnabled(self._zoom < MAX_ZOOM - 1e-6)
        self._update_overlay_texts()
        self.update()

    def _cancel_pending(self):
        self._tile_request_timer.stop()
        self._tile_retry_timer.stop()
        self._desired_tile_keys.clear()
        pending = list(self._pending.values())
        self._pending.clear()
        self._pending_by_reply_id.clear()
        for reply in pending:
            if not shiboken6.isValid(reply):
                continue
            try:
                if reply.isRunning():
                    reply.abort()
            except RuntimeError:
                continue
            self._dispose_reply(reply)

    def _retire_nonvisible_pending(self):
        """Abort stale requests so rapid navigation cannot starve the new view."""

        self._tile_request_timer.stop()
        self._tile_retry_timer.stop()
        self._desired_tile_keys.clear()
        if not self._pending:
            return
        visible = {key for key, _rectangle in self._visible_tile_entries()}
        stale = [key for key in self._pending if key not in visible]
        for key in stale:
            reply = self._pending.pop(key, None)
            if reply is None:
                continue
            self._pending_by_reply_id.pop(_qt_object_token(reply), None)
            if not shiboken6.isValid(reply):
                continue
            try:
                if reply.isRunning():
                    reply.abort()
            except RuntimeError:
                continue
            self._dispose_reply(reply)

    def _prune_failed_tiles(self):
        if not self._failed_until:
            return
        now = time.monotonic()
        expired = [key for key, retry_at in self._failed_until.items() if retry_at <= now]
        for key in expired:
            self._failed_until.pop(key, None)

    def _record_tile_failure(self, key: TileKey):
        """Remember a transient failure without allowing navigation to grow state forever."""

        self._prune_failed_tiles()
        self._failed_until.pop(key, None)
        self._failed_until[key] = time.monotonic() + FAILED_TILE_RETRY_SECONDS
        while len(self._failed_until) > MAX_FAILED_TILES:
            self._failed_until.pop(next(iter(self._failed_until)), None)

    @staticmethod
    def _dispose_reply(reply):
        """Schedule a live Qt reply for deletion without touching stale wrappers."""

        if not shiboken6.isValid(reply):
            return
        try:
            reply.deleteLater()
        except RuntimeError:
            # Qt can destroy a reply between a queued signal and Python dispatch.
            return

    def _network_reply_destroyed(self, reply_id: int):
        """Remove capacity bookkeeping even if Qt destroys a reply unexpectedly."""

        key = self._pending_by_reply_id.pop(reply_id, None)
        if key is None:
            return
        current = self._pending.get(key)
        if current is not None and _qt_object_token(current) == reply_id:
            self._pending.pop(key, None)

    def _forget_reply_key(self, key: TileKey):
        stale_ids = [
            reply_id
            for reply_id, mapped_key in self._pending_by_reply_id.items()
            if mapped_key == key
        ]
        for reply_id in stale_ids:
            self._pending_by_reply_id.pop(reply_id, None)

    def _network_reply_finished(self, reply: QNetworkReply):
        """Resolve QNAM completion without a callback retaining the reply wrapper."""

        reply_id = _qt_object_token(reply)
        key = self._pending_by_reply_id.pop(reply_id, None)
        if key is None:
            self._dispose_reply(reply)
            return
        current = self._pending.get(key)
        if current is None or _qt_object_token(current) != reply_id:
            self._dispose_reply(reply)
            return
        self._pending.pop(key, None)
        self._tile_finished(key, reply, bookkeeping_resolved=True)

    def _has_cached_base_for_layer(self, layer: Optional[str] = None) -> bool:
        selected_layer = self._active_layer if layer is None else _validated_layer(layer)
        return any(key[0] == selected_layer and key[-1] == "base" for key in self._tiles)

    def _should_draw_offline_map(self) -> bool:
        """Use offline artwork only initially, offline, or after a real tile outage."""

        return (
            not self._online_enabled
            or not self._live_detail_seen
            or self._failure_fallback_active
        )

    def _visible_base_unavailable(
        self,
        entries: Optional[list[tuple[TileKey, QRectF]]] = None,
    ) -> bool:
        """Return whether every visible base tile is in a failure cooldown."""

        visible_entries = self._visible_tile_entries() if entries is None else entries
        visible_base = {key for key, _ in visible_entries if key[-1] == "base"}
        now = time.monotonic()
        return bool(visible_base) and all(
            self._failed_until.get(key, 0.0) > now for key in visible_base
        )

    def _cached_base_fallback(
        self,
        painter: QPainter,
        key: TileKey,
        target: QRectF,
    ) -> bool:
        """Draw same-layer cached detail while a replacement base tile loads."""

        layer, zoom, x, y, kind = key
        if kind != "base":
            return False

        for ancestor_zoom in range(zoom - 1, -1, -1):
            subdivisions = 1 << (zoom - ancestor_zoom)
            ancestor_key = (
                layer,
                ancestor_zoom,
                x // subdivisions,
                y // subdivisions,
                "base",
            )
            pixmap = self._tiles.get(ancestor_key)
            if pixmap is None:
                continue
            self._tiles.move_to_end(ancestor_key)
            source_width = pixmap.width() / subdivisions
            source_height = pixmap.height() / subdivisions
            source = QRectF(
                (x % subdivisions) * source_width,
                (y % subdivisions) * source_height,
                source_width,
                source_height,
            )
            painter.drawPixmap(target, pixmap, source)
            return True

        for descendant_zoom in range(zoom + 1, min(int(MAX_ZOOM), zoom + 2) + 1):
            subdivisions = 1 << (descendant_zoom - zoom)
            fragment_width = target.width() / subdivisions
            fragment_height = target.height() / subdivisions
            drew_fragment = False
            for fragment_y in range(subdivisions):
                for fragment_x in range(subdivisions):
                    descendant_key = (
                        layer,
                        descendant_zoom,
                        x * subdivisions + fragment_x,
                        y * subdivisions + fragment_y,
                        "base",
                    )
                    pixmap = self._tiles.get(descendant_key)
                    if pixmap is None:
                        continue
                    self._tiles.move_to_end(descendant_key)
                    fragment = QRectF(
                        target.left() + fragment_x * fragment_width,
                        target.top() + fragment_y * fragment_height,
                        fragment_width + 0.5,
                        fragment_height + 0.5,
                    )
                    painter.drawPixmap(fragment, pixmap, QRectF(pixmap.rect()))
                    drew_fragment = True
            if drew_fragment:
                return True
        return False

    def _visible_tile_entries(self) -> list[tuple[TileKey, QRectF]]:
        width = max(1.0, float(self.width()))
        height = max(1.0, float(self.height()))
        tile_zoom = int(math.floor(self._zoom))
        scale = 2.0 ** (self._zoom - tile_zoom)
        displayed_tile_size = TILE_SIZE * scale
        center = _mercator_project(
            self._center_latitude, self._center_longitude, tile_zoom
        ) * scale
        first_x = math.floor((center.x() - width / 2.0) / displayed_tile_size)
        last_x = math.floor((center.x() + width / 2.0) / displayed_tile_size)
        first_y = math.floor((center.y() - height / 2.0) / displayed_tile_size)
        last_y = math.floor((center.y() + height / 2.0) / displayed_tile_size)
        tile_count = 1 << tile_zoom
        kinds = (
            ("base",)
            if self._active_layer == LAYER_STREET
            else ("base", "transport", "labels")
        )

        entries: list[tuple[TileKey, QRectF]] = []
        for kind in kinds:
            for tile_y in range(first_y, last_y + 1):
                if tile_y < 0 or tile_y >= tile_count:
                    continue
                for unwrapped_x in range(first_x, last_x + 1):
                    if unwrapped_x < 0 or unwrapped_x >= tile_count:
                        continue
                    tile_x = unwrapped_x
                    left = (
                        unwrapped_x * displayed_tile_size
                        - center.x()
                        + width / 2.0
                    )
                    top = tile_y * displayed_tile_size - center.y() + height / 2.0
                    key = (self._active_layer, tile_zoom, tile_x, tile_y, kind)
                    entries.append(
                        (
                            key,
                            QRectF(
                                left,
                                top,
                                displayed_tile_size + 0.5,
                                displayed_tile_size + 0.5,
                            ),
                        )
                    )
        return entries

    def _has_cached_visible_base_tile(
        self,
        entries: Optional[list[tuple[TileKey, QRectF]]] = None,
    ) -> bool:
        if not self._online_enabled or not self._tiles:
            return False
        visible_entries = self._visible_tile_entries() if entries is None else entries
        visible_base = {
            key for key, _ in visible_entries if key[-1] == "base"
        }
        return bool(visible_base) and all(key in self._tiles for key in visible_base)

    def _schedule_tile_requests(self, keys: list[TileKey]):
        if self._closing or not self._online_enabled:
            return
        desired = list(keys)
        changed = desired != self._desired_tile_keys
        self._desired_tile_keys = desired
        if not desired:
            self._tile_request_timer.stop()
            self._tile_retry_timer.stop()
            return

        now = time.monotonic()
        can_dispatch = any(
            key not in self._tiles
            and key not in self._pending
            and self._failed_until.get(key, 0.0) <= now
            for key in desired
        )
        if can_dispatch and (changed or not self._tile_request_timer.isActive()):
            self._tile_request_timer.start()
        self._arm_failed_tile_retry()

    def _arm_failed_tile_retry(self):
        """Wake the map when a visible transient-failure cooldown expires."""

        if self._closing or not self._online_enabled:
            self._tile_retry_timer.stop()
            return
        now = time.monotonic()
        deadlines = [
            self._failed_until[key]
            for key in self._desired_tile_keys
            if key not in self._tiles
            and key not in self._pending
            and self._failed_until.get(key, 0.0) > now
        ]
        if not deadlines:
            self._tile_retry_timer.stop()
            return
        delay_ms = max(1, math.ceil((min(deadlines) - now) * 1000.0))
        remaining = self._tile_retry_timer.remainingTime()
        if remaining < 0 or delay_ms < remaining:
            self._tile_retry_timer.start(delay_ms)

    def _retry_failed_visible_tiles(self):
        if self._closing or not self._online_enabled:
            return
        self._prune_failed_tiles()
        self._dispatch_tile_requests()
        self._arm_failed_tile_retry()

    def _dispatch_tile_requests(self):
        if self._closing or not self._online_enabled:
            return
        for key in tuple(self._desired_tile_keys):
            self._request_tile(key)

    def _request_tile(self, key: TileKey):
        manager = self._network_manager
        if (
            manager is None
            or self._closing
            or key in self._pending
            or key in self._tiles
            or len(self._pending) >= MAX_PENDING_TILES
        ):
            return
        now = time.monotonic()
        retry_at = self._failed_until.get(key, 0.0)
        if retry_at > now:
            self._arm_failed_tile_retry()
            return
        if retry_at:
            self._failed_until.pop(key, None)

        url = _tile_url(key)
        if url.scheme() != "https" or url.host().lower() not in _ALLOWED_TILE_HOSTS:
            self._record_tile_failure(key)
            self._arm_failed_tile_retry()
            return

        request = QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", MAP_USER_AGENT.encode("ascii"))
        request.setRawHeader(b"Accept", b"image/png,image/jpeg,image/*;q=0.8")
        request.setAttribute(
            QNetworkRequest.CacheLoadControlAttribute,
            QNetworkRequest.PreferCache,
        )
        request.setAttribute(QNetworkRequest.Http2AllowedAttribute, True)
        request.setAttribute(
            QNetworkRequest.RedirectPolicyAttribute,
            _TILE_REDIRECT_POLICY,
        )
        reply = manager.get(request)
        self._pending[key] = reply
        reply_id = _qt_object_token(reply)
        self._pending_by_reply_id[reply_id] = key
        reply.destroyed.connect(
            lambda _object=None, reply_id=reply_id: self._network_reply_destroyed(
                reply_id
            )
        )
        self._network_request_count += 1

    def _tile_finished(
        self,
        key: TileKey,
        reply: QNetworkReply,
        *,
        bookkeeping_resolved: bool = False,
    ):
        if not bookkeeping_resolved:
            if self._pending.get(key) is not reply:
                self._pending_by_reply_id.pop(_qt_object_token(reply), None)
                self._dispose_reply(reply)
                return
            self._pending.pop(key, None)
            self._forget_reply_key(key)
        if self._closing or not shiboken6.isValid(reply):
            self._dispose_reply(reply)
            return

        try:
            error = reply.error()
            if error == QNetworkReply.OperationCanceledError:
                return

            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            try:
                status_ok = status is None or 200 <= int(status) < 300
            except (TypeError, ValueError):
                status_ok = False
            data = bytes(reply.readAll())
            pixmap = (
                _decode_tile_pixmap(data)
                if error == QNetworkReply.NoError and status_ok
                else None
            )
            if pixmap is not None:
                self._tiles[key] = pixmap
                self._tiles.move_to_end(key)
                self._failed_until.pop(key, None)
                while len(self._tiles) > MAX_MEMORY_TILES:
                    self._tiles.popitem(last=False)
                if key[-1] == "base":
                    self._live_detail_seen = True
                if key[0] == self._active_layer and key[-1] == "base":
                    was_ready = self._online_ready
                    self._online_ready = self._has_cached_visible_base_tile()
                    if self._online_ready:
                        self._failure_fallback_active = False
                    if was_ready != self._online_ready:
                        self.detail_ready_changed.emit(self._online_ready)
                    self._update_overlay_texts()
                self.update()
            else:
                self._record_tile_failure(key)
                if key[0] == self._active_layer and key[-1] == "base":
                    self._failure_fallback_active = self._visible_base_unavailable()
                if self._network_cache is not None:
                    try:
                        self._network_cache.remove(_tile_url(key))
                    except RuntimeError:
                        # Shutdown can invalidate the cache between reply delivery
                        # and this queued callback. The in-memory failure state is
                        # already safe, so cache cleanup is best effort here.
                        pass
                self._arm_failed_tile_retry()
                self._update_overlay_texts()
                self.update()
        except RuntimeError:
            # A reply can be destroyed after its queued completion but before the
            # Python callback runs. Bookkeeping is already clear, so repainting
            # safely permits a future request without crashing the application.
            if not self._closing:
                self.update()
        finally:
            self._dispose_reply(reply)

    def _draw_offline_map(self, painter: QPainter):
        target = QRectF(self.rect())
        pixmap_width = float(self._map_pixmap.width())
        pixmap_height = float(self._map_pixmap.height())
        if self._zoom <= 2.0:
            scale = min(
                target.width() / max(1.0, pixmap_width),
                target.height() / max(1.0, pixmap_height),
            )
            fitted = QRectF(
                0.0,
                0.0,
                pixmap_width * scale,
                pixmap_height * scale,
            )
            fitted.moveCenter(target.center())
            painter.drawPixmap(fitted, self._map_pixmap, QRectF(self._map_pixmap.rect()))
            return

        center = coordinate_to_scene(self._center_latitude, self._center_longitude)
        if self._location is not None:
            world_size = TILE_SIZE * (2.0 ** self._zoom)
            latitude_scale = max(
                0.01,
                math.cos(math.radians(self._center_latitude)),
            )
            source_width = (
                pixmap_width * target.width() / max(1.0, world_size)
            )
            source_height = (
                2.0
                * pixmap_height
                * target.height()
                * latitude_scale
                / max(1.0, world_size)
            )
        else:
            magnification = 2.0 ** min(
                4.0,
                max(0.0, (self._zoom - 2.0) / 4.0),
            )
            source_width = pixmap_width / magnification
            source_height = source_width * target.height() / max(1.0, target.width())
        source_width = max(1.0, min(pixmap_width, source_width))
        source_height = max(1.0, min(pixmap_height, source_height))
        source = QRectF(
            center.x() - source_width / 2.0,
            center.y() - source_height / 2.0,
            source_width,
            source_height,
        )
        source.moveLeft(max(0.0, min(pixmap_width - source.width(), source.left())))
        source.moveTop(max(0.0, min(pixmap_height - source.height(), source.top())))
        painter.drawPixmap(target, self._map_pixmap, source)

    def _draw_tiles(self, painter: QPainter, entries: list[tuple[TileKey, QRectF]]):
        unique_keys: list[TileKey] = []
        seen_keys: set[TileKey] = set()
        for key, rectangle in entries:
            if key not in seen_keys:
                seen_keys.add(key)
                unique_keys.append(key)
            pixmap = self._tiles.get(key)
            if pixmap is not None:
                self._tiles.move_to_end(key)
                painter.drawPixmap(rectangle, pixmap, QRectF(pixmap.rect()))
            elif key[-1] == "base" and self._live_detail_seen:
                if not self._failure_fallback_active:
                    painter.fillRect(rectangle, QColor("#0b1015"))
                self._cached_base_fallback(painter, key, rectangle)

        ready = self._has_cached_visible_base_tile(entries)
        if ready != self._online_ready:
            self._online_ready = ready
            self.detail_ready_changed.emit(ready)
            self._update_overlay_texts()
        if self._online_enabled:
            self._schedule_tile_requests(
                [key for key in unique_keys if key not in self._tiles]
            )

    def _location_screen_point(self) -> Optional[QPointF]:
        if self._location is None:
            return None
        latitude, longitude = self._location
        pin_world = _mercator_project(latitude, longitude, self._zoom)
        center_world = _mercator_project(
            self._center_latitude, self._center_longitude, self._zoom
        )
        world_size = TILE_SIZE * (2.0 ** self._zoom)
        delta_x = pin_world.x() - center_world.x()
        if delta_x > world_size / 2.0:
            delta_x -= world_size
        elif delta_x < -world_size / 2.0:
            delta_x += world_size
        return QPointF(
            self.width() / 2.0 + delta_x,
            self.height() / 2.0 + pin_world.y() - center_world.y(),
        )

    def _draw_location(self, painter: QPainter):
        point = self._location_screen_point()
        if point is None:
            return
        if self._confidence_km and self._location:
            latitude = self._location[0]
            meters_per_pixel = (
                156543.03392
                * max(0.01, math.cos(math.radians(latitude)))
                / (2.0 ** self._zoom)
            )
            radius = self._confidence_km * 1000.0 / meters_per_pixel
            maximum_visible_radius = max(40.0, min(self.width(), self.height()) * 0.48)
            if 1.0 < radius <= maximum_visible_radius:
                painter.setPen(QPen(QColor(242, 95, 92, 210), 1.6))
                painter.setBrush(QColor(242, 95, 92, 42))
                painter.drawEllipse(point, radius, radius)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawEllipse(QRectF(point.x() - 8.0, point.y() - 2.0, 16.0, 5.0))

        pin = QPainterPath()
        pin.moveTo(point)
        pin.cubicTo(
            point.x() - 2.5,
            point.y() - 5.5,
            point.x() - 11.0,
            point.y() - 12.5,
            point.x() - 11.0,
            point.y() - 20.0,
        )
        pin.cubicTo(
            point.x() - 11.0,
            point.y() - 27.0,
            point.x() - 6.0,
            point.y() - 32.0,
            point.x(),
            point.y() - 32.0,
        )
        pin.cubicTo(
            point.x() + 6.0,
            point.y() - 32.0,
            point.x() + 11.0,
            point.y() - 27.0,
            point.x() + 11.0,
            point.y() - 20.0,
        )
        pin.cubicTo(
            point.x() + 11.0,
            point.y() - 12.5,
            point.x() + 2.5,
            point.y() - 5.5,
            point.x(),
            point.y(),
        )
        pin.closeSubpath()
        painter.setPen(QPen(QColor("#ffffff"), 1.4))
        painter.setBrush(QColor("#f25f5c"))
        painter.drawPath(pin)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(point.x() - 3.4, point.y() - 23.4, 6.8, 6.8))

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(frame, 11.0, 11.0)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor("#080c11"))
        entries = self._visible_tile_entries()
        if self._should_draw_offline_map():
            self._draw_offline_map(painter)
        self._draw_tiles(painter, entries)
        self._draw_location(painter)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#252b32"), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(frame, 11.0, 11.0)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_position is not None and event.buttons() & Qt.LeftButton:
            delta = event.position() - self._drag_position
            self._drag_position = event.position()
            center = _mercator_project(
                self._center_latitude, self._center_longitude, self._zoom
            ) - delta
            self._set_center_from_world(center)
            self._prepare_view_change()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._drag_position is not None:
            self._drag_position = None
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._set_zoom(self._zoom + ZOOM_STEP, event.position())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if not delta:
            event.ignore()
            return
        steps = delta / 120.0
        self._set_zoom(self._zoom + steps * ZOOM_STEP, event.position())
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_in()
            event.accept()
            return
        if event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
            self.zoom_out()
            event.accept()
            return
        if event.key() in (Qt.Key_0, Qt.Key_Home):
            self.reset_world()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._constrain_view()
        self._retire_nonvisible_pending()
        self._prune_failed_tiles()
        self._failure_fallback_active = self._visible_base_unavailable()
        was_ready = self._online_ready
        self._online_ready = self._has_cached_visible_base_tile()
        if was_ready != self._online_ready:
            self.detail_ready_changed.emit(self._online_ready)
        self._update_overlay_texts()
        self.update()

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self._layout_overlays()

    def closeEvent(self, event):
        self._closing = True
        self._cancel_pending()
        super().closeEvent(event)


def run_self_test() -> list[str]:
    """Run deterministic checks with online tile access explicitly disabled."""

    app = QApplication.instance()
    owns_application = app is None
    if app is None:
        app = QApplication([])

    checks: list[str] = []

    if not verify_map_asset():
        raise RuntimeError("The bundled Natural Earth map asset did not verify.")
    checks.append("bundled asset integrity and provenance")

    expected_points = [
        ((0.0, 0.0), QPointF(1800.0, 900.0)),
        ((90.0, -180.0), QPointF(0.0, 0.0)),
        ((-90.0, 180.0), QPointF(3600.0, 1800.0)),
        ((60.3913, 5.3221), QPointF(1853.221, 296.087)),
    ]
    for coordinates, expected in expected_points:
        actual = coordinate_to_scene(*coordinates)
        if abs(actual.x() - expected.x()) > 0.002:
            raise RuntimeError(f"Fallback-map X projection failed for {coordinates}: {actual}")
        if abs(actual.y() - expected.y()) > 0.002:
            raise RuntimeError(f"Fallback-map Y projection failed for {coordinates}: {actual}")
    checks.append("fallback projection and geographic bounds")

    for coordinates in ((0.0, 0.0), (60.3913, 5.3221), (-33.8688, 151.2093)):
        projected = _mercator_project(*coordinates, 12.0)
        latitude, longitude = _mercator_unproject(projected.x(), projected.y(), 12.0)
        if abs(latitude - coordinates[0]) > 1e-6 or abs(longitude - coordinates[1]) > 1e-6:
            raise RuntimeError(f"Web Mercator round trip failed for {coordinates}.")
    checks.append("Web Mercator projection and round trip")

    for invalid in ((91.0, 0.0), (0.0, 181.0), (math.nan, 0.0)):
        try:
            coordinate_to_scene(*invalid)
        except ValueError:
            continue
        raise RuntimeError(f"Invalid coordinates were accepted: {invalid}")
    checks.append("invalid-coordinate rejection")

    street_url = _tile_url((LAYER_STREET, 12, 2110, 1341, "base")).toString()
    satellite_url = _tile_url((LAYER_SATELLITE, 12, 2110, 1341, "labels")).toString()
    if street_url != "https://tile.openstreetmap.org/12/2110/1341.png":
        raise RuntimeError("The required OpenStreetMap tile endpoint changed.")
    if "World_Boundaries_and_Places/MapServer/tile/12/1341/2110" not in satellite_url:
        raise RuntimeError("The satellite label overlay URL is malformed.")
    if _TILE_REDIRECT_POLICY != QNetworkRequest.ManualRedirectPolicy:
        raise RuntimeError("Tile redirects could escape the strict provider allowlist.")
    checks.append("strict HTTPS tile provider allowlist and URL ordering")

    tile_image = QImage(TILE_SIZE, TILE_SIZE, QImage.Format_RGB32)
    tile_image.fill(QColor("#345678"))
    tile_buffer = QBuffer()
    tile_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not tile_image.save(tile_buffer, "PNG"):
        raise RuntimeError("The tile-decoder test image could not be encoded.")
    decoded_tile = _decode_tile_pixmap(bytes(tile_buffer.data()))
    tile_buffer.close()
    jpeg_buffer = QBuffer()
    jpeg_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not tile_image.save(jpeg_buffer, "JPEG"):
        raise RuntimeError("The JPEG tile-decoder test image could not be encoded.")
    decoded_jpeg_tile = _decode_tile_pixmap(bytes(jpeg_buffer.data()))
    jpeg_buffer.close()
    wrong_size = QImage(1, 1, QImage.Format_RGB32)
    wrong_size.fill(QColor("#345678"))
    wrong_buffer = QBuffer()
    wrong_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    wrong_size.save(wrong_buffer, "PNG")
    rejected_tile = _decode_tile_pixmap(bytes(wrong_buffer.data()))
    wrong_buffer.close()
    if decoded_tile is None or decoded_jpeg_tile is None or rejected_tile is not None:
        raise RuntimeError("Tile payload dimensions were not validated before use.")
    checks.append("bounded image-only tile decoding before pixmap allocation")

    view = WorldMapView(online_enabled=False)
    view.resize(720, 420)
    view.show()
    app.processEvents()
    if not view.using_fallback or not view.map_asset_valid:
        raise RuntimeError("Offline test mode did not use the verified fallback.")
    if view.network_request_count != 0 or view._network_manager is not None:
        raise RuntimeError("Offline test mode created a network request path.")
    if not math.isclose(view.zoom_factor, view._minimum_zoom_for_viewport()):
        raise RuntimeError("The map did not start at the world overview.")
    if view.active_layer != LAYER_STREET or not view._street_button.isChecked():
        raise RuntimeError("The map did not default to the Street layer.")
    checks.append("explicit zero-network offline and screenshot-test mode")

    view.set_location(60.3913, 5.3221, "Bergen, Norway", 12.0)
    app.processEvents()
    if view.current_location != (60.3913, 5.3221) or not view._location_label.isVisible():
        raise RuntimeError("The result pin state or location card did not appear.")
    if view.network_request_count != 0:
        raise RuntimeError("Setting a location in offline mode made a tile request.")
    checks.append("exact result pin, label, and confidence radius state")

    framing_cases = (
        ((60.3913, 5.3221), (720, 420), 4.757027787885948),
        ((-33.8688, 151.2093), (720, 420), 5.505961263679928),
        ((0.0, 0.0), (320, 240), 4.7969491479827315),
    )
    framed_zooms = []
    for coordinates, viewport_size, expected_zoom in framing_cases:
        view.resize(*viewport_size)
        app.processEvents()
        view._set_zoom(MAX_ZOOM)
        view.set_location(*coordinates, "Regional framing check")
        app.processEvents()
        actual_zoom = view.zoom_factor
        framed_zooms.append(actual_zoom)
        if not math.isclose(actual_zoom, expected_zoom, abs_tol=1e-9):
            raise RuntimeError(
                "Regional result framing was not deterministic for "
                f"{coordinates} at {viewport_size}: {actual_zoom}."
            )
        if not RESULT_MIN_ZOOM <= actual_zoom <= RESULT_MAX_ZOOM:
            raise RuntimeError("A result was framed at world or road-level scale.")
        if (
            abs(view._center_latitude - coordinates[0]) > 1e-6
            or abs(view._center_longitude - coordinates[1]) > 1e-6
        ):
            raise RuntimeError("A regional result frame did not center its pin.")
        if view.network_request_count != 0:
            raise RuntimeError("Offline regional result framing made a tile request.")

    if not framed_zooms[2] < _regional_result_zoom(0.0, 720, 420):
        raise RuntimeError("Compact result framing ignored the smaller viewport.")
    view.resize(720, 420)
    app.processEvents()
    view.set_location(60.3913, 5.3221, "Bergen, Norway", 12.0)
    checks.append("deterministic viewport-aware regional result framing")

    for _ in range(40):
        view.zoom_in()
    if view.zoom_factor > MAX_ZOOM + 1e-9:
        raise RuntimeError("Zoom-in exceeded the configured maximum.")
    for _ in range(80):
        view.zoom_out()
    minimum_view_zoom = view._minimum_zoom_for_viewport()
    if not math.isclose(view.zoom_factor, minimum_view_zoom, abs_tol=1e-9):
        raise RuntimeError("Zoom-out exceeded the configured minimum.")
    if not all(
        control.isVisible()
        for control in (view._controls, view._layer_controls, view._zoom_in_button, view._world_button)
    ):
        raise RuntimeError("Map controls disappeared after repeated zooming.")
    if not view.rect().contains(view._controls.geometry()) or not view.rect().contains(
        view._layer_controls.geometry()
    ):
        raise RuntimeError("Map controls moved outside the visible widget.")
    zoom_buttons = (view._zoom_out_button, view._zoom_in_button, view._world_button)
    if len({button.height() for button in zoom_buttons}) != 1:
        raise RuntimeError("The zoom and World controls do not share one height.")
    if view._street_button.size() != view._satellite_button.size():
        raise RuntimeError("The Street and Satellite controls are not equally sized.")
    for frame, buttons in (
        (view._controls, zoom_buttons),
        (view._layer_controls, (view._street_button, view._satellite_button)),
    ):
        for button in buttons:
            top_inset = button.geometry().top()
            bottom_inset = frame.height() - button.geometry().bottom() - 1
            if top_inset != CONTROL_FRAME_PADDING or bottom_inset != CONTROL_FRAME_PADDING:
                raise RuntimeError(
                    "A map control has unequal visible top and bottom padding: "
                    f"{top_inset}px / {bottom_inset}px."
                )
    checks.append("pixel-balanced persistent map controls")

    view._set_zoom(6.0)
    world_size = TILE_SIZE * (2.0 ** view.zoom_factor)
    half_width = view.width() / 2.0
    half_height = view.height() / 2.0
    for raw_center in (
        QPointF(-1.0e12, -1.0e12),
        QPointF(1.0e12, 1.0e12),
        QPointF(-1.0e12, 1.0e12),
        QPointF(1.0e12, -1.0e12),
    ):
        view._set_center_from_world(raw_center)
        bounded = _mercator_project(
            view._center_latitude, view._center_longitude, view.zoom_factor
        )
        if not half_width - 1e-6 <= bounded.x() <= world_size - half_width + 1e-6:
            raise RuntimeError("Horizontal panning escaped the single-world bounds.")
        if not half_height - 1e-6 <= bounded.y() <= world_size - half_height + 1e-6:
            raise RuntimeError("Vertical panning exposed space beyond the Mercator bounds.")

    for _ in range(80):
        view.zoom_out()
    world_size = TILE_SIZE * (2.0 ** view.zoom_factor)
    if world_size + 1e-6 < max(view.width(), view.height()):
        raise RuntimeError("The low-zoom world became smaller than the viewport.")
    view._set_center_from_world(QPointF(-1.0e12, -1.0e12))
    base_rectangles = [
        rectangle
        for key, rectangle in view._visible_tile_entries()
        if key[-1] == "base"
    ]
    if (
        not base_rectangles
        or min(rectangle.left() for rectangle in base_rectangles) > 0.5
        or min(rectangle.top() for rectangle in base_rectangles) > 0.5
        or max(rectangle.right() for rectangle in base_rectangles) < view.width() - 0.5
        or max(rectangle.bottom() for rectangle in base_rectangles) < view.height() - 0.5
    ):
        raise RuntimeError("Bounded low-zoom tiles did not cover the complete viewport.")
    checks.append("finite horizontal, vertical, and low-zoom viewport bounds")

    view._online_enabled = True
    view._live_detail_seen = True
    if view._should_draw_offline_map() or view._has_cached_base_for_layer():
        raise RuntimeError("The live-map transition state is inconsistent.")
    cached_tile = QPixmap(TILE_SIZE, TILE_SIZE)
    cached_tile.fill(QColor("#345678"))
    view._tiles[(LAYER_STREET, 1, 0, 0, "base")] = cached_tile
    transition_image = QImage(64, 64, QImage.Format_RGB32)
    transition_image.fill(QColor("#080c11"))
    transition_painter = QPainter(transition_image)
    fallback_drawn = view._cached_base_fallback(
        transition_painter,
        (LAYER_STREET, 2, 1, 1, "base"),
        QRectF(0.0, 0.0, 64.0, 64.0),
    )
    transition_painter.end()
    if not fallback_drawn or transition_image.pixelColor(32, 32) != QColor("#345678"):
        raise RuntimeError("A zoom transition did not reuse same-layer cached detail.")
    view._tiles.clear()
    visible_entries = view._visible_tile_entries()
    visible_base_keys = list(
        dict.fromkeys(key for key, _ in visible_entries if key[-1] == "base")
    )
    if len(visible_base_keys) < 2:
        raise RuntimeError("The readiness test did not span multiple visible tiles.")
    for key in visible_base_keys:
        view._record_tile_failure(key)
    view._failure_fallback_active = view._visible_base_unavailable(visible_entries)
    view._update_overlay_texts()
    if (
        not view._should_draw_offline_map()
        or "Natural Earth" not in view._attribution_label.text()
        or "unavailable" not in view._status_label.text().lower()
    ):
        raise RuntimeError("A confirmed visible-tile outage did not restore the fallback map.")
    for key in visible_base_keys:
        view._failed_until[key] = time.monotonic() - 1.0
    view._prune_failed_tiles()
    if not view._should_draw_offline_map():
        raise RuntimeError("A retry hid the outage fallback before replacement tiles were ready.")
    view._failure_fallback_active = False
    view._failed_until.clear()
    view._update_overlay_texts()
    checks.append("persistent offline fallback during a confirmed live-tile outage")
    view._tiles[visible_base_keys[0]] = cached_tile
    view._online_ready = False
    readiness_image = QImage(view.size(), QImage.Format_RGB32)
    readiness_image.fill(QColor("#080c11"))
    readiness_painter = QPainter(readiness_image)
    view._draw_tiles(readiness_painter, visible_entries)
    readiness_painter.end()
    if view.detail_ready or view._status_label.isHidden():
        raise RuntimeError("One cached tile prematurely marked the full viewport ready.")

    for key in visible_base_keys:
        view._tiles[key] = cached_tile
    view._online_ready = True
    readiness_changes: list[bool] = []
    view.detail_ready_changed.connect(readiness_changes.append)
    view.resize(1200, 600)
    app.processEvents()
    if view.detail_ready or not readiness_changes or readiness_changes[-1] is not False:
        raise RuntimeError("Resize did not invalidate and signal incomplete tile coverage.")
    view._tile_request_timer.stop()
    view._tile_retry_timer.stop()
    view._desired_tile_keys.clear()
    view.resize(720, 420)
    view._online_enabled = False
    checks.append("no blue fallback and complete-viewport readiness transitions")

    class CanceledReplyProbe:
        def __init__(self):
            self.running = True
            self.deleted_later = False

        def isRunning(self):
            return self.running

        def abort(self):
            self.running = False
            view._tile_finished(probe_key, self)

        def deleteLater(self):
            self.deleted_later = True

    probe_key = (LAYER_STREET, 3, 2, 2, "base")
    canceled_reply = CanceledReplyProbe()
    view._pending[probe_key] = canceled_reply
    view._pending_by_reply_id[id(canceled_reply)] = probe_key
    view._cancel_pending()
    if (
        not canceled_reply.deleted_later
        or view._pending
        or view._pending_by_reply_id
    ):
        raise RuntimeError("Canceled tile replies were not finalized safely.")

    stale_key = (LAYER_STREET, 4, 4, 4, "base")
    stale_reply = QLabel()
    view._pending[stale_key] = stale_reply
    view._pending_by_reply_id[_qt_object_token(stale_reply)] = stale_key
    shiboken6.delete(stale_reply)
    view._tile_finished(stale_key, stale_reply)
    if view._pending or view._pending_by_reply_id:
        raise RuntimeError("A Qt-deleted tile reply remained in pending bookkeeping.")

    first_batch = [
        (LAYER_STREET, 5, 10, 10, "base"),
        (LAYER_STREET, 5, 11, 10, "base"),
    ]
    final_batch = [(LAYER_STREET, 6, 22, 20, "base")]
    dispatched: list[TileKey] = []
    original_request_tile = view._request_tile
    view._online_enabled = True
    view._request_tile = dispatched.append
    view._schedule_tile_requests(first_batch)
    view._schedule_tile_requests(final_batch)
    if dispatched or view._desired_tile_keys != final_batch:
        raise RuntimeError("Rapid tile scheduling was not coalesced to the newest view.")
    view._tile_request_timer.stop()
    view._dispatch_tile_requests()
    view._request_tile = original_request_tile
    view._desired_tile_keys.clear()
    view._online_enabled = False
    if dispatched != final_batch:
        raise RuntimeError("The coalesced tile request did not dispatch the final view.")
    checks.append("safe reply lifecycle and coalesced rapid navigation requests")

    view._failed_until.clear()
    failure_keys = [
        (LAYER_STREET, 10, index, 0, "base")
        for index in range(MAX_FAILED_TILES + 16)
    ]
    for failure_key in failure_keys:
        view._record_tile_failure(failure_key)
    if (
        len(view._failed_until) != MAX_FAILED_TILES
        or failure_keys[0] in view._failed_until
        or failure_keys[-1] not in view._failed_until
    ):
        raise RuntimeError("Transient tile failures could grow without a fixed bound.")
    view._failed_until.clear()
    view._online_enabled = False
    checks.append("bounded transient-failure bookkeeping during rapid navigation")

    retry_key = next(
        key for key, _ in view._visible_tile_entries() if key[-1] == "base"
    )
    view._tiles.pop(retry_key, None)
    retry_dispatches: list[TileKey] = []
    original_request_tile = view._request_tile
    view._request_tile = retry_dispatches.append
    view._online_enabled = True
    view._desired_tile_keys = [retry_key]
    view._failed_until[retry_key] = time.monotonic() + 0.025
    view._arm_failed_tile_retry()
    retry_deadline = time.monotonic() + 0.25
    while not retry_dispatches and time.monotonic() < retry_deadline:
        app.processEvents()
        time.sleep(0.005)
    view._tile_retry_timer.stop()
    view._tile_request_timer.stop()
    view._request_tile = original_request_tile
    view._desired_tile_keys.clear()
    view._failed_until.pop(retry_key, None)
    view._online_enabled = False
    if retry_dispatches.count(retry_key) != 1:
        raise RuntimeError("A visible failed tile did not retry after its cooldown.")
    checks.append("automatic visible-tile retry after transient failure")

    view.show_satellite()
    app.processEvents()
    if view.active_layer != LAYER_SATELLITE or not view._satellite_button.isChecked():
        raise RuntimeError("Satellite layer selection did not update the map controls.")
    if view.network_request_count != 0:
        raise RuntimeError("Satellite selection bypassed offline test mode.")
    checks.append("street and labeled-satellite layer switching")

    view.clear_location()
    if view.has_location or view._location_label.isVisible():
        raise RuntimeError("Clearing the map left a result visible.")
    if not math.isclose(view.zoom_factor, view._minimum_zoom_for_viewport()):
        raise RuntimeError("Clearing the result did not restore the world view.")
    checks.append("clear and reset behavior")

    missing_path = MODULE_DIR / "assets" / "__missing_world_map_for_test__.png"
    fallback_view = WorldMapView(asset_path=missing_path, online_enabled=False)
    fallback_view.resize(640, 360)
    fallback_view.set_location(0.0, 0.0, "Fallback check")
    fallback_view.show()
    app.processEvents()
    if fallback_view.map_asset_valid or not fallback_view.using_fallback:
        raise RuntimeError("The missing-asset fallback was not functional.")
    checks.append("missing or corrupt asset fallback path")

    if view._attribution_label.isHidden() or fallback_view._attribution_label.isHidden():
        raise RuntimeError("Map attribution was not permanently visible.")
    checks.append("permanent visible attribution and privacy summary")

    view.close()
    fallback_view.close()
    app.processEvents()
    if owns_application:
        app.quit()
    return checks


if __name__ == "__main__":
    completed = run_self_test()
    for index, check in enumerate(completed, 1):
        print(f"[{index:02d}] PASS - {check}")
    print(f"PASS - {len(completed)} offline map checks")
