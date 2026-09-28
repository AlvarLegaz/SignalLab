import numpy as np

class SignalGenerator:
    def __init__(self):
        self.channels = {
            "CH1": {"wave": "Senoidal", "amp": 5.0, "freq": 1000.0, "phase": 0.0, "offset": 0.0, "duty": 50.0, "enabled": True},
            "CH2": {"wave": "Senoidal", "amp": 2.0, "freq": 100.0, "phase": 0.0, "offset": 0.0, "duty": 50.0, "enabled": True},
            "CH3": {"mode": "MIXER", "type": "AM", "mu": 1.0, "kf": 5.0, "offset": 0.0, "enabled": False}
        }
        # Guardamos el tiempo acumulado total para mantener la coherencia
        self.total_time = 0.0
        self.phases_fm = 0.0 

        self.adc_enabled = False
        self.adc_fs = 10000
        self.adc_bits = 4
        self.adc_vref = 10.0

        # Estado del muestreo del ADC entre bloques: muestras procesadas,
        # índice de la última muestra ADC y valor retenido.
        self._adc_n = 0
        self._adc_k = -1
        self._adc_hold = 0.0


    def apply_adc(self, signal, t):
        if not self.adc_enabled:
            return signal

        fs_adc = self.adc_fs
        bits = self.adc_bits

        if fs_adc <= 0 or bits <= 0:
            return signal

        # -----------------------------
        # 1️⃣ MUESTREO (muestreo y retención, continuo entre bloques)
        # -----------------------------
        dt = t[1] - t[0]
        fs_signal = 1.0 / dt

        # Índice de la muestra ADC vigente en cada punto, contando desde el
        # arranque: así el ritmo es exacto (3000 Hz son 3000 Hz) y no se
        # reinicia al empezar cada bloque.
        n = np.arange(len(signal))
        k = np.floor((self._adc_n + n) * fs_adc / fs_signal)
        nueva = np.empty(len(signal), dtype=bool)
        nueva[0] = k[0] != self._adc_k
        nueva[1:] = k[1:] != k[:-1]

        # Cada punto toma el valor de la última muestra nueva; los primeros
        # puntos del bloque, si no hay muestra nueva, mantienen el valor retenido.
        ultima = np.maximum.accumulate(np.where(nueva, n, -1))
        sampled = np.where(ultima >= 0, signal[np.maximum(ultima, 0)], self._adc_hold)

        self._adc_n += len(signal)
        self._adc_k = k[-1]
        self._adc_hold = sampled[-1]

        # -----------------------------
        # 2️⃣ CUANTIFICACIÓN ADC CON VREF
        # -----------------------------
        bits = int(self.adc_bits)
        bits = max(1, min(bits, 24))

        vref = abs(self.adc_vref)
        levels = 2 ** bits

        # Saturación
        sampled = np.clip(sampled, -vref, vref)

        # Cuantificador tipo ADC real (mid-rise)
        q_step = (2 * vref) / levels

        # El código máximo es levels-1: con la entrada en +Vref la salida
        # no puede pasar de Vref.
        codigo = np.clip(np.floor((sampled + vref) / q_step), 0, levels - 1)
        quantized = codigo * q_step - vref + q_step/2
        return quantized
    
    
    def generate(self, ch, t):
        if len(t) < 2: return np.zeros_like(t)
        
        # CH3 (Mixer) no debe avanzar el tiempo global, solo leer los valores
        if ch == "CH3":
            c_raw = self._generate_base("CH1", t, is_mixer_call=True)
            m_raw = self._generate_base("CH2", t, is_mixer_call=True)
            
            cfg3 = self.channels["CH3"]
            c_ac = c_raw - self.channels["CH1"]["offset"]
            amp2 = self.channels["CH2"]["amp"]
            
            if cfg3["type"] == "SUM":
                res = c_raw + m_raw
            elif cfg3["type"] == "AM":
                m_ac_norm = (m_raw - self.channels["CH2"]["offset"]) / (amp2 if amp2 != 0 else 1.0)
                res = c_ac * (1.0 + cfg3["mu"] * m_ac_norm) + self.channels["CH1"]["offset"]
            elif cfg3["type"] == "FM":
                # Para FM simplificado usamos la fase del CH1 como base
                fc = self.channels["CH1"]["freq"]
                kf = cfg3["kf"] * 1000.0
                m_ac_norm = (m_raw - self.channels["CH2"]["offset"]) / (amp2 if amp2 != 0 else 1.0)
                dt = t[1] - t[0]
                inst_freq = fc + kf * m_ac_norm
                phase_inc = 2 * np.pi * inst_freq * dt
                # Usamos una fase interna propia para el modo FM
                block_phases = self.phases_fm + np.cumsum(phase_inc)
                self.phases_fm = block_phases[-1] % (2 * np.pi)
                res = self.channels["CH1"]["amp"] * np.sin(block_phases) + self.channels["CH1"]["offset"]
            else:
                # DBL: producto de las partes alternas (sin portadora)
                m_ac_norm = (m_raw - self.channels["CH2"]["offset"]) / (amp2 if amp2 != 0 else 1.0)
                res = c_ac * m_ac_norm + self.channels["CH1"]["offset"]

            adc_out = self.apply_adc(res + cfg3["offset"], t)

            # El tiempo global avanza una vez por ciclo, DESPUÉS del último canal
            # (CH3). Si avanzase antes, el mezclador calcularía el bloque
            # siguiente y CH3 saldría desfasado respecto a CH1 y CH2.
            self.total_time += len(t) * (t[1] - t[0])
            return adc_out

        return self._generate_base(ch, t, is_mixer_call=False)

    def _generate_base(self, ch_key, t, is_mixer_call=False):
        cfg = self.channels[ch_key]
        freq = cfg["freq"]
        
        # Convertimos fase de grados a radianes
        phase_offset = np.radians(cfg.get("phase", 0.0))
        
        # Calculamos el tiempo absoluto para cada muestra del bloque
        t_absolute = self.total_time + t
        
        # Ecuación fundamental: 2 * pi * f * t + fase
        phi = 2 * np.pi * freq * t_absolute - phase_offset

        kind = cfg["wave"]
        if kind == "Senoidal": 
            sig = cfg["amp"] * np.sin(phi)
        elif kind == "Cuadrada": 
            sig = cfg["amp"] * np.where((phi % (2*np.pi)) < (cfg["duty"]/100)*2*np.pi, 1.0, -1.0)
        elif kind == "Diente": 
            sig = cfg["amp"] * (2 * ((phi / (2*np.pi)) % 1) - 1)
        elif kind == "Triangular": 
            sig = cfg["amp"] * (2 * np.abs(2 * ((phi / (2*np.pi)) % 1) - 1) - 1)
        elif kind == "Gaussiana":
            # Normalizamos la fase phi para que vaya de 0 a 1 en cada ciclo
            phase_norm = (phi % (2 * np.pi)) / (2 * np.pi)
            
            # El Duty controla el ancho de la campana (sigma)
            duty_factor = (cfg["duty"] / 100.0) ** 2
            sigma = 0.005 + (duty_factor * 0.250)
            if sigma == 0: sigma = 0.001 
            
            # Ecuación de la campana de Gauss (Pulso para GFSK) centrada en 0.5
            sig = cfg["amp"] * np.exp(-0.5 * ((phase_norm - 0.5) / sigma)**2)
        else: 
            sig = np.zeros_like(t)
        
        return sig + cfg["offset"]