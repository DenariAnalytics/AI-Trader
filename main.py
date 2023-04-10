import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

import load_data

def split_data(data, train_fraction=0.8):
    data_array = np.array(data)
    split_index = int(len(data_array) * train_fraction)
    train_data = data_array[:split_index]
    test_data = data_array[split_index:]
    return train_data, test_data

def create_sequences(data, window_size=60):
    X, y = [], []
    for i in range(len(data) - window_size - 1):
        X.append(data[i:(i + window_size), :])
        y.append(data[i + window_size, 0])
    X = np.stack(X, axis=0)
    y = np.array(y)
    return X, y


def calculate_trading_signals(y_pred, y_true, buy_threshold=0.03, sell_threshold=-0.03):
    # Ensure y_pred and y_true are numpy arrays
    y_pred = np.array(y_pred)
    y_true = np.array(y_true)
    
    # Calculate price changes between predicted and true values
    price_changes = y_pred[1:] - y_true[:-1]

    # Generate trading signals
    signals = np.zeros(price_changes.shape)
    signals[price_changes > buy_threshold] = 1    # Buy signal
    signals[price_changes < sell_threshold] = -1  # Sell signal

    return signals

def backtest_strategy(signals, prices, initial_capital=1000, return_dataframe=False):
    # Calculate returns
    returns = np.zeros_like(prices)
    position = 0
    capital = initial_capital
    invested_amounts = []

    for i in range(1, len(signals)):
        if signals[i - 1] != 0:
            position = signals[i - 1]
            invested_amount = capital * position
            invested_amounts.append(invested_amount)
        returns[i] = (prices[i] - prices[i - 1]) * position
        capital += returns[i]

    # Calculate cumulative returns
    cumulative_returns = np.cumsum(returns)

    # Calculate win rate
    wins = np.sum(returns > 0)
    total_trades = np.sum(np.abs(signals) > 0)
    win_rate = wins / total_trades

    # Calculate drawdowns
    drawdowns = np.maximum.accumulate(cumulative_returns) - cumulative_returns
    max_drawdown = np.max(drawdowns)

    results = {
        'returns': returns,
        'cumulative_returns': cumulative_returns,
        'win_rate': win_rate,
        'drawdowns': drawdowns,
        'max_drawdown': max_drawdown
    }

    if return_dataframe:
        results_df = pd.DataFrame(results)
        return results_df

    return results


# Load and preprocess data
data = load_data.local_data('C:\\Users\\tempf\\Desktop\\AI-Trader\\data\\BTC-USDT_binance.csv')


# Create train/test split
train_data, test_data = split_data(data)

# Scale data
scaler = MinMaxScaler()
train_data_scaled = train_data.copy()
test_data_scaled = test_data.copy()
train_data_scaled[:, 0] = scaler.fit_transform(train_data[:, 0].reshape(-1, 1)).flatten()
test_data_scaled[:, 0] = scaler.transform(test_data[:, 0].reshape(-1, 1)).flatten()

# Create sequences for training and testing
X_train, y_train = create_sequences(train_data_scaled)
X_test, y_test = create_sequences(test_data_scaled)

# Create LSTM model
model = tf.keras.Sequential([
    tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.LSTM(50, return_sequences=False),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(1)
])

# Compile and train the model
model.compile(optimizer='adam', loss='mse')
model.fit(X_train, y_train, epochs=750, batch_size=32, shuffle=False)
model.save('btc/usdt_tading_model.h5')

# Evaluate the model
y_pred = model.predict(X_test)
y_pred_inverse = scaler.inverse_transform(np.hstack([y_pred, np.zeros((y_pred.shape[0], train_data.shape[1]-1))]))[:, 0]
y_test_inverse = scaler.inverse_transform(np.hstack([y_test.reshape(-1, 1), np.zeros((y_test.shape[0], train_data.shape[1]-1))]))[:, 0]

# Calculate trading signals and backtest
trading_signals = calculate_trading_signals(y_pred_inverse, y_test_inverse)
backtest_results = backtest_strategy(trading_signals, y_test_inverse, initial_capital=1000, return_dataframe=True)
print(backtest_results)