# ==============================================================================
# Pruebas Unitarias de Adaptadores de Infraestructura Externa (Mocked HTTPX) - MPDW
# SAD Ref: ADR-011, I-04, I-07, E-02
# ==============================================================================
from unittest.mock import MagicMock

import httpx
import pytest

from apps.m13_plataforma.adapters.email_sendgrid import SendGridEmailAdapter
from apps.m13_plataforma.adapters.storage_supabase import SupabaseStorageAdapter


@pytest.mark.unit
def test_sendgrid_adapter_exito_envio():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=202)

    adapter = SendGridEmailAdapter(api_key="SG.fake_key_123", remitente="no-reply@mpdw.com", client=client_mock)
    resultado = adapter.enviar_recuperacion_password("usuario@cliente.com", "https://mpdw.com/reset?token=abc")

    assert resultado is True
    client_mock.post.assert_called_once()


@pytest.mark.unit
def test_sendgrid_adapter_sin_api_key_retorna_falso():
    adapter = SendGridEmailAdapter(api_key="")
    assert adapter.enviar_recuperacion_password("test@test.com", "http://reset") is False


@pytest.mark.unit
def test_sendgrid_adapter_error_http_retorna_falso():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=400, text="Bad Request")

    adapter = SendGridEmailAdapter(api_key="SG.fake_key", client=client_mock)
    assert adapter.enviar_recuperacion_password("u@test.com", "http://reset") is False


@pytest.mark.unit
def test_sendgrid_adapter_excepcion_red():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.side_effect = httpx.ConnectError("Connection refused")

    adapter = SendGridEmailAdapter(api_key="SG.fake_key", client=client_mock)
    assert adapter.enviar_recuperacion_password("u@test.com", "http://reset") is False


@pytest.mark.unit
def test_supabase_storage_adapter_subir_archivo_publico_exito():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=201)

    adapter = SupabaseStorageAdapter(
        supabase_url="https://test.supabase.co",
        service_key="secret-key",
        bucket_publico="productos",
        client=client_mock,
    )

    url = adapter.subir_archivo_publico(b"fake image data", "vinilos/prod1.webp", "image/webp")
    assert "https://test.supabase.co/storage/v1/object/public/productos/vinilos/prod1.webp" in url
    client_mock.post.assert_called_once()


@pytest.mark.unit
def test_supabase_storage_adapter_subir_archivo_publico_error_lanza_excepcion():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=403, text="Forbidden")

    adapter = SupabaseStorageAdapter(
        supabase_url="https://test.supabase.co",
        service_key="secret-key",
        client=client_mock,
    )

    with pytest.raises(RuntimeError) as exc_info:
        adapter.subir_archivo_publico(b"data", "test.png", "image/png")
    assert "403" in str(exc_info.value)


@pytest.mark.unit
def test_supabase_storage_adapter_subir_archivo_privado_exito():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=200)

    adapter = SupabaseStorageAdapter(
        supabase_url="https://test.supabase.co",
        service_key="secret-key",
        bucket_privado="soportes",
        client=client_mock,
    )

    ruta = adapter.subir_archivo_privado(b"pdf data", "cierres/soporte1.pdf", "application/pdf")
    assert ruta == "cierres/soporte1.pdf"


@pytest.mark.unit
def test_supabase_storage_adapter_subir_archivo_privado_error():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=500, text="Internal Error")

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)
    with pytest.raises(RuntimeError):
        adapter.subir_archivo_privado(b"pdf", "file.pdf", "application/pdf")


@pytest.mark.unit
def test_supabase_storage_adapter_obtener_url_firmada():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=200, json={"signedURL": "/object/sign/soporte1.pdf?token=123"})

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)
    url_firmada = adapter.obtener_url_firmada("cierres/soporte1.pdf", segundos_validez=1800)
    assert "signedURL" in url_firmada or "soporte1.pdf" in url_firmada


@pytest.mark.unit
def test_supabase_storage_adapter_verificar_conexion():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.get.return_value = httpx.Response(status_code=200)

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)
    assert adapter.verificar_conexion() is True


@pytest.mark.unit
def test_supabase_storage_adapter_eliminar_archivo():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.delete.return_value = httpx.Response(status_code=200)

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)
    assert adapter.eliminar_archivo("mpdw-public", "test.png") is True


@pytest.mark.unit
def test_public_and_private_storage_specialized_adapters():
    from apps.m13_plataforma.adapters.storage_supabase import (
        PrivateBucketStorageAdapter,
        PublicBucketStorageAdapter,
    )

    base_mock = MagicMock(spec=SupabaseStorageAdapter)
    base_mock.subir_archivo_publico.return_value = "https://cdn.com/img.png"
    base_mock.subir_archivo_privado.return_value = "priv/doc.pdf"
    base_mock.obtener_url_firmada.return_value = "https://cdn.com/priv?token=1"
    base_mock.eliminar_archivo.return_value = True

    pub_adapter = PublicBucketStorageAdapter(adapter=base_mock)
    assert pub_adapter.subir_archivo_publico(b"123", "img.png", "image/png") == "https://cdn.com/img.png"
    assert pub_adapter.eliminar_archivo("b", "p") is True

    priv_adapter = PrivateBucketStorageAdapter(adapter=base_mock)
    assert priv_adapter.subir_archivo(b"123", "doc.pdf", "application/pdf") == "priv/doc.pdf"
    assert priv_adapter.obtener_url_firmada("doc.pdf") == "https://cdn.com/priv?token=1"
    assert priv_adapter.eliminar_archivo("b", "p") is True


@pytest.mark.unit
def test_supabase_storage_adapter_errores_red():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.side_effect = httpx.ConnectError("Connection refused")
    client_mock.delete.side_effect = httpx.ConnectError("Connection refused")
    client_mock.get.side_effect = httpx.ConnectError("Connection refused")

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)

    with pytest.raises(RuntimeError):
        adapter.subir_archivo_publico(b"123", "test.png", "image/png")

    with pytest.raises(RuntimeError):
        adapter.subir_archivo_privado(b"123", "test.pdf", "application/pdf")

    assert adapter.obtener_url_firmada("test.pdf") == ""
    assert adapter.eliminar_archivo("b", "p") is False
    assert adapter.verificar_conexion() is False


@pytest.mark.unit
def test_supabase_storage_adapter_fallos_respuesta():
    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = httpx.Response(status_code=404)
    client_mock.get.return_value = httpx.Response(status_code=500)

    adapter = SupabaseStorageAdapter(supabase_url="https://test.supabase.co", service_key="key", client=client_mock)

    assert adapter.obtener_url_firmada("test.pdf") == ""
    assert adapter.verificar_conexion() is False


@pytest.mark.unit
def test_fake_adapters_cobertura():
    from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter, FakeStorageAdapter

    fake_email = FakeEmailAdapter()
    assert fake_email.enviar_recuperacion_password("test@mpdw.com", "http://reset") is True
    assert len(fake_email.enviados) == 1

    fake_storage = FakeStorageAdapter()
    url = fake_storage.subir_archivo_publico(b"data", "foto.png", "image/png")
    assert "foto.png" in url
    assert fake_storage.eliminar_archivo("b", "foto.png") is True
    assert fake_storage.eliminar_archivo("b", "inexistente.png") is False


