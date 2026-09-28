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

    IMPORTANTE:
    - Los textos (CH1/CH2, TIME, TITLE) NO se crean aquí,
      solo se actualizan. Deben crearse UNA VEZ en main.py
    """

    ax.clear()

    if offsets is None:
        offsets = [0.0] * len(signals)

    if channel_names is None:
        channel_names = [f"CH{i+1}" for i in range(len(signals))]

    # ===============================
    # Fondo
    # ===============================
    ax.set_facecolor("#0b0b0b")
    ax.figure.patch.set_facecolor("#0b0b0b")

    # Reservar espacio arriba y abajo (leyendas)
    ax.set_position([0.12, 0.18, 0.83, 0.64])

    # ===============================
    # Ejes en DIVISIONES
    # ===============================
    ax.set_xlim(0, n_tdiv * time_per_div * 1e3)
    ax.set_ylim(-n_vdiv / 2, n_vdiv / 2)

    # ===============================
    # Retícula
    # ===============================
    ax.set_xticks(np.linspace(0, n_tdiv * time_per_div * 1e3, n_tdiv + 1))
    ax.set_yticks(np.linspace(-n_vdiv / 2, n_vdiv / 2, n_vdiv + 1))

    ax.grid(True, color="#707070", linewidth=1.6)
    ax.minorticks_on()
    ax.grid(which="minor", color="#404040", linestyle=":", linewidth=0.9)

    ax.set_xticklabels([])
    ax.set_yticklabels([])

    # Línea central (0 divisiones)
    ax.axhline(0, color="#aaaaaa", linewidth=1.2)

    # ===============================
    # Referencia 0 V real por canal
    # ===============================
    for off, vdiv, col in zip(offsets, volts_per_div, colors):
        ax.axhline(
            off / vdiv,
            color=col,
            linestyle="--",
            linewidth=1.5,
            alpha=0.7
        )

    # ===============================
    # Dibujar señales (Optimizado)
    # ===============================
    for sig, col, vdiv, off in zip(signals, colors, volts_per_div, offsets):
        y = (sig + off) / vdiv

        # Reducimos de 20 a 3 trazos de persistencia para ganar velocidad
        for i in range(3):
            noise = np.random.normal(0, noise_std, size=len(sig))
            ax.plot(
                t * 1e3,
                y + noise,
                color=col,
                alpha=0.1,  # Un poco más visible ya que hay menos
                linewidth=1.5
            )

        # Trazo principal (más grueso)
        ax.plot(
            t * 1e3,
            y,
            color=col,
            linewidth=2.0,
            antialiased=True # Mejora visual sin gran coste
        )

    # ===============================
    # CH1 / CH2 ARRIBA (ACTUALIZAR)
    # ===============================
    if ch_texts is not None:
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

    # ===============================
    # TIME ABAJO (ACTUALIZAR)
    # ===============================
    if time_text is not None:
        time_text.set_text(f"Time  {format_time_div(time_per_div)}")

    # ===============================
    # TÍTULO (ACTUALIZAR)
    # ===============================
    if title_text is not None:
        title_text.set_text(title)
