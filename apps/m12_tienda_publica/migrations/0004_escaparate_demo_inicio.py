from django.db import migrations


def sembrar_vitrinas(apps, schema_editor):
    Escaparate = apps.get_model("m12_tienda_publica", "Escaparate_seccion")
    filas = [
        ("mas-vendidos", "Lo más pedido", "Los más vendidos", "/catalogo?orden=destacados", "#E11D74", 0),
        ("ferreteria", "Todo para el trabajo", "Ferretería", "/catalogo?tipo=ferreteria", "#00ACC1", 1),
        ("vinilos", "Acabados DECO", "Vinilos y esmaltes", "/catalogo?categoria=vinilos", "#4A154B", 2),
        ("exteriores", "Resistentes al clima", "Exteriores y tráfico", "/catalogo?q=exterior", "#F4A236", 3),
    ]
    for clave, frase, titulo, enlace, color, orden in filas:
        Escaparate.objects.get_or_create(
            clave=clave,
            defaults={
                "frase": frase,
                "titulo": titulo,
                "enlace_catalogo": enlace,
                "color_acento": color,
                "orden": orden,
                "estado": True,
                "version_fila": 1,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("m12_tienda_publica", "0003_escaparate_seccion"),
    ]

    operations = [
        migrations.RunPython(sembrar_vitrinas, migrations.RunPython.noop),
    ]