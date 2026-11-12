"""Plantillas HTML transaccionales. No incluyen secretos de configuración."""

from html import escape


def _marco(titulo: str, cuerpo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>{titulo}</title></head>
<body style="margin:0;background:#fffaf4;font-family:Segoe UI,sans-serif;color:#1b1220;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fffaf4;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border:2px solid #4a154b;border-radius:16px;overflow:hidden;">
        <tr><td style="background:#4a154b;color:#ffffff;padding:24px 28px;font-size:22px;font-weight:800;">Mundo Pinturas Diana</td></tr>
        <tr><td style="padding:28px;">
          <h1 style="margin:0 0 12px;font-size:22px;color:#4a154b;">{titulo}</h1>
          {cuerpo}
          <p style="margin-top:28px;font-size:12px;color:#1b122080;">Si usted no solicitó esta acción, ignore este mensaje. El equipo no le pedirá su contraseña.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def html_recuperacion(enlace: str) -> str:
    cuerpo = (
        "<p>Recibimos una solicitud para restablecer su contraseña. "
        "El enlace es de un solo uso y vence en 60 minutos.</p>"
        f'<p style="margin:24px 0;"><a href="{enlace}" '
        'style="background:#e11d74;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700;">'
        "Restablecer contraseña</a></p>"
        f'<p style="font-size:12px;word-break:break-all;">Si el botón no abre, copie este enlace en el navegador:<br>{enlace}</p>'
    )
    return _marco("Restablecer contraseña", cuerpo)


def html_codigo_2fa(codigo: str) -> str:
    cuerpo = (
        "<p>Use este código para completar el inicio de sesión. Vence en 10 minutos y solo puede usarse una vez.</p>"
        f'<p style="font-size:32px;letter-spacing:8px;font-weight:800;color:#4a154b;">{codigo}</p>'
    )
    return _marco("Código de verificación", cuerpo)


def html_contrasena_inicial(nombre: str, contrasena: str) -> str:
    saludo = escape(nombre.strip() or "colaborador(a)")
    clave = escape(contrasena)
    cuerpo = (
        f"<p>Hola {saludo},</p>"
        "<p>Se creó su acceso a Mundo Pinturas Diana. Use la contraseña temporal siguiente "
        "y cámbiela en el primer inicio de sesión.</p>"
        f'<p style="font-size:22px;font-weight:800;color:#4a154b;letter-spacing:2px;">{clave}</p>'
        "<p>La contraseña temporal vence en 24 horas.</p>"
    )
    return _marco("Acceso al sistema", cuerpo)
