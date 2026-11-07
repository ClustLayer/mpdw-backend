from unittest.mock import MagicMock, patch

import pytest
from django.db import OperationalError
from rest_framework.throttling import SimpleRateThrottle

from apps.m13_plataforma.throttling import DatabaseCacheRateThrottle
from config.settings.base import parse_db_url


@pytest.mark.unit
def test_parse_db_url_conserva_usuario_tenant_supabase():
    url = (
        "postgresql://postgres.ymxlkdzkpskvgrpdggjp:Secr%2Fet@"
        "aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )
    cfg = parse_db_url(url, ssl_require=False)
    assert cfg["USER"] == "postgres.ymxlkdzkpskvgrpdggjp"
    assert cfg["PASSWORD"] == "Secr/et"
    assert cfg["HOST"] == "aws-0-us-east-1.pooler.supabase.com"
    assert cfg["PORT"] == "6543"
    assert cfg["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert cfg["OPTIONS"]["prepare_threshold"] is None


@pytest.mark.unit
def test_parse_db_url_ssl_en_options_cuando_se_exige():
    url = "postgresql://mpdw_app:secret@localhost:5432/mpdw_db"
    cfg = parse_db_url(url, ssl_require=True)
    assert cfg["OPTIONS"].get("sslmode") == "require"


@pytest.mark.unit
def test_throttle_degrada_si_cache_falla():
    throttle = DatabaseCacheRateThrottle()
    request = MagicMock()
    request.user = MagicMock(is_authenticated=False)
    view = MagicMock()
    with patch.object(
        SimpleRateThrottle,
        "allow_request",
        side_effect=OperationalError("connection failed"),
    ):
        assert throttle.allow_request(request, view) is True
