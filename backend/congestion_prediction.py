import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(10, 1)),
    LSTM(50),
    Dense(1)
])

model.compile(optimizer="adam", loss="mse")

def predict_congestion(data):
    data = np.array(data).reshape(1, 10, 1)
    prediction = model.predict(data)
    return prediction[0][0]