# Sedes de la demo (Cali Centro y Sede Sur) para sitio público y panel.
from datetime import time

from django.db import migrations


def seed_demo_sedes(apps, schema_editor):
    Sedes = apps.get_model("m02_sedes", "Sedes")
    Sede_horario = apps.get_model("m02_sedes", "Sede_horario")

    if Sedes.objects.filter(nombre="Cali Centro").exists():
        return

    sedes_data = [
        {
            "nombre": "Cali Centro",
            "direccion": "Calle 10 #10-15, Cali",
            "telefono": "+573122486627",
            "whatsapp": "+573122486627",
            "ciudad": "Cali",
            "maps_url": "",
            "map_query": "Calle 10 #10-15, Cali, Colombia",
            "orden": 1,
            "estado": True,
            "horarios": [
                (1, "08:00", "18:00", False),
                (2, "08:00", "18:00", False),
                (3, "08:00", "18:00", False),
                (4, "08:00", "18:00", False),
                (5, "08:00", "18:00", False),
                (6, "08:00", "18:00", False),
                (7, None, None, True),
            ],
        },
        {
            "nombre": "Sede Sur",
            "direccion": "Av. 6N #28-30, Cali",
            "telefono": "+573122486628",
            "whatsapp": "+573122486628",
            "ciudad": "Cali",
            "maps_url": "",
            "map_query": "Av. 6N #28-30, Cali, Colombia",
            "orden": 2,
            "estado": True,
            "horarios": [
                (1, "08:00", "18:00", False),
                (2, "08:00", "18:00", False),
                (3, "08:00", "18:00", False),
                (4, "08:00", "18:00", False),
                (5, "08:00", "18:00", False),
                (6, "08:00", "18:00", False),
                (7, None, None, True),
            ],
        },
    ]

    for data in sedes_data:
        horarios = data.pop("horarios")
        sede = Sedes.objects.create(**data)
        for dia, apertura, cierre, cerrado in horarios:
            Sede_horario.objects.create(
                id_sede=sede,
                dia_semana=dia,
                hora_apertura=time.fromisoformat(apertura) if apertura else None,
                hora_cierre=time.fromisoformat(cierre) if cierre else None,
                cerrado=cerrado,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("m02_sedes", "0002_epic4_sedes_horarios"),
    ]

    operations = [
        migrations.RunPython(seed_demo_sedes, migrations.RunPython.noop),
    ]
