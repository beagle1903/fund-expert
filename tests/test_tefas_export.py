import json
from datetime import date, datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError

import pytest

from fundexpert.data.bundle import validate_bundle
from fundexpert.data.tefas_export import (
    EXPORTS,
    WebExportError,
    _one_month_before,
    download_web_export_bundle,
)


def _row(code, definition):
    values = {
        "fonKodu": code,
        "fonUnvan": f"{code} FONU",
        "fonTurAciklama": "Değişken Şemsiye Fonu",
        "riskDegeri": 4,
        "getiri1a": Decimal("1.25"),
        "getiri3a": Decimal("2.50"),
        "getiri6a": Decimal("3.75"),
        "getiriyb": Decimal("4.00"),
        "getiri1y": Decimal("5.25"),
        "getiri3y": Decimal("15.50"),
        "getiri5y": Decimal("25.75"),
        "uygulananYu1Y": Decimal("1.50"),
        "fonIcTuzukYu1G": Decimal("2.00"),
        "yillikGetiri": Decimal("5.25"),
        "fonTopGiderKesoran": Decimal("2.50"),
        "ilkPortfoyDegeri": Decimal("1000.50"),
        "sonPortfoyDegeri": Decimal("1100.75"),
        "portBuyuklukDegisim": Decimal("10.02"),
        "ilkPayAdedi": Decimal("100.00"),
        "sonPayAdedi": Decimal("105.00"),
        "payAdetDegisim": Decimal("5.00"),
        "netGetiriOrani": Decimal("1.25"),
    }
    return {key: values[key] for key, _ in definition.columns}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload, default=float, ensure_ascii=False).encode("utf-8")


class RecordingOpener:
    def __init__(self, *, rows=500):
        self.rows = rows
        self.requests = []

    def __call__(self, request, *, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        self.requests.append((payload, timeout))
        definition = next(
            item for item in EXPORTS if item.listing_type == payload["listingType"]
        )
        return FakeResponse(
            [_row(f"F{index:04}", definition) for index in range(self.rows)]
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 7, 27), date(2026, 6, 27)),
        (date(2026, 3, 31), date(2026, 2, 28)),
        (date(2024, 3, 31), date(2024, 2, 29)),
        (date(2026, 1, 15), date(2025, 12, 15)),
    ],
)
def test_one_month_before_matches_tefas_date_window(value, expected):
    assert _one_month_before(value) == expected


def test_download_web_export_bundle_renders_valid_canonical_csvs(tmp_path):
    opener = RecordingOpener()
    acquired_at = datetime(2026, 7, 27, 14, 30, 45)

    download_web_export_bundle(
        "tefas",
        tmp_path,
        now=acquired_at,
        opener=opener,
    )
    manifest = validate_bundle(tmp_path, "tefas", source="tefas-web-export")

    assert manifest.row_count == 500
    assert manifest.exported_at == acquired_at
    assert {path.name for path in tmp_path.iterdir()} == {
        "getiri.csv",
        "yonetim ucreti.csv",
        "buyukluk.csv",
    }
    assert (tmp_path / "getiri.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    assert len(opener.requests) == 3
    size_payload = opener.requests[2][0]
    assert size_payload["filters"]["basTarih"] == "2026-06-27"
    assert size_payload["filters"]["bitTarih"] == "2026-07-27"
    assert size_payload["filters"]["calismaTipi"] == 1


def test_download_web_export_bundle_uses_befas_fund_type(tmp_path):
    opener = RecordingOpener(rows=100)

    download_web_export_bundle("befas", tmp_path, opener=opener)

    assert {request[0]["fundType"] for request in opener.requests} == {"EMK"}


def test_download_web_export_bundle_rejects_short_response(tmp_path):
    opener = RecordingOpener(rows=10)

    with pytest.raises(WebExportError, match="only 10 TEFAS rows"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def test_download_web_export_bundle_ignores_up_to_five_code_set_differences(tmp_path):
    opener = RecordingOpener(rows=505)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-5]
        return response

    download_web_export_bundle("tefas", tmp_path, opener=mismatch)

    manifest = validate_bundle(tmp_path, "tefas", source="tefas-web-export")
    assert manifest.row_count == 500
    for path in tmp_path.iterdir():
        contents = path.read_text(encoding="utf-8-sig")
        assert "F0500" not in contents
        assert "F0504" not in contents


def test_download_web_export_bundle_rejects_more_than_five_code_set_differences(
    tmp_path,
):
    opener = RecordingOpener(rows=506)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-6]
        return response

    with pytest.raises(WebExportError, match="differs by 6 codes"):
        download_web_export_bundle("tefas", tmp_path, opener=mismatch)


def test_download_web_export_bundle_keeps_exact_befas_code_coverage(tmp_path):
    opener = RecordingOpener(rows=101)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-1]
        return response

    with pytest.raises(WebExportError, match="maximum tolerated is 0"):
        download_web_export_bundle("befas", tmp_path, opener=mismatch)


def test_download_web_export_bundle_keeps_row_floor_after_alignment(tmp_path):
    opener = RecordingOpener()
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload[0]["fonKodu"] = "DIFFERENT"
        return response

    with pytest.raises(WebExportError, match="only 499 aligned TEFAS rows"):
        download_web_export_bundle("tefas", tmp_path, opener=mismatch)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            HTTPError("https://example.com", 503, "Unavailable", {}, None),
            "HTTP 503",
        ),
        (URLError("offline"), "could not be reached"),
    ],
)
def test_download_web_export_bundle_wraps_transport_errors(tmp_path, error, message):
    def fail(*args, **kwargs):
        raise error

    with pytest.raises(WebExportError, match=message):
        download_web_export_bundle("tefas", tmp_path, opener=fail)


def test_download_web_export_bundle_rejects_invalid_json(tmp_path):
    class InvalidResponse(FakeResponse):
        def read(self):
            return b"not-json"

    with pytest.raises(WebExportError, match="invalid JSON"):
        download_web_export_bundle(
            "tefas",
            tmp_path,
            opener=lambda *args, **kwargs: InvalidResponse(None),
        )


def test_download_web_export_bundle_rejects_unexpected_shape(tmp_path):
    with pytest.raises(WebExportError, match="unexpected response"):
        download_web_export_bundle(
            "tefas",
            tmp_path,
            opener=lambda *args, **kwargs: FakeResponse({"error": "nope"}),
        )


def test_download_web_export_bundle_rejects_unknown_universe(tmp_path):
    with pytest.raises(ValueError, match="Unsupported universe"):
        download_web_export_bundle("both", tmp_path)
