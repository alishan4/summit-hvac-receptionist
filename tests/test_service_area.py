import pytest

from app.services.service_area import in_service_area, normalize_zip


@pytest.mark.parametrize(
    "raw,expected",
    [("80202", "80202"), (" 80202 ", "80202"), ("80202-1234", "80202"), ("8 0 2 0 2", "80202"),
     ("802", None), ("abcde", None), ("", None)],
)
def test_normalize(raw, expected):
    assert normalize_zip(raw) == expected


def test_in_area(cfg):
    assert in_service_area(cfg, "80203") == (True, "80203")


def test_out_of_area(cfg):
    assert in_service_area(cfg, "80301") == (False, "80301")  # Boulder


def test_invalid(cfg):
    assert in_service_area(cfg, "12") == (False, None)
