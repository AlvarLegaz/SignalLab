import numpy as np


class Oscilloscope:
    """
    Digital Oscilloscope + Spectrum Analyzer Engine
    """

    def __init__(self, fs=200_000, buffer_seconds=1.0):
        self.fs = fs
        self.buffer_size = int(fs * buffer_seconds)

        self.buffers = {
            "CH1": np.zeros(self.buffer_size),
            "CH2": np.zeros(self.buffer_size),
            "CH3": np.zeros(self.buffer_size),
        }

        self.write_idx = 0

        self.time_position = 0.0        # segundos (scroll hacia el pasado)
        self.time_reference = "CENTER" # CENTER o LEFT

        # -----------------------------
        # Estados
        # -----------------------------
        self.time_div = 0.2e-3
        self.mode = "TIME"

        # FFT (modo antiguo)
        self.fft_channel = "CH1"
        self.fft_frozen = False
        self.fft_cache = None
        self.fft_buffer = None

        # -----------------------------
        # Spectrum Analyzer
        # -----------------------------
        self.spec_channel = "CH1"
        self.spec_rbw = 50.0        # Hz
        self.spec_alpha = 0.2       # Promedio exponencial
        self.spec_max_hold = False

        self.spec_psd_avg = None
        self.spec_max = None

        # -----------------------------
        # Visual
        # -----------------------------
        # Configuración de canales
        self.channels = {
            "CH1": {"enabled": True, "vdiv": 5.0, "offset": 0.0, "color": "#FFFF00", "coupling": "DC", "prev_ac_out": 0.0},
            "CH2": {"enabled": True, "vdiv": 5.0, "offset": 0.0, "color": "#FF00FF", "coupling": "DC", "prev_ac_out": 0.0},
            "CH3": {"enabled": False, "vdiv": 5.0, "offset": 0.0, "color": "#00FFFF", "coupling": "DC", "prev_ac_out": 0.0},
        }

    # -----------------------------
    # Adquisición
    # -----------------------------

    def acquire(self, samples_dict):
        """
        Recibe un diccionario con nuevos samples y los procesa según el acoplamiento.
        """
        n = len(next(iter(samples_dict.values())))
        
        for ch, data in samples_dict.items():
            # Aplicar acoplamiento (AC/DC/GND) antes de guardar en buffer
            processed_data = self._apply_coupling(ch, data)
            
            # Escritura circular
            end_idx = (self.write_idx + n) % self.buffer_size
            if end_idx > self.write_idx:
                self.buffers[ch][self.write_idx:end_idx] = processed_data
            else:
                first_part = self.buffer_size - self.write_idx
                self.buffers[ch][self.write_idx:] = processed_data[:first_part]
                self.buffers[ch][:end_idx] = processed_data[first_part:]
        
        self.write_idx = (self.write_idx + n) % self.buffer_size

    def _apply_coupling(self, ch, data):
        """
        Filtra la señal según el modo seleccionado: DC, AC o GND.
        """
        mode = self.channels[ch]["coupling"]
        
        if mode == "GND":
            return np.zeros_like(data)
        
        if mode == "AC":
            # Filtro Paso Alto Digital (Bloqueador de DC)
            # y[n] = x[n] - x[n-1] + alpha * y[n-1]
            alpha = 0.996  # Constante de tiempo del filtro
            out = np.zeros_like(data)
            
            # Recuperamos el último valor procesado para dar continuidad entre bloques
            prev_y = self.channels[ch]["prev_ac_out"]
            prev_x = data[0] # Simplificación para el primer punto del bloque
            
            for i in range(len(data)):
                out[i] = data[i] - prev_x + alpha * prev_y
                prev_x = data[i]
                prev_y = out[i]
            
            self.channels[ch]["prev_ac_out"] = prev_y
            return out

        return data # Modo DC (Pasa todo)

    def step(self):
        """
        Calcula el frame de datos para graficar.
        """
        if self.mode == "SPECTRUM":
            return self.get_spectrum_frame()
        return self.get_time_frame()

    # -----------------------------
    # TIME
    # -----------------------------
    def get_time_frame(self):
        # 1. Usar el time_div dinámico (el osciloscopio suele mostrar 10 divisiones)
        span = self.time_div * 10 
        n = int(span * self.fs)

        # 2. Calcular el desplazamiento en muestras (offset de tiempo)
        # Convertimos segundos de desplazamiento a número de muestras
        offset_samples = int(self.time_position * self.fs)

        # 3. Ajustar los índices usando el desplazamiento
        # Restamos offset_samples para "ir al pasado"
        end_idx = self.write_idx - offset_samples
        idxs = (end_idx - n + np.arange(n)) % self.buffer_size

        # Tiempo para el eje X (de 0 a span)
        t = np.arange(n) / self.fs

        signals, colors, volts, offsets, names = [], [], [], [], []

        for ch, cfg in self.channels.items():
            if cfg["enabled"]:
                signals.append(self.buffers[ch][idxs])
                colors.append(cfg["color"])
                volts.append(cfg["vdiv"])
                offsets.append(cfg["offset"])
                names.append(ch)

        return {
            "mode": "TIME",
            "t": t,
            "signals": signals,
            "colors": colors,
            "volts": volts,
            "offsets": offsets,
            "names": names,
            "time_div": self.time_div, # Pasar el valor real a la función de plot
        }

    # -----------------------------
    # FFT antigua (congelada)
    # -----------------------------
    def get_fft_frame(self):
        sig = self.fft_buffer.copy()
        sig -= np.mean(sig)

        window = np.hanning(len(sig))
        sig_w = sig * window

        fft = np.fft.rfft(sig_w)
        freqs = np.fft.rfftfreq(len(sig), 1 / self.fs)

        mag = np.abs(fft) / (np.sum(window) / 2)
        mag[mag < 1e-15] = 1e-15
        mag_db = 20 * np.log10(mag)

        return {
            "mode": "FFT",
            "freqs": freqs,
            "mag_db": mag_db,
            "channel": self.fft_channel,
            "color": self.channels[self.fft_channel]["color"],
            "fs": self.fs,
            "df": self.fs / len(sig),
        }

    # -----------------------------
    # Spectrum Analyzer
    # -----------------------------
    def _fft_size_from_rbw(self):
        return int(self.fs / self.spec_rbw)

    def get_spectrum_frame(self):
        sig = self.buffers[self.spec_channel].copy()
        sig -= np.mean(sig)

        N = self._fft_size_from_rbw()
        sig = sig[-N:]

        window = np.hanning(N)
        sig_w = sig * window

        fft = np.fft.rfft(sig_w)
        freqs = np.fft.rfftfreq(N, 1 / self.fs)

        # ---- ESCALADO RMS REAL CORRECTO ----

        # Normalización por número de puntos
        fft = fft / N

        # Corrección de ventana Hann (ganancia coherente = 0.5)
        fft = fft / 0.5

        # Magnitud
        mag = np.abs(fft)

        # Espectro unilateral → conservar potencia
        if len(mag) > 2:
            mag[1:-1] *= np.sqrt(2)

        # Esto YA ES Vrms
        mag[mag < 1e-15] = 1e-15
        mag_db = 20 * np.log10(mag)

        # Promedio exponencial
        if self.spec_psd_avg is None:
            self.spec_psd_avg = mag_db
        else:
            self.spec_psd_avg = (
                self.spec_alpha * mag_db
                + (1 - self.spec_alpha) * self.spec_psd_avg
            )

        # Max Hold
        if self.spec_max_hold:
            if self.spec_max is None:
                self.spec_max = self.spec_psd_avg.copy()
            else:
                self.spec_max = np.maximum(self.spec_max, self.spec_psd_avg)

        return {
            "mode": "SPECTRUM",
            "freqs": freqs,
            "mag_db": self.spec_max if self.spec_max_hold else self.spec_psd_avg,
            "channel": self.spec_channel,
            "rbw": self.fs / N,
            "fs": self.fs,
            "color": self.channels[self.spec_channel]["color"],
        }

    # -----------------------------
    # STEP
    # -----------------------------
    def step(self):
        if self.mode == "SPECTRUM":
            return self.get_spectrum_frame()
        elif self.mode == "FFT":
            if not self.fft_frozen:
                self.fft_cache = self.get_fft_frame()
                self.fft_frozen = True
            return self.fft_cache
        else:
            return self.get_time_frame()

    # -----------------------------
    # Controles
    # -----------------------------
    def set_channels(self, ch1, ch2):
        self.mode = "TIME"
        self.channels["CH1"]["enabled"] = ch1
        self.channels["CH2"]["enabled"] = ch2
    
    def toggle_channel(self, ch):
        """
        Conmuta el estado ON/OFF de un canal.
        """
        self.channels[ch]["enabled"] = not self.channels[ch]["enabled"]

    def change_vdiv(self, ch, factor):
        self.channels[ch]["vdiv"] *= factor

    def change_offset(self, ch, delta):
        self.channels[ch]["offset"] += delta

    def change_time_div(self, factor):
        self.mode = "TIME"
        self.time_div *= factor
        self.time_position = 0.0

    def show_fft(self, ch):
        self.mode = "FFT"
        self.fft_channel = ch
        self.fft_buffer = self.buffers[ch].copy()
        self.fft_frozen = False
        self.fft_cache = None

    def show_spectrum(self, ch):
        # Si ya estamos en espectro de ESTE canal → volver a TIME
        if self.mode == "SPECTRUM" and self.spec_channel == ch:
            self.mode = "TIME"
            return

        # Si no, entrar (o cambiar) a espectro
        self.mode = "SPECTRUM"
        self.spec_channel = ch
        self.spec_psd_avg = None
        self.spec_max = None
