from apps.m05_clientes.models import Clientes


class ClienteRepository:
    def buscar_por_documento(self, doc: str) -> Clientes | None:
        return Clientes.objects.filter(documento=doc).first()

