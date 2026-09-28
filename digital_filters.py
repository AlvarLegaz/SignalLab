import numpy as np
from scipy.signal import butter, sosfilt, sosfreqz


def design_filter(filter_type, fs, freq, order=1, bandwidth=None):
    """
    Diseña un filtro digital Butterworth en formato SOS.
    """

    nyq = fs / 2.0
    order = int(np.clip(order, 1, 15))

    if freq <= 0 or freq >= nyq:
        raise ValueError("Frecuencia fuera de rango")

    if filter_type == "Paso Bajo":
        wn = freq / nyq
        sos = butter(order, wn, btype="low", output="sos")

    elif filter_type == "Paso Alto":
        wn = freq / nyq
        sos = butter(order, wn, btype="high", output="sos")

    elif filter_type == "Pasa Banda":
        if bandwidth is None or bandwidth <= 0:
            raise ValueError("Ancho de banda inválido")

        f1 = max(freq - bandwidth / 2, 1.0)
        f2 = min(freq + bandwidth / 2, nyq * 0.99)
        wn = [f1 / nyq, f2 / nyq]
        sos = butter(order, wn, btype="band", output="sos")

    elif filter_type == "Rechaza Banda":
        if bandwidth is None or bandwidth <= 0:
            raise ValueError("Ancho de banda inválido")

        f1 = max(freq - bandwidth / 2, 1.0)
        f2 = min(freq + bandwidth / 2, nyq * 0.99)
        wn = [f1 / nyq, f2 / nyq]
        sos = butter(order, wn, btype="bandstop", output="sos")

    else:
        raise ValueError(f"Tipo de filtro desconocido: {filter_type}")

    return sos


def apply_filter(signal, fs, filter_type, freq, order=1, bandwidth=None):
    """
    Aplica un filtro Butterworth SOS a la señal.
    """

    if signal is None or len(signal) == 0:
        return signal

    try:
        sos = design_filter(
            filter_type=filter_type,
            fs=fs,
            freq=freq,
            order=order,
            bandwidth=bandwidth
        )
        return sosfilt(sos, signal)

    except Exception as e:
        print(f"[Filtro] Error: {e}")
        return signal

def filter_frequency_response(
    fs, filter_type, freq, order=1, bandwidth=None, n_points=2048
):
    """
    Respuesta en frecuencia del filtro (dB).
    """

    try:
        sos = design_filter(
            filter_type=filter_type,
            fs=fs,
            freq=freq,
            order=order,
            bandwidth=bandwidth
        )

        w, h = sosfreqz(sos, worN=n_points, fs=fs)
        mag = np.abs(h)
        mag[mag < 1e-12] = 1e-12
        mag_db = 20 * np.log10(mag)

        return w, mag_db

    except Exception as e:
        print(f"[Filtro] Error respuesta frecuencia: {e}")
        return None, None