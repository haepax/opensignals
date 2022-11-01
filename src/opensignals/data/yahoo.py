import random

import datetime as dt
import time as _time
from typing import Tuple, Dict, Union

import numpy as np
import pandas as pd
import requests
from opensignals.data.provider import Provider
from opensignals import utils


class Yahoo(Provider):
    """Implementation of a stock data price provider that uses the Yahoo! Finance API"""

    def download_ticker(self, ticker: str, start: dt.datetime, end: dt.datetime) -> Tuple[str, pd.DataFrame]:
        """download data for a given ticker"""

        def empty_df() -> pd.DataFrame:
            return pd.DataFrame(columns=[
                "date", "bloomberg_ticker",
                "open", "high", "low", "close",
                "adj_close", "volume", "currency", "provider"])

        retries = 20
        tries = retries + 1
        backoff = 1
        url = f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
        user_agent = random.choice(utils.USER_AGENTS)
        params: Dict[str, Union[int, str]] = dict(
            period1=int(start.timestamp()),
            period2=int(end.timestamp()),
            interval='1d',
            events='div,splits',
        )
        while tries > 0:
            data_json = {}
            tries -= 1
            try:
                data = requests.get(
                    url=url,
                    params=params,
                    headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                        "accept-encoding": "gzip, deflate, br",
                        "accept-language": "en-US,en;q=0.9",
                        'user-agent': user_agent}
                )
                data_json = data.json()
                quotes = data_json["chart"]["result"][0]
                if "timestamp" not in quotes:
                    return ticker, empty_df()

                timestamps = quotes["timestamp"]
                ohlc = quotes["indicators"]["quote"][0]
                volumes = ohlc["volume"]
                opens = ohlc["open"]
                closes = ohlc["close"]
                lows = ohlc["low"]
                highs = ohlc["high"]

                adjclose = closes
                if "adjclose" in quotes["indicators"]:
                    adjclose = quotes["indicators"]["adjclose"][0]["adjclose"]

                df = pd.DataFrame({
                    "date": pd.to_datetime(timestamps, unit="s").normalize(),
                    "bloomberg_ticker": ticker,
                    "open": np.array(opens, dtype='float32'),
                    "high": np.array(highs, dtype='float32'),
                    "low": np.array(lows, dtype='float32'),
                    "close": np.array(closes, dtype='float32'),
                    "adj_close": np.array(adjclose, dtype='float32'),
                    "volume": np.array(volumes, dtype='float32'),
                    "currency": quotes['meta']['currency'],
                    "provider": 'yahoo'
                })

                return ticker, df.drop_duplicates().dropna()

            except Exception:
                if 'error' in data_json.get('chart', "") and data_json['chart']['error']['description'] == "No data found, symbol may be delisted":
                    break
                else:
                    _time.sleep(backoff)
                    backoff = min(backoff * 2, 30)

        return ticker, empty_df()
