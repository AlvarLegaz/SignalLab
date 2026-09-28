# SignalLab

Generador y analizador de señales virtual: un generador de funciones, un modulador, un conversor A/D, filtros digitales y un osciloscopio con analizador de espectro, todo simulado en una sola ventana.

## Uso

```bash
pip install -r requirements.txt
python main.py
```

## Qué hace

La señal recorre esta cadena cada 50 ms:

```text
CH1, CH2 (generador) ──► CH3 (mezclador) ──► ADC (opcional) ──► filtro (opcional) ──► osciloscopio / espectro
```

- **Generador (CH1, CH2)**: senoidal, cuadrada, diente de sierra, triangular y gaussiana, con amplitud, frecuencia, fase, duty y offset.
- **Mezclador / modulador (CH3)**: CH1 es la portadora y CH2 la moduladora. Modos SUM, AM (índice μ), DBL y FM (desviación kf × 1000 Hz).
- **Conversor A/D (CH3)**: muestreo y retención a la frecuencia elegida, saturación en ±Vref y cuantificación de 1 a 24 bits.
- **Filtros digitales (CH3)**: Butterworth paso bajo, paso alto, pasa banda y rechaza banda, de orden 1 a 15.
- **Osciloscopio**: 200 kS/s, búfer de 1 s, retícula de 10 × 8 divisiones, V/div y offset por canal, Time/div, desplazamiento en el tiempo y acoplamiento DC/AC/GND (el AC corta a 10 Hz, como un osciloscopio real).
- **Analizador de espectro**: FFT con ventana de Hann, nivel en dBV RMS, promediado y vista de ±5 kHz alrededor del pico. En CH3 puede superponer la respuesta del filtro.
- **Captura** de la pantalla en PNG.

## Estructura

| Fichero | Contenido |
| --- | --- |
| `main.py` | Interfaz (Tkinter + matplotlib) y bucle principal |
| `signal_generator.py` | Generador, mezclador y ADC |
| `digital_filters.py` | Diseño y aplicación de los filtros Butterworth |
| `oscilloscope.py` | Búfer de adquisición, acoplamiento y espectro |
| `scope_plot.py` | Dibujo de la pantalla del osciloscopio |
| `signal_utils.py`, `gui_utils.py` | Lectura segura de campos y rutas de recursos |
| `assets/` | Logo e icono |
| `SignalLab_Diagrama_Bloques.docx` | Diagrama de bloques de la aplicación |

## Generar el ejecutable (Windows)

```bat
build_signallab.bat
```

Instala PyInstaller si no está y genera `dist\SignalLab.exe` con el icono. `build/`, `dist/` y `SignalLab.spec` se regeneran en cada compilación y no se guardan en el repositorio.
