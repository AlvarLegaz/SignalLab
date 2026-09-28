import numpy as np


# ==================================================
# Formateo automático de Time/div
# ==================================================
def format_time_div(seconds):
    """
    Formatea el tiempo por división con unidades automáticas.
    """
    if seconds >= 1:
        return f"{seconds:.2f} s/div"
    elif seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms/div"
    elif seconds >= 1e-6:
        return f"{seconds * 1e6:.2f} µs/div"
    else:
        return f"{seconds * 1e9:.2f} ns/div"


# Trazos de persistencia (ruido) por canal, además del trazo principal.
N_PERSISTENCIA = 3


# ==================================================
# Plot principal del osciloscopio
# ==================================================
def tek_scope_plot(
    ax,
    t,
    signals,
    colors,
    volts_per_div,
    time_per_div,
    offsets=None,
    channel_names=None,
    ch_texts=None,
    time_text=None,
    title_text=None,
    n_vdiv=8,
    n_tdiv=10,
    title="",
    noise_std=0.07
):
    """
    Dibuja una vista tipo osciloscopio profesional.

    RENDIMIENTO: la retícula y las líneas se crean una sola vez y se guardan
    en el propio eje (ax._tek). En cada fotograma solo se actualizan los
    datos (set_data), en vez de borrar y reconstruir todo el gráfico.
    Se reconstruye solo si el eje se ha borrado (p. ej. tras ver el espectro)
    o si cambian los canales visibles o la base de tiempos.

    IMPORTANTE:
    - Los textos (CH1/CH2, TIME, TITLE) NO se crean aquí,
      solo se actualizan. Deben crearse UNA VEZ en main.py
    """

    if offsets is None:
        offsets = [0.0] * len(signals)

    if channel_names is None:
        channel_names = [f"CH{i+1}" for i in range(len(signals))]

    cache = getattr(ax, "_tek", None)

    # ===============================
    # Fondo, ejes y retícula (solo al crear o si el eje se ha borrado)
    # ===============================
    if cache is None or cache["centro"] not in ax.lines:
        ax.clear()
        ax.set_facecolor("#0b0b0b")
        ax.figure.patch.set_facecolor("#0b0b0b")

        # Reservar espacio arriba y abajo (leyendas)
        ax.set_position([0.12, 0.18, 0.83, 0.64])

        # Ejes en DIVISIONES (vertical)
        ax.set_ylim(-n_vdiv / 2, n_vdiv / 2)
        ax.set_yticks(np.linspace(-n_vdiv / 2, n_vdiv / 2, n_vdiv + 1))

        ax.grid(True, color="#707070", linewidth=1.6)
        ax.minorticks_on()
        ax.grid(which="minor", color="#404040", linestyle=":", linewidth=0.9)

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        # El espectro pone las marcas en blanco y ax.clear() no lo deshace:
        # aquí vuelven a negro (invisibles sobre el fondo, como al arrancar).
        ax.tick_params(which="both", colors="black")

        # Línea central (0 divisiones)
        centro = ax.axhline(0, color="#aaaaaa", linewidth=1.2)

        cache = {"centro": centro, "time_div": None, "canales": None,
                 "refs": [], "trazas": [], "textos": None, "fondo": None}
        ax._tek = cache

    # ===============================
    # Base de tiempos (solo si cambia)
    # ===============================
    if cache["time_div"] != time_per_div:
        ax.set_xlim(0, n_tdiv * time_per_div * 1e3)
        ax.set_xticks(np.linspace(0, n_tdiv * time_per_div * 1e3, n_tdiv + 1))
        ax.set_xticklabels([])
        cache["time_div"] = time_per_div
        cache["fondo"] = None

    # ===============================
    # Líneas por canal (solo si cambian los canales visibles)
    # ===============================
    canales = tuple(zip(channel_names, colors))
    if cache["canales"] != canales:
        for artista in cache["refs"] + [l for grupo in cache["trazas"] for l in grupo]:
            artista.remove()
        cache["refs"], cache["trazas"] = [], []
        # animated=True: no forman parte del fondo guardado; tek_scope_blit
        # las pinta encima en cada fotograma.
        for col in colors:
            # Referencia 0 V real por canal
            cache["refs"].append(ax.axhline(0, color=col, linestyle="--",
                                            linewidth=1.5, alpha=0.7, animated=True))
            # Trazos de persistencia + trazo principal (más grueso)
            grupo = [ax.plot([], [], color=col, alpha=0.1, linewidth=1.5, animated=True)[0]
                     for _ in range(N_PERSISTENCIA)]
            grupo.append(ax.plot([], [], color=col, linewidth=2.0, antialiased=True,
                                 animated=True)[0])
            cache["trazas"].append(grupo)
        cache["canales"] = canales
        cache["fondo"] = None

    # ===============================
    # Actualizar datos
    # ===============================
    x = t * 1e3
    # Con Time/div grande llega la envolvente mín/máx (tiempos repetidos): el
    # ruido de persistencia ahí solo engorda el trazo y cuesta mucho dibujarlo.
    envolvente = len(t) > 1 and t[0] == t[1]
    for sig, vdiv, off, ref, grupo in zip(signals, volts_per_div, offsets,
                                          cache["refs"], cache["trazas"]):
        ref.set_ydata([off / vdiv, off / vdiv])
        y = (sig + off) / vdiv
        if envolvente:
            for linea in grupo[:-1]:
                linea.set_data([], [])
        else:
            ruido = np.random.normal(0, noise_std, size=(N_PERSISTENCIA, len(sig)))
            for linea, r in zip(grupo[:-1], ruido):
                linea.set_data(x, y + r)
        grupo[-1].set_data(x, y)

    # ===============================
    # CH1 / CH2 ARRIBA (solo si cambian nombre, V/div o color)
    # ===============================
    if ch_texts is not None:
        firma = tuple(zip(channel_names, volts_per_div, colors))
        if cache["textos"] != firma or len(ch_texts) != len(firma):
            for txt in ch_texts:
                txt.remove()
            ch_texts.clear()

            y_text = 0.95
            for name, vdiv, col in zip(channel_names, volts_per_div, colors):
                txt = ax.figure.text(
                    0.08,
                    y_text,
                    f"{name}  {vdiv:.2f} V/div",
                    color=col,
                    fontsize=14,
                    va="top"
                )
                ch_texts.append(txt)
                y_text -= 0.05
            cache["textos"] = firma
            cache["fondo"] = None

    # ===============================
    # TIME ABAJO (ACTUALIZAR)
    # ===============================
    if time_text is not None:
        time_text.set_text(f"Time  {format_time_div(time_per_div)}")

    # ===============================
    # TÍTULO (ACTUALIZAR)
    # ===============================
    if title_text is not None and title_text.get_text() != title:
        title_text.set_text(title)
        cache["fondo"] = None


# ==================================================
# Dibujo rápido (blitting)
# ==================================================
def tek_scope_blit(ax, canvas):
    """
    Muestra en pantalla lo preparado por tek_scope_plot.

    El fondo (retícula, marcas y textos) no cambia entre fotogramas: se dibuja
    una vez, se guarda como imagen y en cada fotograma solo se restaura esa
    imagen y se pintan encima las trazas. Es mucho más barato que redibujar la
    figura entera, sobre todo en PCs modestos.
    """
    cache = ax._tek
    tamano = canvas.get_width_height()

    if cache["fondo"] is None or cache.get("fondo_tamano") != tamano:
        canvas.draw()                       # todo menos las trazas (animated)
        cache["fondo"] = canvas.copy_from_bbox(ax.figure.bbox)
        cache["fondo_tamano"] = tamano
    else:
        canvas.restore_region(cache["fondo"])

    for artista in cache["refs"]:
        ax.draw_artist(artista)
    for grupo in cache["trazas"]:
        for linea in grupo:
            ax.draw_artist(linea)

    canvas.blit(ax.figure.bbox)
