"""Bounded offline regression/performance checks; no keys, photos or network.

Run with the app's private python.exe -I, optionally --output PATH.json.
Timings are generous tripwires, not claims about real API latency.
"""
import argparse
import gzip
import importlib.machinery
import importlib.util
import json
import math
import os
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP_DIR = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("audit_location_app", str(APP_DIR / "AI Location Finder.pyw"))
spec = importlib.util.spec_from_loader(loader.name, loader)
ai = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ai
loader.exec_module(ai)
p = ai.provider_catalog
app = ai.QApplication.instance() or ai.QApplication([])
app.setStyle("Fusion")
metrics = {"network_requests": 0, "real_desktop_captures": 0, "synthetic_only": True}
VALID = {"found": True, "location": "Synthetic", "latitude": 1.0, "longitude": 2.0}


class OfflineRegression(unittest.TestCase):
    def test_result_status_types(self):
        for value in (1, {}, {"unexpected": 1}, [], [True]):
            with self.subTest(value=value), self.assertRaises(ai.AnalysisError):
                ai.result_from_payload({**VALID, "found": value})
        self.assertEqual(ai.result_from_payload({**VALID, "found": "true"}).latitude, 1)

    def test_numeric_boolean_rejected(self):
        for key in ("latitude", "longitude", "confidence_km", "confidence_percent"):
            with self.subTest(key=key), self.assertRaises(ai.AnalysisError):
                ai.result_from_payload({**VALID, key: True})
        result = ai.result_from_payload({**VALID, "alternatives": [{"location": "bad", "latitude": True, "longitude": 2}]})
        self.assertEqual(result.alternatives, [])

    def test_numeric_nonfinite_rejected(self):
        for key in ("latitude", "longitude", "confidence_km", "confidence_percent"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(key=key, value=value), self.assertRaises(ai.AnalysisError):
                    ai.result_from_payload({**VALID, key: value})

    def test_malformed_provider_text(self):
        for text in (None, {}, [], 42):
            with self.subTest(text=text):
                with self.assertRaises(p.ProviderRequestError) as caught:
                    p._extract_anthropic_response({"content": [{"type": "text", "text": text}]})
                self.assertEqual(caught.exception.category, "bad_response")

    def test_json_recovery_bounded_and_latest(self):
        before = time.perf_counter()
        text = "{" * 40000 + json.dumps(VALID)
        self.assertEqual(p._parse_json_text(text, "Synthetic"), VALID)
        elapsed = time.perf_counter() - before
        metrics["json_40k_prefix_seconds"] = elapsed
        self.assertLess(elapsed, 0.5)
        latest = {**VALID, "location": "Final"}
        self.assertEqual(p._parse_json_text("preface " + json.dumps(VALID) + "\n" + json.dumps(latest), "Synthetic"), latest)
        for text in ("x" * (256 * 1024 + 1), "[" * 20000 + "0" + "]" * 20000):
            with self.assertRaises(p.ProviderRequestError):
                p._parse_json_text(text, "Synthetic")

    def test_timeout_validation_before_io(self):
        for value in (0, -1, math.nan, math.inf, -math.inf, "invalid"):
            with self.subTest(value=value), patch.object(p, "_get_http_client", side_effect=AssertionError("I/O attempted")), self.assertRaises(ValueError):
                p._post_json(p.provider_by_id("openai"), "synthetic-not-a-key", {}, value, None)

    def test_stream_body_cap_and_cleanup(self):
        class Body(p.httpx.SyncByteStream):
            closed = False
            chunks = 0
            def __iter__(self):
                for _ in range(100):
                    self.chunks += 1
                    yield b"x" * 65536
            def close(self):
                self.closed = True
        body = Body()
        client = p.httpx.Client(transport=p.httpx.MockTransport(lambda request: p.httpx.Response(200, stream=body)), trust_env=False)
        try:
            with patch.object(p, "_get_http_client", return_value=client), self.assertRaises(p.ProviderRequestError) as caught:
                p._post_json(p.provider_by_id("openai"), "synthetic-not-a-key", {}, 1, None)
            self.assertEqual(caught.exception.category, "bad_response")
            self.assertTrue(body.closed)
            self.assertLessEqual(body.chunks, (4 * 1024 * 1024) // 65536 + 1)
            metrics["oversize_stream_chunks_read"] = body.chunks
        finally:
            client.close()

    def test_compressed_stream_and_repeated_job_memory(self):
        encoded = gzip.compress(json.dumps(VALID).encode())
        requests = []
        def respond(request):
            requests.append(request.url.host)
            return p.httpx.Response(200, headers={"Content-Encoding": "gzip"}, content=encoded)
        client = p.httpx.Client(transport=p.httpx.MockTransport(respond), trust_env=False)
        tracemalloc.start()
        before = time.perf_counter()
        try:
            with patch.object(p, "_get_http_client", return_value=client):
                for _ in range(30):
                    response = p._post_json(p.provider_by_id("openai"), "synthetic-not-a-key", {}, 1, None)
                    self.assertEqual(p._response_json(response, p.provider_by_id("openai")), VALID)
            elapsed = time.perf_counter() - before
            peak = tracemalloc.get_traced_memory()[1]
            metrics.update(fake_network_jobs=30, fake_network_jobs_seconds=elapsed, fake_network_jobs_peak_bytes=peak)
            self.assertLess(elapsed, 3)
            self.assertLess(peak, 4 * 1024 * 1024)
            self.assertEqual(len(requests), 30)
        finally:
            tracemalloc.stop()
            client.close()

    def test_map_unread_network_buffer_cap(self):
        import location_map as maps
        class Reply(maps.QNetworkReply):
            aborted = False
            def bytesAvailable(self):
                return maps.MAX_TILE_PAYLOAD_BYTES + 1
            def abort(self):
                self.aborted = True
        view = maps.WorldMapView(online_enabled=False)
        reply = Reply(view)
        class Manager:
            def get(self, request):
                return reply
        view._network_manager = Manager()
        view._request_tile((maps.LAYER_STREET, 3, 2, 2, "base"))
        self.assertEqual(reply.readBufferSize(), maps.MAX_TILE_PAYLOAD_BYTES + 1)
        reply.readyRead.emit()
        self.assertTrue(reply.aborted)
        view._network_manager = None
        view.close()
        view.deleteLater()
        app.processEvents()

    def test_startup_and_worker_event_responsiveness(self):
        with tempfile.TemporaryDirectory(prefix="location-offline-audit-") as temporary:
            before = time.perf_counter()
            window = ai.LocationFinder(Path(temporary) / "settings.ini", testing=True)
            startup = time.perf_counter() - before
            metrics["startup_seconds"] = startup
            self.assertLess(startup, 5)
            ticks = []
            timer = ai.QTimer()
            timer.setInterval(5)
            timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
            timer.start()
            thread = ai.QThread()
            worker = ai.AnalysisWorker(b"synthetic-image-data", "image/jpeg", "synthetic-not-a-key", ai.default_model("openai"), "Low", 3, "Regular photo or screenshot", "", None, "synthetic.jpg")
            worker.moveToThread(thread)
            completions = []
            worker.finished.connect(lambda *values: completions.append(values))
            worker.finished.connect(thread.quit)
            thread.started.connect(worker.run)
            def fake_call(*args, **kwargs):
                time.sleep(0.10)
                return dict(VALID)
            with patch.object(ai, "call_vision_model", side_effect=fake_call):
                thread.start()
                deadline = time.perf_counter() + 4
                while thread.isRunning() and time.perf_counter() < deadline:
                    app.processEvents()
                    time.sleep(0.001)
                self.assertFalse(thread.isRunning())
                app.processEvents()
            timer.stop()
            self.assertTrue(completions)
            self.assertEqual(completions[0][0], "success")
            self.assertEqual(worker.api_key, "")
            self.assertEqual(worker.image_data, b"")
            self.assertGreater(len(ticks), 10)
            max_gap = max(b - a for a, b in zip(ticks, ticks[1:]))
            metrics.update(worker_timer_ticks=len(ticks), worker_max_timer_gap_seconds=max_gap)
            self.assertLess(max_gap, 0.25)
            worker.deleteLater()
            thread.deleteLater()
            window.close()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineRegression))
    metrics.update(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), limits={"startup_seconds": 5, "json_seconds": 0.5, "fake_jobs_seconds": 3, "fake_jobs_peak_bytes": 4194304, "timer_gap_seconds": 0.25})
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    raise SystemExit(not result.wasSuccessful())
