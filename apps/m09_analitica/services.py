from apps.m09_analitica.repositories import AnaliticaRepository


class AnaliticaService:
    def __init__(self, repo: AnaliticaRepository | None = None) -> None:
        self._repo = repo or AnaliticaRepository()

    def obtener_ventas(self):
        return self._repo.obtener_resumen_ventas_diarias()

