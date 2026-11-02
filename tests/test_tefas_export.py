import json
from datetime import date, datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError

import pytest

from fundexpert.data.bundle import BundleValidationError, validate_bundle
from fundexpert.data.loader import GETIRI_RENAME, _read_one
from fundexpert.data.tefas_export import (
    EXPORTS,
    OPEN_CODES_EXPORT,
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
    def __init__(self, *, rows=1500, open_rows=None):
        self.rows = rows
        self.open_rows = open_rows
        self.requests = []

    def __call__(self, request, *, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        self.requests.append((payload, timeout))
        if payload["filters"]["islem"] == 1:
            minimum = 500 if payload["fundType"] == "YAT" else 250
            count = minimum if self.open_rows is None else self.open_rows
            return FakeResponse(
                [_row(f"F{index:04}", OPEN_CODES_EXPORT) for index in range(count)]
            )
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

    assert manifest.row_count == 1500
    assert manifest.has_open_codes
    assert manifest.exported_at == acquired_at
    assert {path.name for path in tmp_path.iterdir()} == {
        "getiri.csv",
        "yonetim ucreti.csv",
        "buyukluk.csv",
        "islem_goren.csv",
    }
    assert (tmp_path / "getiri.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    assert len(opener.requests) == 4
    assert {payload["fundType"] for payload, _ in opener.requests} == {"YAT"}
    assert [payload["filters"]["islem"] for payload, _ in opener.requests] == [
        None,
        None,
        None,
        1,
    ]
    assert opener.requests[3][0]["listingType"] == "return"
    assert opener.requests[3][0]["columns"] == ["fonKodu"]
    size_payload = opener.requests[2][0]
    assert size_payload["filters"]["basTarih"] == "2026-06-27"
    assert size_payload["filters"]["bitTarih"] == "2026-07-27"
    assert size_payload["filters"]["calismaTipi"] == 1


def test_download_web_export_bundle_requests_all_befas_transaction_statuses(tmp_path):
    opener = RecordingOpener(rows=350)

    download_web_export_bundle("befas", tmp_path, opener=opener)

    assert len(opener.requests) == 4
    payloads = [request[0] for request in opener.requests]
    assert {payload["fundType"] for payload in payloads} == {"EMK"}
    assert [payload["filters"]["islem"] for payload in payloads] == [None, None, None, 1]
    assert {payload["listingType"] for payload in payloads} == {
        "return",
        "management",
        "size",
    }


def test_download_web_export_bundle_rejects_short_response(tmp_path):
    opener = RecordingOpener(rows=10)

    with pytest.raises(WebExportError, match="only 10 TEFAS rows"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def test_download_web_export_bundle_ignores_up_to_sixty_tefas_code_set_differences(
    tmp_path,
):
    opener = RecordingOpener(rows=1560)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-60]
        return response

    download_web_export_bundle("tefas", tmp_path, opener=mismatch)

    manifest = validate_bundle(tmp_path, "tefas", source="tefas-web-export")
    assert manifest.row_count == 1500
    for path in tmp_path.iterdir():
        contents = path.read_text(encoding="utf-8-sig")
        assert "F1500" not in contents
        assert "F1559" not in contents


def test_download_web_export_bundle_rejects_more_than_sixty_tefas_code_set_differences(
    tmp_path,
):
    opener = RecordingOpener(rows=1561)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-61]
        return response

    with pytest.raises(WebExportError, match="differs by 61 codes"):
        download_web_export_bundle("tefas", tmp_path, opener=mismatch)


def test_download_web_export_bundle_ignores_up_to_five_befas_code_set_differences(
    tmp_path,
):
    opener = RecordingOpener(rows=355)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-5]
        return response

    download_web_export_bundle("befas", tmp_path, opener=mismatch)

    manifest = validate_bundle(tmp_path, "befas", source="tefas-web-export")
    assert manifest.row_count == 350
    for path in tmp_path.iterdir():
        contents = path.read_text(encoding="utf-8-sig")
        assert "F0350" not in contents
        assert "F0354" not in contents


def test_download_web_export_bundle_rejects_more_than_five_befas_code_set_differences(
    tmp_path,
):
    opener = RecordingOpener(rows=356)
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[:-6]
        return response

    with pytest.raises(
        WebExportError,
        match="BEFAS fund-code coverage differs by 6",
    ) as raised:
        download_web_export_bundle("befas", tmp_path, opener=mismatch)
    assert "maximum tolerated is 5" in str(raised.value)


def test_download_web_export_bundle_rejects_befas_islem_goren_row_floor(tmp_path):
    opener = RecordingOpener(rows=311)

    with pytest.raises(WebExportError, match="only 311 BEFAS rows"):
        download_web_export_bundle("befas", tmp_path, opener=opener)


def test_download_web_export_bundle_rejects_tefas_islem_goren_row_floor(tmp_path):
    opener = RecordingOpener(rows=1071)

    with pytest.raises(WebExportError, match="only 1071 TEFAS rows"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def test_download_web_export_bundle_rejects_short_open_code_response(tmp_path):
    opener = RecordingOpener(open_rows=499)

    with pytest.raises(WebExportError, match="only 499 open TEFAS rows"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def test_download_web_export_bundle_rejects_ignored_open_filter(tmp_path):
    opener = RecordingOpener(open_rows=1500)

    with pytest.raises(WebExportError, match="every TEFAS fund as open"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def _dropping_first_fee_rows(opener, count):
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload = response.payload[count:]
        return response

    return mismatch


def test_download_web_export_bundle_drops_up_to_five_unaligned_open_codes(tmp_path):
    opener = _dropping_first_fee_rows(RecordingOpener(rows=1505), 5)

    download_web_export_bundle("tefas", tmp_path, opener=opener)

    contents = (tmp_path / "islem_goren.csv").read_text(encoding="utf-8-sig")
    assert validate_bundle(tmp_path, "tefas").has_open_codes
    assert "Toplam Kayıt Sayısı:,495" in contents
    assert "F0004" not in contents
    assert "F0005" in contents


def test_download_web_export_bundle_rejects_six_unaligned_open_codes(tmp_path):
    opener = _dropping_first_fee_rows(RecordingOpener(rows=1506), 6)

    with pytest.raises(WebExportError, match="6 open TEFAS fund codes"):
        download_web_export_bundle("tefas", tmp_path, opener=opener)


def _with_risk(opener, code, risk):
    original_call = opener.__call__

    def set_risk(request, *, timeout):
        response = original_call(request, timeout=timeout)
        for row in response.payload:
            if row["fonKodu"] == code and "riskDegeri" in row:
                row["riskDegeri"] = risk
        return response

    return set_risk


@pytest.mark.parametrize("risk", ["-", 0])
def test_download_web_export_bundle_blanks_closed_fund_risk(tmp_path, risk):
    opener = _with_risk(RecordingOpener(), "F1000", risk)

    download_web_export_bundle("tefas", tmp_path, opener=opener)

    frame = _read_one(tmp_path / "getiri.csv", GETIRI_RENAME)
    assert validate_bundle(tmp_path, "tefas").row_count == 1500
    assert frame.set_index("fon_kodu")["risk"].isna()["F1000"]


def test_download_web_export_bundle_rejects_open_fund_invalid_risk(tmp_path):
    opener = _with_risk(RecordingOpener(), "F0000", "-")

    download_web_export_bundle("tefas", tmp_path, opener=opener)

    with pytest.raises(BundleValidationError, match="invalid numeric values"):
        validate_bundle(tmp_path, "tefas")


def test_download_web_export_bundle_keeps_row_floor_after_alignment(tmp_path):
    opener = RecordingOpener()
    original_call = opener.__call__

    def mismatch(request, *, timeout):
        response = original_call(request, timeout=timeout)
        payload = json.loads(request.data.decode("utf-8"))
        if payload["listingType"] == "management":
            response.payload[0]["fonKodu"] = "DIFFERENT"
        return response

    with pytest.raises(WebExportError, match="only 1499 aligned TEFAS rows"):
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
