import matplotlib
matplotlib.use("TkAgg")

import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import datetime
from tkinter import filedialog

from signal_generator import SignalGenerator
from oscilloscope import Oscilloscope
from scope_plot import tek_scope_plot
from digital_filters import apply_filter, filter_frequency_response
from signal_utils import safe_get, safe_int, safe_float
from gui_utils import resource_path


import sys
import os

def resource_path(relative_path):
    """
    Devuelve la ruta correcta tanto en modo .py como en .exe (PyInstaller)
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ==================================================
# CONFIG
# ==================================================
REFRESH_MS = 50  # ms
SPECTRUM_SPAN_HZ = 5000   # ±5 kHz alrededor del pico


# ==================================================
# INSTRUMENTOS
# ==================================================
generator = SignalGenerator()

scope = Oscilloscope(fs=200_000, buffer_seconds=1.0)
scope.channels["CH3"]["enabled"] = False

last_gen_state = None


# ==================================================
# VENTANA PRINCIPAL
# ==================================================
root = tk.Tk()
root.title("SignalLab – Generador y analizador de señales virtual")
root.geometry("1450x780")

root.rowconfigure(0, weight=0)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=0)
root.columnconfigure(0, weight=5)
root.columnconfigure(1, weight=0)


# ==================================================
# FRAME SUPERIOR –
# ==================================================
frame_signals = tk.Frame(root, pady=5)
frame_signals.grid(row=0, column=0, columnspan=2, sticky="ew")

frame_gen = tk.Frame(frame_signals)
frame_gen.grid(row=0, column=0, sticky="nw", padx=(0, 20))

frame_mixer = tk.Frame(frame_signals)
frame_mixer.grid(row=0, column=1, sticky="nw")

frame_adc = tk.Frame(frame_signals)
frame_adc.grid(row=0, column=2, sticky="nw")

frame_filtros = tk.Frame(frame_signals)
frame_filtros.grid(row=0, column=3, sticky="nw")

# ==================================================
# FRAME SUPERIOR – CONFIGURACIÓN DE SEÑALES
# ==================================================
waves = ["Senoidal", "Cuadrada", "Diente", "Triangular", "Gaussiana"]

wave1 = tk.StringVar(value="Senoidal")
amp1 = tk.DoubleVar(value=12.0)
freq1 = tk.DoubleVar(value=2000.0)
phase1 = tk.DoubleVar(value=0.0)
duty1 = tk.DoubleVar(value=50.0)
offset1 = tk.DoubleVar(value=0.0)

wave2 = tk.StringVar(value="Senoidal")
amp2 = tk.DoubleVar(value=5.0)
freq2 = tk.DoubleVar(value=500.0)
phase2 = tk.DoubleVar(value=0.0)
duty2 = tk.DoubleVar(value=50.0)
offset2 = tk.DoubleVar(value=0.0)

# ==============================
# MIXER (CH3) – GUI
# ==============================
mod_type = tk.StringVar(value="SUM")   # SUM/ AM / DBL / FM
mu_kf = tk.DoubleVar(value=0.5)       # μ (AM, DBL) o kf (FM)

# ==============================
# DAC (CH3) – GUI
# ==============================
freq_sample = tk.IntVar(value=20000) # Frecuencia muestreo
bits_res = tk.IntVar(value=4)       # Bits de resolucion
adc_ch3_var = tk.BooleanVar()       # Activa la ADC en el canal 3.
vref_var = tk.DoubleVar(value=10.0) # Tensión de referencia.

# ==============================
# Filtros (CH3) – GUI
# ==============================
filters = tk.StringVar(value="Paso Bajo")  # "Paso Bajo", "Paso Álto", "Pasa Banda", "Rechaza Banda"]
freq_filtro = tk.DoubleVar(value=1000)
orden = tk.IntVar(value=1) 
Ancho_Banda = tk.DoubleVar(value=1000)
filtro_ch3_var = tk.BooleanVar()       # Activa la Filtro en el canal 3.
show_filter_resp_var = tk.BooleanVar(value=False)

# ==================================================
# GENERADOR DE SEÑALES (BONOTES DE CONTROL)
# ==================================================

tk.Label(frame_gen, text="GENERADOR SEÑALES", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

headers = ["Canal", "Forma", "Amplitud (V)", "Frecuencia (Hz)", "Fase (°)", "Duty (%)", "Offset (V)"]

for i, h in enumerate(headers):
    lbl = tk.Label(frame_gen, text=h)
    lbl.grid(row=1, column=i, padx=5)

# CH1
tk.Label(frame_gen, text="CH1").grid(row=2, column=0)
tk.OptionMenu(frame_gen, wave1, *waves).grid(row=2, column=1, sticky="ew")
tk.Entry(frame_gen, textvariable=amp1, width=8).grid(row=2, column=2)
tk.Entry(frame_gen, textvariable=freq1, width=8).grid(row=2, column=3)
tk.Entry(frame_gen, textvariable=phase1, width=8).grid(row=2, column=4)
tk.Entry(frame_gen, textvariable=duty1, width=8).grid(row=2, column=5)
tk.Entry(frame_gen, textvariable=offset1, width=8).grid(row=2, column=6)

# CH2
tk.Label(frame_gen, text="CH2").grid(row=3, column=0)
tk.OptionMenu(frame_gen, wave2, *waves).grid(row=3, column=1, sticky="ew")
tk.Entry(frame_gen, textvariable=amp2, width=8).grid(row=3, column=2)
tk.Entry(frame_gen, textvariable=freq2, width=8).grid(row=3, column=3)
tk.Entry(frame_gen, textvariable=phase2, width=8).grid(row=3, column=4)
tk.Entry(frame_gen, textvariable=duty2, width=8).grid(row=3, column=5)
tk.Entry(frame_gen, textvariable=offset2, width=8).grid(row=3, column=6)


# ==================================================
# MEZCLADOR (BONOTES DE CONTROL) GENERA CH3
# ==================================================

tk.Label(frame_mixer, text="MEZCLADOR / MODULADOR", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))


tk.Label(frame_mixer, text="Canal").grid(row=1, column=0, sticky="w", padx=5)
tk.Label(frame_mixer, text="Modo").grid(row=1, column=1, sticky="w", padx=5)
tk.Label(frame_mixer, text="Parámetro").grid(row=1, column=2, sticky="w", padx=5)

tk.Label(frame_mixer, text="MIXER (CH3)").grid(row=2, column=0, sticky="w", padx=5)

tk.OptionMenu(
    frame_mixer,
    mod_type,
    "SUM",
    "AM",
    "DBL",
    "FM"
).grid(row=2, column=1, sticky="ew", padx=5)

tk.Entry(
    frame_mixer,
    textvariable=mu_kf,
    width=8
).grid(row=2, column=2, padx=5)

tk.Label(
    frame_mixer,
    text="CH1 = Portadora | CH2 = Moduladora\nParámetro = μ (AM/DBL) o kf (escala x1000) (FM)",
    justify="left"
).grid(row=3, column=0, columnspan=3, sticky="w", padx=5, pady=(6, 0))


# ==================================================
# CONVERSOR ANALOGICO DIGITAL (BONOTES DE CONTROL) GENERA CH3
# ==================================================

tk.Label(frame_adc, text="CONVERSOR ANALÓGICO/DIGITAL", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

tk.Label(frame_adc, text="Fruencia muestro").grid(row=1, column=0, sticky="w", padx=5)
tk.Label(frame_adc, text="Vref ADC (±V)").grid(row=2, column=0, sticky="w", padx=5)
tk.Label(frame_adc, text="Bit cuantificacion (max 24)").grid(row=3, column=0, sticky="w", padx=5)
tk.Label(frame_adc, text="Activar ADC en (CH3)").grid(row=4, column=0, sticky="w", padx=5)

tk.Entry(frame_adc, textvariable=freq_sample, width=8).grid(row=1, column=1, sticky="w", padx=5)
tk.Entry(frame_adc, textvariable=vref_var, width=8).grid(row=2, column=1, sticky="w", padx=5)
tk.Entry(frame_adc, textvariable=bits_res, width=8).grid(row=3, column=1, sticky="w", padx=5)
chk_adc_ch3 = tk.Checkbutton(frame_adc, text="Activar ADC en (CH3)", variable=adc_ch3_var, onvalue=True, offvalue=False)
chk_adc_ch3.grid(row=4, column=1, sticky="w", padx=5)


# ==================================================
# FILTROS (BONOTES DE CONTROL) GENERA CH3
# ==================================================

tk.Label(frame_filtros, text="FILTROS DE SEÑAL", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

tk.Label(frame_filtros, text="Tipo filtro").grid(row=1, column=0, sticky="w", padx=5)
tk.Label(frame_filtros, text="Frecuencia corte/res.").grid(row=2, column=0, sticky="w", padx=5)
tk.Label(frame_filtros, text="Orden").grid(row=3, column=0, sticky="w", padx=5)
tk.Label(frame_filtros, text="Ancho Banda").grid(row=4, column=0, sticky="w", padx=5)
tk.Label(frame_filtros, text="Activar Filtro en (CH3)").grid(row=5, column=0, sticky="w", padx=5)
tk.Label(frame_filtros, text="Mostra filtro en espectro").grid(row=6, column=0, sticky="w", padx=5)

tk.OptionMenu(frame_filtros,filters,"Paso Bajo", "Paso Álto", "Pasa Banda", "Rechaza Banda").grid(row=1, column=1, sticky="ew", padx=5)
tk.Entry(frame_filtros, textvariable=freq_filtro, width=8).grid(row=2, column=1, sticky="w", padx=5)
tk.Entry(frame_filtros, textvariable=orden, width=8).grid(row=3, column=1, sticky="w", padx=5)
tk.Entry(frame_filtros, textvariable=Ancho_Banda, width=8).grid(row=4, column=1, sticky="w", padx=5)
chk_filter_ch3 = tk.Checkbutton(frame_filtros, variable=filtro_ch3_var, onvalue=True, offvalue=False)
chk_filter_ch3.grid(row=5, column=1, sticky="w", padx=5)
chk_filter_resp = tk.Checkbutton(frame_filtros,
    variable=show_filter_resp_var,
    onvalue=True,
    offvalue=False
)
chk_filter_resp.grid(row=6, column=1, sticky="w", padx=5)

tk.Label(frame_filtros, text="Hz.").grid(row=2, column=2, sticky="w", padx=5)
tk.Label(frame_filtros, text="Max 15.").grid(row=3, column=2, sticky="w", padx=5)
tk.Label(frame_filtros, text="Hz").grid(row=4, column=2, sticky="w", padx=5)


# ==================================================
# OSCILOSCOPIO (PLOT)
# ==================================================
frame_plot = tk.Frame(root, bg="black")
frame_plot.grid(row=1, column=0, sticky="nsew")

fig = Figure(figsize=(6, 4), dpi=100)
ax = fig.add_subplot(111)

ch_texts = []
time_text = fig.text(0.50, 0.04, "", color="white", fontsize=14, ha="center")
title_text = fig.text(0.50, 0.98, "", color="white", fontsize=18, ha="center", va="top")

canvas = FigureCanvasTkAgg(fig, master=frame_plot)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

fft_legend = ax.text(
    0.02, 0.95, "", transform=ax.transAxes,
    va="top", ha="left", fontsize=12, color="white",
    bbox=dict(facecolor="black", alpha=0.4, edgecolor="none"),
    visible=False
)


# ==================================================
# BOTONES
# ==================================================
frame_buttons = tk.Frame(root, padx=10)
frame_buttons.grid(row=1, column=1, sticky="ns")
frame_buttons.configure(width=600)
frame_buttons.grid_propagate(False)

for i in range(4):
    frame_buttons.rowconfigure(i, weight=1)
for j in range(6):
    frame_buttons.columnconfigure(j, weight=0)


# ==================================================
# FUNCIONES PARA ACTUALIZAR Y MOSTRAR
# ==================================================
def update_channel_buttons():
    for ch, btn in [("CH1", btn_ch1), ("CH2", btn_ch2), ("CH3", btn_ch3)]:
        if scope.channels[ch]["enabled"]:
            btn.config(bg=scope.channels[ch]["color"],
                       fg="black", relief=tk.SUNKEN)
        else:
            btn.config(bg="#303030",
                       fg="#aaaaaa", relief=tk.RAISED)

def update_spectrum_buttons():
    buttons = {
        "CH1": btn_spec_ch1,
        "CH2": btn_spec_ch2,
        "CH3": btn_spec_ch3,
    }

    for ch, btn in buttons.items():
        if scope.mode == "SPECTRUM" and scope.spec_channel == ch:
            btn.config(
                bg=scope.channels[ch]["color"],
                fg="black",
                relief=tk.SUNKEN
            )
        else:
            btn.config(
                bg="#303030",
                fg="#aaaaaa",
                relief=tk.RAISED
            )

def toggle_ch(ch):
    scope.toggle_channel(ch)
    update_channel_buttons()

def toggle_spectrum(ch):
    scope.show_spectrum(ch)
    update_spectrum_buttons()

# Variables globales para los botones
btn_master_dc = None
btn_master_ac = None
btn_master_gnd = None

def update_generator_from_gui():
    global last_gen_state

    # -------------------------
    # CH1 – Portadora
    # -------------------------
    ch1 = (
        wave1.get(),
        safe_get(amp1, 0),
        safe_get(freq1, 0),
        safe_get(phase1, 0),
        safe_get(duty1, 50),
        safe_get(offset1, 0),
    )

    # -------------------------
    # CH2 – Moduladora
    # -------------------------
    ch2 = (
        wave2.get(),
        safe_get(amp2, 0),
        safe_get(freq2, 0),
        safe_get(phase2, 0),
        safe_get(duty2, 50),
        safe_get(offset2, 0),
    )

    # -------------------------
    # Estado global (CLAVE)
    # -------------------------
    mu_val = safe_get(mu_kf, 0.5)

    adc_fs_val = int(safe_get(freq_sample, 40000))
    adc_bits_val = int(safe_get(bits_res, 4))
    vref_val = float(safe_get(vref_var, 10.0))

    state = ch1 + ch2 + (
        mod_type.get(),
        mu_val,
        adc_ch3_var.get(),
        adc_fs_val,
        adc_bits_val,
        vref_val
    )

    if state == last_gen_state:
        return

    # -------------------------
    # Actualizar CH1
    # -------------------------
    generator.channels["CH1"].update({
        "wave": ch1[0],
        "amp": ch1[1],
        "freq": ch1[2],
        "phase": ch1[3],
        "duty": ch1[4],
        "offset": ch1[5],
    })

    # -------------------------
    # Actualizar CH2
    # -------------------------
    generator.channels["CH2"].update({
        "wave": ch2[0],
        "amp": ch2[1],
        "freq": ch2[2],
        "phase": ch2[3],
        "duty": ch2[4],
        "offset": ch2[5],
    })

    # -------------------------
    # Actualizar MIXER (CH3)
    # -------------------------
    mtype = mod_type.get()

    ch3_conf = {
        "mode": "MIXER",
        "type": mtype,
    }

    if mtype in ("AM"):
        ch3_conf["mu"] = mu_val

    elif mtype == "FM":
        ch3_conf["kf"] = mu_val

    # SUM no necesita parámetros

    generator.channels["CH3"].update(ch3_conf)

    # -------------------------
    # Añade datos del ADC y si se activa
    # -------------------------

    generator.adc_enabled = adc_ch3_var.get()
    generator.adc_fs = adc_fs_val
    generator.adc_bits = adc_bits_val
    generator.adc_vref = vref_val


    # -------------------------
    # FFT coherente
    # -------------------------
    if scope.mode == "FFT":
        scope.fft_buffer = scope.buffers[scope.fft_channel].copy()
        scope.fft_frozen = False
        scope.fft_cache = None

    last_gen_state = state

def update_coupling_ui(mode):
    """Cambia los colores de los botones para indicar cuál está activo"""
    # Estilos: Encendido (Verde) vs Apagado (Gris estándar)
    style_on = {"bg": "#00FF00", "fg": "black"}
    style_off = {"bg": "#f0f0f0", "fg": "black"} # O el color por defecto de tu sistema

    if btn_master_dc:
        btn_master_dc.config(**(style_on if mode == "DC" else style_off))
    if btn_master_ac:
        btn_master_ac.config(**(style_on if mode == "AC" else style_off))
    if btn_master_gnd:
        btn_master_gnd.config(**(style_on if mode == "GND" else style_off))

def set_global_coupling(mode):
    """Aplica el modo a todos los canales y actualiza la visualización"""
    for ch in ["CH1", "CH2", "CH3"]:
        scope.channels[ch]["coupling"] = mode
    update_coupling_ui(mode)

# ---- CH1 ----
btn_ch1 = tk.Button(frame_buttons, text="CH1",
                    command=lambda: toggle_ch("CH1"))

btn_ch1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH1 V/div -",
          command=lambda: scope.change_vdiv("CH1", 0.5)
          ).grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH1 V/div +",
          command=lambda: scope.change_vdiv("CH1", 2)
          ).grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH1 Offset +",
          command=lambda: scope.change_offset(
              "CH1", scope.channels["CH1"]["vdiv"]/2)
          ).grid(row=0, column=3, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH1 Offset -",
          command=lambda: scope.change_offset(
              "CH1", -scope.channels["CH1"]["vdiv"]/2)
          ).grid(row=0, column=4, sticky="nsew", padx=5, pady=5)


btn_spec_ch1 = tk.Button(
    frame_buttons,
    text="SPECTRUM CH1",
    command=lambda: toggle_spectrum("CH1")
)
btn_spec_ch1.grid(row=0, column=5, sticky="nsew", padx=5, pady=5)

# ---- CH2 ----
btn_ch2 = tk.Button(frame_buttons, text="CH2",
                    command=lambda: toggle_ch("CH2"))

btn_ch2.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH2 V/div -",
          command=lambda: scope.change_vdiv("CH2", 0.5)
          ).grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH2 V/div +",
          command=lambda: scope.change_vdiv("CH2", 2)
          ).grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH2 Offset +",
          command=lambda: scope.change_offset(
              "CH2", scope.channels["CH2"]["vdiv"]/2)
          ).grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH2 Offset -",
          command=lambda: scope.change_offset(
              "CH2", -scope.channels["CH2"]["vdiv"]/2)
          ).grid(row=1, column=4, sticky="nsew", padx=5, pady=5)

btn_spec_ch2 = tk.Button(
    frame_buttons,
    text="SPECTRUM CH2",
    command=lambda: toggle_spectrum("CH2")
)
btn_spec_ch2.grid(row=1, column=5, sticky="nsew", padx=5, pady=5)

# ---- CH3 ----
btn_ch3 = tk.Button(frame_buttons, text="CH3",
                    command=lambda: toggle_ch("CH3"))

btn_ch3.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH3 V/div -",
          command=lambda: scope.change_vdiv("CH3", 0.5)
          ).grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH3 V/div +",
          command=lambda: scope.change_vdiv("CH3", 2)
          ).grid(row=2, column=2, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH3 Offset +",
          command=lambda: scope.change_offset(
              "CH3", scope.channels["CH3"]["vdiv"]/2)
          ).grid(row=2, column=3, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="CH3 Offset -",
          command=lambda: scope.change_offset(
              "CH3", -scope.channels["CH3"]["vdiv"]/2)
          ).grid(row=2, column=4, sticky="nsew", padx=5, pady=5)

# si tienes MIXER
btn_spec_ch3 = tk.Button(
    frame_buttons,
    text="SPECTRUM MIXER",
    command=lambda: toggle_spectrum("CH3")
)
btn_spec_ch3.grid(row=2, column=5, sticky="nsew", padx=5, pady=5)

update_channel_buttons()

# ==================================================
# BASE TIEMPOS
# ==================================================
tk.Button(frame_buttons, text="Time/div +",
          command=lambda: scope.change_time_div(2)
          ).grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

tk.Button(frame_buttons, text="Time/div -",
          command=lambda: scope.change_time_div(0.5)
          ).grid(row=3, column=1, sticky="nsew", padx=5, pady=5)

step = lambda: scope.time_div / 10  # PASO TIEMPO 
tk.Button(
    frame_buttons,
    text="⟵ Time",
    command=lambda: setattr(
        scope,
        "time_position",
        scope.time_position + step()
    )
).grid(row=3, column=2, sticky="nsew", padx=5, pady=5)

tk.Button(
    frame_buttons,
    text="Time ⟶",
    command=lambda: setattr(
        scope,
        "time_position",
        scope.time_position - step()
    )
).grid(row=3, column=3, sticky="nsew",padx=5, pady=5)


# ==================================================
# ACOPLAMIENTO MASTER 
# ==================================================

btn_master_dc = tk.Button(
    frame_buttons, 
    text="DC MODE", 
    bg="#00FF00", # Empieza encendido
    command=lambda: set_global_coupling("DC")
)
btn_master_dc.grid(row=3, column=4, sticky="nsew",padx=5, pady=5)

btn_master_ac = tk.Button(
    frame_buttons, 
    text="AC MODE", 
    command=lambda: set_global_coupling("AC")
)
btn_master_ac.grid(row=3, column=5, sticky="nsew",padx=5, pady=5)



# ==================================================
# CONTROLES INFERIORES (GUARDAR CAPTURA)
# ==================================================

def save_screenshot():
    # Nombre por defecto con fecha y hora
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"Capture_SignalLab_{timestamp}.png"

    # Diálogo para elegir dónde guardar
    filepath = filedialog.asksaveasfilename(
        defaultextension=".png",
        initialfile=default_name,
        filetypes=[("PNG image", "*.png")]
    )

    if not filepath:
        return  # usuario canceló

    # Guardar figura EXACTA
    fig.savefig(
        filepath,
        dpi=150,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight"
    )


frame_capture = tk.Frame(root)
frame_capture.grid(row=2, column=0, sticky="w", padx=10, pady=5)

btn_capture = tk.Button(
    frame_capture,
    text="📸 Guardar captura (.PNG)",
    command=save_screenshot,
    padx=15,
    pady=8,
    font=("Arial", 10)
)
btn_capture.pack(anchor="w")

# ==================================================
# LOGO
# ==================================================
frame_signature = tk.Frame(root)
frame_signature.grid(row=2, column=1, sticky="se", padx=15, pady=10)

logo_path = resource_path("assets/logo.png")

logo_img = Image.open(logo_path)
logo_img = logo_img.resize((276, 101), Image.LANCZOS)
logo = ImageTk.PhotoImage(logo_img)

tk.Label(frame_signature, text="Diseñado por Álvar Legaz",
         font=("Arial", 10, "bold"), fg="#888").pack(anchor="e")
tk.Label(frame_signature, image=logo).pack(anchor="e")




# ==================================================
# LOOP PRINCIPAL
# ==================================================


def update():
    update_generator_from_gui()

    n = int(scope.fs * (REFRESH_MS / 1000))
    # t debe ser relativo al bloque (0 a n), el generador hará el resto
    t = np.arange(n) / scope.fs 

    ch1 = generator.generate("CH1", t)
    ch2 = generator.generate("CH2", t)
    ch3 = generator.generate("CH3", t)

    # ---- FILTRO DIGITAL (solo CH3) ----
    if filtro_ch3_var.get():
        ch3 = apply_filter(
            signal=ch3,
            fs=scope.fs,
            filter_type=filters.get(),
            freq=safe_get(freq_filtro, 0),
            order = min(safe_int(orden, 1), 15),
            bandwidth=safe_get(Ancho_Banda, None)
        )

    samples = {
        "CH1": ch1,
        "CH2": ch2,
        "CH3": ch3,
    }

    scope.acquire(samples)
    frame = scope.step()

    if frame["mode"] == "TIME":
        fft_legend.set_visible(False)

        tek_scope_plot(
            ax,
            frame["t"],
            frame["signals"],
            frame["colors"],
            frame["volts"],
            frame["time_div"],
            offsets=frame["offsets"],
            channel_names=frame["names"],
            ch_texts=ch_texts,
            time_text=time_text,
            title_text=title_text
        )

    elif frame["mode"] == "SPECTRUM":
        ax.clear()
        ax.set_facecolor("#0b0b0b")
        ax.figure.patch.set_facecolor("#0b0b0b")

        freqs = frame["freqs"]
        mag = frame["mag_db"]

        # ---- FRECUENCIA DOMINANTE ----
        idx_max = np.argmax(mag)
        f_center = freqs[idx_max]

        # ---- VENTANA CENTRADA ----
        f_min = max(0, f_center - SPECTRUM_SPAN_HZ)
        f_max = f_center + SPECTRUM_SPAN_HZ

        mask = (freqs >= f_min) & (freqs <= f_max)
        freqs_view = freqs[mask]
        mag_view = mag[mask]

        ax.plot(
            freqs_view,
            mag_view,
            color=frame["color"],
            linewidth=2
        )

        ax.set_xlim(f_min, f_max)

        # ---- RESPUESTA EN FRECUENCIA DEL FILTRO ----
        if (
            filtro_ch3_var.get()
            and show_filter_resp_var.get()
            and frame["channel"] == "CH3"
        ):
            freqs_f, mag_f = filter_frequency_response(
                fs=scope.fs,
                filter_type=filters.get(),
                freq=safe_get(freq_filtro, 0),
                order=min(safe_int(orden, 1), 15),
                bandwidth=safe_get(Ancho_Banda, None)
            )

            if freqs_f is not None:
                mask_f = (freqs_f >= f_min) & (freqs_f <= f_max)

                ax.plot(
                    freqs_f[mask_f],
                    mag_f[mask_f],
                    linestyle="--",
                    linewidth=2,
                    color="#00FF00",
                    alpha=0.9,
                    label="Filtro"
                )
                ax.legend(loc="upper right")

        ax.set_title(f"Spectrum {frame['channel']}", color="white")
        ax.set_xlabel("Frecuencia (kHz)", color="white")
        ax.set_ylabel("Nivel (dBV RMS)", color="white")

        ax.xaxis.set_major_formatter(
            lambda x, pos: f"{x/1000:.0f}"
        )

        ax.grid(True, color="#444")
        ax.tick_params(colors="white")

        fft_legend.set_text(
            f"{frame['channel']}  Spectrum\n"
            f"Fs = {frame['fs']/1000:.0f} kSa/s\n"
            f"RBW ≈ {frame['rbw']:.1f} Hz"
        )
        fft_legend.set_color(frame["color"])
        fft_legend.set_visible(True)

    canvas.draw()
    update_spectrum_buttons()
    root.after(REFRESH_MS, update)


update()
root.mainloop()
