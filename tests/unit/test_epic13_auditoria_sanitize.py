import pytest

from apps.m10_auditoria.sanitize import _mask_tarjeta_o_cuenta, sanitize_auditoria_payload


@pytest.mark.unit
def test_sanitiza_password_y_token():
    d = sanitize_auditoria_payload({"password": "x", "access_token": "y", "ok": 1})
    assert d is not None
    assert d["password"] == "[omitido]"
    assert d["access_token"] == "[omitido]"
    assert d["ok"] == 1


@pytest.mark.unit
def test_sanitiza_numero_tarjeta_en_string():
    pan = "4111 1111 1111 1111"
    d = sanitize_auditoria_payload({"nota": f"Pago con {pan}"})
    assert d is not None
    assert "4111" in d["nota"]
    assert "1111" not in d["nota"] or "****" in d["nota"]


@pytest.mark.unit
def test_sanitiza_string_corto_no_enmascara():
    d = sanitize_auditoria_payload({"x": "123456789012"})
    assert d is not None
    assert d["x"] == "123456789012"


@pytest.mark.unit
def test_sanitiza_lista_con_dict():
    d = sanitize_auditoria_payload({"items": [{"token": "abc"}]})
    assert d is not None
    assert d["items"][0]["token"] == "[omitido]"


@pytest.mark.unit
def test_sanitize_none():
    assert sanitize_auditoria_payload(None) is None


@pytest.mark.unit
def test_nested_dict_recursivo():
    d = sanitize_auditoria_payload({"outer": {"refresh_token": "abc"}})
    assert d is not None
    assert d["outer"]["refresh_token"] == "[omitido]"


@pytest.mark.unit
def test_tarjeta_15_digitos_omite():
    # 15 dígitos: enmascara como [omitido] (menos de 16 en solo dígitos)
    d = sanitize_auditoria_payload({"x": "411111111111111"})
    assert d is not None
    assert d["x"] == "[omitido]"


@pytest.mark.unit
def test_mask_tarjeta_ramas_cortas():
    assert _mask_tarjeta_o_cuenta("ab") == "ab"
    # 13 letras, sin dígitos: queda la cadena original tras contar dígitos
    assert _mask_tarjeta_o_cuenta("abcdefghijklm") == "abcdefghijklm"
