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

# === 3. Stub predykcji ===
class TempPredictor:
    def __init__(self, history=None):
        self.history = history if history is not None else []

    def add(self, t):
        if t is not None:
            self.history.append(t)
            if len(self.history) > 1000:
                self.history.pop(0)

    def predict(self, horizon=60, window_size=100):
        if len(self.history) < window_size + 1:
            return self.history[-1] if self.history else None
        print(f"Historia: {len(self.history)}")
        X, y = [], []
        for i in range(len(self.history) - window_size):
            X.append(self.history[i:i + window_size])
            y.append(self.history[i + window_size])
        X, y = np.array(X), np.array(y)

        model = LinearRegression()
        try:
            model.fit(X, y)
        except Exception:
            return self.history[-1] if self.history else None

        current_window = np.array(self.history[-window_size:]).reshape(1, -1)
        for _ in range(horizon):
            pred = model.predict(current_window)[0]
            current_window = np.roll(current_window, -1)
            current_window[0, -1] = pred

        return pred

# === 4. Inicjalizacja ===
# Inicjalizacja sesji stanu dla historii
if 'history' not in st.session_state:
    st.session_state.history = []

# Inicjalizacja obiektów
reader = AM2302Reader(pin=4)  # zmień na swój GPIO
alarm = ThresholdAlarm()
predictor = TempPredictor(history=st.session_state.history)
stop_ev = Event()

# === 5. Streamlit UI ===
st.set_page_config(page_title="Monitor serwerowni", layout="wide")
st.title("🌡️ Monitor temperatury i wilgotności")

with st.sidebar:
    st.header("⚙️ Ustawienia progów alarmu")
    temp_thresh = st.slider("Próg temperatury (°C)", -10.0, 100.0, 30.0, 0.1)
    hum_thresh = st.slider("Próg wilgotności (%)", 0, 100, 60, 1)

alarm.update(temp_thresh, hum_thresh)

# Automatyczne odświeżanie co 1 sekundę
st_autorefresh(interval=1000, limit=None, key="timer")

# Pobierz i oblicz
t_cur, h_cur = reader.read()
predictor.add(t_cur)
# Aktualizacja historii w session_state
st.session_state.history = predictor.history
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