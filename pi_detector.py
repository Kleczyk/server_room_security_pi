# app.py

import time
import board
import adafruit_dht
import numpy as np
import streamlit as st
from threading import Thread, Event
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LinearRegression

# === 1. Moduł odczytu z czujnika ===
class AM2302Reader:
    def __init__(self, pin: int = 2):
        pin_attr = f"D{pin}"
        if not hasattr(board, pin_attr):
            raise ValueError(f"Pin BCM{pin} nie istnieje w module board")
        self.dht = adafruit_dht.DHT22(getattr(board, pin_attr), use_pulseio=False)

    def read(self):
        try:
            t = self.dht.temperature
            h = self.dht.humidity
            print(f"t: {t}, h: {h}")
        except RuntimeError:
            return None, None
        return t, h

# === 2. Progowanie i alarmy ===
class ThresholdAlarm:
    def __init__(self, temp_thresh: float = 30.0, hum_thresh: float = 60.0):
        self.temp_thresh = temp_thresh
        self.hum_thresh = hum_thresh

    def update(self, temp_thresh, hum_thresh):
        self.temp_thresh = temp_thresh
        self.hum_thresh = hum_thresh

    def check(self, t, h):
        msgs = []
        if t is not None and t > self.temp_thresh:
            msgs.append("🔥 ZA CIEPŁO!")
        if h is not None and h > self.hum_thresh:
            msgs.append("💧 ZA WILGOTNO!")
        return "  ".join(msgs) if msgs else "OK"

i = 0
# === 3. Stub predykcji ===
history = list()
class TempPredictor:


    def add(self, t):
        if t is not None:
            history.append(t)
            i =+ 1
            print(i)
            print(f"Historia: {len(history)}")
            print(f"Historia: {history}")

    def predict(self, horizon=60, window_size=60):
        """
        Przewiduje temperaturę na podstawie historii danych za pomocą regresji liniowej.

        Args:
            history (list): Lista wartości temperaturowych (np. [20.1, 20.5, ...]).
            horizon (int): Liczba kroków w przyszłość do przewidzenia (domyślnie 1).
            window_size (int): Liczba poprzednich wartości użytych jako cechy (domyślnie 10).

        Returns:
            float: Przewidywana wartość temperatury lub ostatnia wartość z historii, jeśli za mało danych.
        """
        # Sprawdzenie, czy jest wystarczająco dużo danych
        if len(history) < window_size + 1:
            return history[-1] if history else None
        print(f"Historia: {len((history))}")
        # Przygotowanie danych: cechy (okno) i cel (następna wartość)
        X, y = [], []
        for i in range(len(history) - window_size):
            X.append(history[i:i + window_size])
            y.append(history[i + window_size])
        X, y = np.array(X), np.array(y)

        # Trenowanie modelu
        model = LinearRegression()
        try:
            model.fit(X, y)
        except Exception:
            return history[-1] if history else None

        # Predykcja krok po kroku
        current_window = np.array(history[-window_size:]).reshape(1, -1)
        for _ in range(horizon):
            pred = model.predict(current_window)[0]
            current_window = np.roll(current_window, -1)
            current_window[0, -1] = pred

        return pred

# === 4. Inicjalizacja ===
reader    = AM2302Reader(pin=4)    # zmień na swój GPIO
alarm     = ThresholdAlarm()
predictor = TempPredictor()
stop_ev   = Event()



# === 5. Streamlit UI ===
st.set_page_config(page_title="Monitor serwerowni", layout="wide")
st.title("🌡️ Monitor temperatury i wilgotności")

with st.sidebar:
    st.header("⚙️ Ustawienia progów alarmu")
    temp_thresh = st.slider("Próg temperatury (°C)", -10.0, 100.0, 30.0, 0.1)
    hum_thresh  = st.slider("Próg wilgotności (%)", 0, 100, 60, 1)

alarm.update(temp_thresh, hum_thresh)
# automatyczne odświeżanie co 5 sekund
st_autorefresh(interval=1000, limit=None, key="timer")

# Pobierz i oblicz
t_cur, h_cur = reader.read()
predictor.add(t_cur)
t_pred = predictor.predict()
status = alarm.check(t_cur, h_cur)

# --- Wyświetlenie metryk ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Temperatura ↑", f"{t_cur:.1f} °C" if t_cur is not None else "—")
with col2:
    st.metric("Wilgotność ↑", f"{h_cur:.1f} %RH" if h_cur is not None else "—")
with col3:
    st.metric("Prognoza ↑ 10 min", f"{t_pred:.1f} °C" if t_pred is not None else "—")

# --- Status alarmu ---
if status != "OK":
    st.error(status)
else:
    st.success("OK")

st.markdown(
    """
    Autorzy: **Michał Kocik**, **Daniel Kleczyński**
    """
)
