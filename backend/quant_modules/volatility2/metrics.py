import numpy as np
import pandas as pd


def log_returns(prices):
    """
    Calcule les rendements logarithmiques
    """
    return np.log(prices / prices.shift(1)).dropna()


def historical_volatility(prices, trading_days=252):
    """
    Volatilité annualisée
    """
    returns = log_returns(prices)

    volatility = returns.std() * np.sqrt(trading_days)

    return float(volatility)


def rolling_volatility(prices, window=20):
    """
    Volatilité glissante
    """
    returns = log_returns(prices)

    return returns.rolling(window).std() * np.sqrt(252)