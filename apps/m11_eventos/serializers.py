from rest_framework import serializers

from apps.m11_eventos.models import Eventos_novedades


class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eventos_novedades
        fields = (
            "id_evento",
            "tipo",
            "id_sede",
            "titulo",
            "descripcion",
            "fecha_inicio",
            "fecha_fin",
            "impacto",
            "estado",
            "visible_sitio",
            "fecha_registro",
        )
        read_only_fields = ("id_evento", "fecha_registro")

