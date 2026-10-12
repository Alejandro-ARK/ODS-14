class HeroMixin:
    """
    Datos de la franja azul ("hero") que base.html muestra bajo la barra de
    navegación. Equivale a las variables $page_titulo, $hero_subtitulo,
    $hero_icono y $hero_grande que cada página PHP definía antes del header.
    """
    titulo = ''
    subtitulo = ''
    icono = 'fa-water'
    hero_grande = False

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            page_titulo=self.titulo,
            hero_subtitulo=self.subtitulo,
            hero_icono=self.icono,
            hero_grande=self.hero_grande,
        )
        return contexto
