import time
from threading import Thread, Event

import Adafruit_DHT
import gradio as gr
import numpy as np

# === 1. Moduł odczytu z czujnika ===
class AM2302Reader:
    def __init__(self, pin: int = 8, sensor=Adafruit_DHT.AM2302):
        self.pin = pin
        self.sensor = sensor

    def read(self):
        """Zwraca (temp_C: float lub None, humidity_%: float lub None)"""
        humidity, temp = Adafruit_DHT.read_retry(self.sensor, self.pin)
        return temp, humidity

# === 2. Moduł progowania i alarmów ===
class ThresholdAlarm:
    def __init__(self, temp_thresh: float = 30.0, hum_thresh: float = 60.0):
        self.temp_thresh = temp_thresh
        self.hum_thresh = hum_thresh

    def update_thresholds(self, temp_thresh: float, hum_thresh: float):
        self.temp_thresh = temp_thresh
        self.hum_thresh = hum_thresh

    def check(self, temp: float, hum: float):
        msg = []
        if temp is not None and temp > self.temp_thresh:
            msg.append("🔥 ZA CIEPŁO!")
        if hum is not None and hum > self.hum_thresh:
            msg.append("💧 ZA WILGOTNO!")
        return "  ".join(msg) if msg else "OK"

# === 3. Stub predykcji przyszłej temperatury ===
class TempPredictor:
    def __init__(self):
        self.history = []

    def add_sample(self, temp: float):
        if temp is not None:
            self.history.append(temp)
            # ogranicz historię, żeby nie rosła w nieskończoność
            if len(self.history) > 1000:
                self.history.pop(0)

    def predict(self, horizon: int = 5) -> float:
        """
        Prognozuje temperaturę za 'horizon' minut.
        Tu prosty stub: średnia z ostatnich 3 pomiarów + niewielki trend.
        Rozbuduj o dowolny model ML czy ARIMA.
        """
        if len(self.history) < 3:
            return self.history[-1] if self.history else None
        last3 = self.history[-3:]
        trend = (last3[-1] - last3[0]) / len(last3)
        return last3[-1] + trend * horizon

# === 4. Aplikacja Gradio ===
reader = AM2302Reader(pin=4)
alarm = ThresholdAlarm()
predictor = TempPredictor()

stop_event = Event()

def background_loop():
    while not stop_event.is_set():
        t, h = reader.read()
        predictor.add_sample(t)
        time.sleep(5)  # co 5s nowy pomiar

# start wątek odczytu
Thread(target=background_loop, daemon=True).start()

def gradio_update(temp_thresh, hum_thresh):
    # odczyt
    temp, hum = reader.read()
    # zaktualizuj progi
    alarm.update_thresholds(temp_thresh, hum_thresh)
    # sprawdź alarmy
    status = alarm.check(temp, hum)
    # prognoza
    pred = predictor.predict(horizon=10)
    # formatowanie tekstu
    temp_txt = f"{temp:.1f} °C" if temp is not None else "—"
    hum_txt  = f"{hum:.1f}% RH"    if hum  is not None else "—"
    pred_txt = f"{pred:.1f} °C" if pred is not None else "—"
    return temp_txt, hum_txt, pred_txt, status

with gr.Blocks(title="Monitor serwerowni (Raspberry Pi + DHT22)") as demo:
    gr.Markdown("## 🌡️ Monitor temperatury i wilgotności")
    with gr.Row():
        temp_disp  = gr.Textbox(label="Temperatura (aktualna)")
        hum_disp   = gr.Textbox(label="Wilgotność (aktualna)")
        pred_disp  = gr.Textbox(label="Prognoza za 10 min")
    alarm_disp = gr.Markdown("**Status:** OK", elem_id="alarm_status")

    with gr.Accordion("Ustaw progi alarmowe", open=False):
        temp_slider = gr.Slider( minimum=0, maximum=50, step=0.5,
                                 label="Próg temperatury (°C)", value=30 )
        hum_slider  = gr.Slider( minimum=0, maximum=100, step=1,
                                 label="Próg wilgotności (%)",  value=60 )

    # co 5s odświeżaj
    demo.load(fn=gradio_update,
              inputs=[temp_slider, hum_slider],
              outputs=[temp_disp, hum_disp, pred_disp, alarm_disp],
              every=5)

    gr.Markdown("> ⚙️ Ten interfejs możesz łatwo rozbudować o wykres historii, zaawansowany model predykcji czy powiadomienia e-mail/SMS.")

demo.launch(server_name="0.0.0.0", server_port=7860)
