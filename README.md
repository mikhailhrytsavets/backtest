# ТЗ для Сodex: Systematic Options Strategy Backtest Engine

## Обзор проекта

Создать полноценный движок для бэктестирования систематической опционной стратегии на основе подхода из Reddit AMA (4-компонентная стратегия: Intraday Short Gamma, Intraday Delta, Positional Short Gamma, Positional Delta). 

**Целевой рынок**: Bybit криптовалютные опционы (BTC, ETH)
**Период**: с момента доступности исторических данных
**Язык**: Python 3.14+
**Архитектура**: Модульная система с возможностью независимого тестирования каждого компонента

***

## 1. АРХИТЕКТУРА ПРОЕКТА

```
bybit_options_backtest/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Глобальные настройки (API keys, пути)
│   └── strategy_params.yaml     # Параметры стратегии
├── data/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── options_collector.py      # Сбор опционных данных
│   │   ├── futures_collector.py      # Сбор фьючерсных данных (для спота)
│   │   ├── volatility_collector.py   # Сбор исторической волатильности
│   │   └── greeks_calculator.py      # Расчёт греков через Black-Scholes
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py               # SQLite/PostgreSQL для хранения
│   │   └── cache.py                  # Кэширование для быстрого доступа
│   └── preprocessor.py               # Очистка и подготовка данных
├── strategy/
│   ├── __init__.py
│   ├── base_strategy.py              # Базовый класс для всех стратегий
│   ├── components/
│   │   ├── __init__.py
│   │   ├── intraday_short_gamma.py   # Компонент 1
│   │   ├── intraday_delta.py         # Компонент 2
│   │   ├── positional_short_gamma.py # Компонент 3
│   │   └── positional_delta.py       # Компонент 4
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── volatility_signals.py     # Сигналы на основе IV
│   │   ├── delta_signals.py          # Дельта-сигналы
│   │   └── gamma_signals.py          # Гамма-сигналы
│   └── portfolio_manager.py          # Управление портфелем (4 компонента)
├── backtest/
│   ├── __init__.py
│   ├── engine.py                     # Основной движок бэктеста
│   ├── position.py                   # Класс для позиций
│   ├── execution.py                  # Моделирование исполнения с slippage
│   ├── risk_manager.py               # VaR, лимиты, маржинальные требования
│   └── performance.py                # Метрики (Sharpe, drawdown, ROI)
├── analysis/
│   ├── __init__.py
│   ├── visualizer.py                 # Графики результатов
│   ├── reports.py                    # Генерация отчётов
│   └── optimizer.py                  # Оптимизация параметров
├── tests/
│   ├── __init__.py
│   ├── test_data_collection.py
│   ├── test_greeks.py
│   ├── test_strategies.py
│   └── test_backtest_engine.py
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_strategy_development.ipynb
│   └── 03_backtest_analysis.ipynb
├── main.py                           # Точка входа
├── requirements.txt
└── README.md
```

***

## 2. МОДУЛЬ СБОРА ДАННЫХ

### 2.1 Options Collector (`data/collectors/options_collector.py`)

**Задачи**:
- Подключение к Bybit API v5 для получения опционных данных
- Сбор полной цепочки опционов (all strikes) для BTC и ETH
- Сохранение данных с минутной детализацией (или максимально доступной)

**Требуемые данные через API**:[1][2]

```python
class OptionsCollector:
    """
    Сборщик опционных данных с Bybit
    """
    
    async def fetch_instruments_info(self, base_coin: str) -> pd.DataFrame:
        """
        GET /v5/market/instruments-info?category=option&baseCoin=BTC
        
        Возвращает:
        - symbol (например, BTC-6NOV25-90000-C)
        - strike_price
        - expiry_date
        - option_type (Call/Put)
        - status (Trading/Settled)
        """
        pass
    
    async def fetch_option_klines(self, symbol: str, interval: str, 
                                   start_time: int, end_time: int) -> pd.DataFrame:
        """
        GET /v5/market/kline?category=option&symbol={symbol}&interval={interval}
        
        Возвращает OHLC данные по опциону:
        - timestamp
        - open, high, low, close
        - volume
        - turnover
        """
        pass
    
    async def fetch_option_tickers(self, symbol: str) -> Dict:
        """
        GET /v5/market/tickers?category=option&symbol={symbol}
        
        Возвращает текущие цены:
        - bid1_price, bid1_iv
        - ask1_price, ask1_iv
        - mark_price, mark_iv
        - underlying_price
        - delta, gamma, vega, theta (если доступны от биржи)
        """
        pass
    
    async def fetch_historical_volatility(self, base_coin: str, period: int,
                                          start_time: int, end_time: int) -> pd.DataFrame:
        """
        GET /v5/market/historical-volatility?baseCoin={base_coin}&period={period}
        
        Возвращает историческую волатильность (почасово):
        - timestamp
        - period (7, 14, 21, 30, 60, 90, 180, 270 days)
        - volatility
        """
        pass
```

**Стратегия сбора данных**:
1. Сначала получить список всех доступных инструментов
2. Для каждого инструмента собрать kline данные (интервалы: 1m, 5m, 15m, 1h)
3. Сохранять данные инкрементально (не перекачивать то, что уже есть)
4. Обрабатывать rate limits (120 запросов/сек для Bybit)

### 2.2 Futures Collector (`data/collectors/futures_collector.py`)

**Задачи**:
- Получение цен базового актива (BTC-USDT, ETH-USDT perpetual futures)
- Синхронизация таймстемпов с опционными данными

```python
class FuturesCollector:
    """
    Сборщик данных по фьючерсам (базовый актив для опционов)
    """
    
    async def fetch_futures_klines(self, symbol: str, interval: str,
                                    start_time: int, end_time: int) -> pd.DataFrame:
        """
        GET /v5/market/kline?category=linear&symbol=BTCUSDT
        
        Возвращает:
        - timestamp
        - open, high, low, close
        - volume
        """
        pass
    
    async def fetch_funding_rate(self, symbol: str, start_time: int, 
                                  end_time: int) -> pd.DataFrame:
        """
        GET /v5/market/funding/history?category=linear&symbol=BTCUSDT
        
        Возвращает funding rate (используется для корректировки стратегии)
        """
        pass
```

### 2.3 Greeks Calculator (`data/collectors/greeks_calculator.py`)

**Задачи**:
- Расчёт греков через Black-Scholes модель
- Использовать для периодов, где биржа не предоставляет греки

```python
class GreeksCalculator:
    """
    Расчёт опционных греков через Black-Scholes
    """
    
    @staticmethod
    def calculate_greeks(S: float, K: float, T: float, r: float, 
                         sigma: float, option_type: str) -> Dict[str, float]:
        """
        Параметры:
        S - текущая цена базового актива (spot)
        K - strike price
        T - время до экспирации (в годах)
        r - безрисковая ставка (используем funding rate или 0)
        sigma - implied volatility
        option_type - 'Call' или 'Put'
        
        Возвращает:
        - delta: чувствительность к изменению цены актива
        - gamma: скорость изменения дельты
        - vega: чувствительность к волатильности
        - theta: временной распад (в день)
        - rho: чувствительность к процентной ставке
        """
        # Реализовать формулы Black-Scholes для каждого грека
        # Использовать scipy.stats.norm для нормального распределения
        pass
    
    def calculate_implied_volatility(self, market_price: float, S: float, 
                                     K: float, T: float, r: float,
                                     option_type: str) -> float:
        """
        Обратная задача: найти IV из рыночной цены опциона
        Использовать метод Ньютона-Рафсона или scipy.optimize
        """
        pass
```

**Референс для формул**:[3][4]
- Delta: N(d1) для Call, N(d1) - 1 для Put
- Gamma: N'(d1) / (S * σ * sqrt(T))
- Vega: S * N'(d1) * sqrt(T)
- Theta: сложная формула, учитывающая временной распад и процентную ставку
- Где d1 = (ln(S/K) + (r + σ²/2)T) / (σ * sqrt(T))

### 2.4 Database Storage (`data/storage/database.py`)

**Задачи**:
- Эффективное хранение временных рядов
- Быстрый доступ для бэктеста

```python
class OptionsDatabase:
    """
    Хранилище опционных данных (SQLite для старта, PostgreSQL для production)
    """
    
    def __init__(self, db_path: str):
        """Инициализация подключения к БД"""
        pass
    
    def create_tables(self):
        """
        Создать таблицы:
        
        - options_instruments (symbol, strike, expiry, type, base_coin)
        - options_klines (timestamp, symbol, open, high, low, close, volume, bid, ask, mark_iv)
        - futures_klines (timestamp, symbol, open, high, low, close, volume)
        - calculated_greeks (timestamp, symbol, delta, gamma, vega, theta, rho)
        - historical_volatility (timestamp, base_coin, period, volatility)
        """
        pass
    
    def insert_klines_batch(self, df: pd.DataFrame, table_name: str):
        """Batch insert для эффективности"""
        pass
    
    def get_options_chain(self, timestamp: datetime, base_coin: str, 
                          expiry_date: datetime) -> pd.DataFrame:
        """
        Получить полную цепочку опционов на определённый момент времени
        Критично для бэктеста: нужна полная картина всех страйков
        """
        pass
    
    def get_option_data(self, symbol: str, start_time: datetime, 
                        end_time: datetime, interval: str = '1m') -> pd.DataFrame:
        """Получить исторические данные по конкретному опциону"""
        pass
```

***

## 3. МОДУЛЬ СТРАТЕГИИ

### 3.1 Base Strategy (`strategy/base_strategy.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Dict
import pandas as pd

class BaseStrategy(ABC):
    """
    Базовый класс для всех компонентов стратегии
    """
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.positions = []
        self.signals_history = []
    
    @abstractmethod
    def generate_signals(self, market_data: pd.DataFrame, 
                        options_chain: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Генерация торговых сигналов на основе данных
        
        Возвращает список сигналов:
        [{
            'action': 'open' | 'close' | 'adjust',
            'symbol': 'BTC-6NOV25-90000-C',
            'quantity': 10,
            'side': 'buy' | 'sell',
            'reason': 'short_gamma_opportunity',
            'target_delta': 0.5,  # целевая дельта позиции
            'stop_loss': 100,
            'take_profit': 50
        }]
        """
        pass
    
    @abstractmethod
    def manage_positions(self, current_positions: List, 
                        market_data: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Управление существующими позициями (хеджирование, закрытие)
        """
        pass
    
    def calculate_portfolio_greeks(self, positions: List, 
                                   options_chain: pd.DataFrame) -> Dict:
        """
        Суммарные греки портфеля (для risk management)
        """
        pass
```

### 3.2 Intraday Short Gamma (`strategy/components/intraday_short_gamma.py`)

```python
class IntradayShortGamma(BaseStrategy):
    """
    Компонент 1: Внутридневная продажа гаммы
    
    Логика:
    - Продаём опционы ATM/NTM в начале сессии
    - Целевая экспирация: 0DTE или 1-3 DTE
    - Хеджируем дельту через фьючерсы при достижении порогов
    - Закрываем все позиции до конца дня (или за N часов до экспирации)
    
    Сигналы входа:
    - Низкая реализованная волатильность за последние N часов
    - IV > HV (implied выше исторической)
    - Греки: gamma < -0.05, theta > 0.1
    
    Управление позицией:
    - Хеджирование дельты при |delta| > 0.2
    - Stop loss при потере > 2% от капитала компонента
    - Take profit при достижении 50% от max theta decay
    """
    
    def __init__(self, config: Dict):
        super().__init__("Intraday Short Gamma", config)
        self.entry_time = config.get('entry_time', '09:00')  # время входа
        self.exit_time = config.get('exit_time', '15:00')    # время выхода
        self.max_dte = config.get('max_dte', 3)
        self.delta_hedge_threshold = config.get('delta_hedge_threshold', 0.2)
    
    def generate_signals(self, market_data: pd.DataFrame, 
                        options_chain: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Генерация сигналов для входа в short gamma позицию
        """
        signals = []
        
        # 1. Проверка времени (только в определённые часы)
        if not self._is_entry_time(timestamp):
            return signals
        
        # 2. Фильтрация опционов по DTE
        eligible_options = self._filter_by_dte(options_chain, max_dte=self.max_dte)
        
        # 3. Расчёт IV vs HV
        iv_hv_spread = self._calculate_iv_hv_spread(eligible_options, market_data)
        
        # 4. Выбор оптимальных страйков (ATM/NTM с высокой IV)
        if iv_hv_spread > self.config['iv_hv_threshold']:
            optimal_strikes = self._select_strikes(eligible_options, strategy='short_gamma')
            
            for strike in optimal_strikes:
                signals.append({
                    'action': 'open',
                    'symbol': strike['symbol'],
                    'quantity': self._calculate_position_size(strike),
                    'side': 'sell',
                    'reason': f'short_gamma_iv_premium_{iv_hv_spread:.2f}',
                    'entry_price': strike['mark_price'],
                    'greeks': strike['greeks']
                })
        
        return signals
    
    def manage_positions(self, current_positions: List, 
                        market_data: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Управление позициями: хеджирование дельты, закрытие
        """
        actions = []
        
        # 1. Расчёт портфельных греков
        portfolio_greeks = self.calculate_portfolio_greeks(current_positions, market_data)
        
        # 2. Хеджирование дельты через фьючерсы
        if abs(portfolio_greeks['delta']) > self.delta_hedge_threshold:
            hedge_action = self._generate_delta_hedge(portfolio_greeks['delta'], market_data)
            actions.append(hedge_action)
        
        # 3. Проверка времени выхода (закрыть все позиции)
        if self._is_exit_time(timestamp):
            for pos in current_positions:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': 'end_of_day_exit'
                })
        
        # 4. Stop loss / Take profit
        for pos in current_positions:
            pnl_pct = self._calculate_position_pnl(pos, market_data)
            
            if pnl_pct < -self.config['stop_loss_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'stop_loss_{pnl_pct:.2f}%'
                })
            elif pnl_pct > self.config['take_profit_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'take_profit_{pnl_pct:.2f}%'
                })
        
        return actions
    
    def _filter_by_dte(self, options_chain: pd.DataFrame, max_dte: int) -> pd.DataFrame:
        """Фильтр по days to expiration"""
        pass
    
    def _calculate_iv_hv_spread(self, options: pd.DataFrame, 
                                market_data: pd.DataFrame) -> float:
        """Разница между IV и HV"""
        pass
    
    def _select_strikes(self, options: pd.DataFrame, strategy: str) -> List[Dict]:
        """Выбор оптимальных страйков для стратегии"""
        pass
    
    def _generate_delta_hedge(self, portfolio_delta: float, 
                              market_data: pd.DataFrame) -> Dict:
        """Генерация хеджа через фьючерсы"""
        pass
```

### 3.3 Intraday Delta (`strategy/components/intraday_delta.py`)

```python
class IntradayDelta(BaseStrategy):
    """
    Компонент 2: Внутридневные дельта-сигналы
    
    Логика:
    - Использование краткосрочных направленных движений
    - Покупка/продажа опционов на основе momentum/reversal сигналов
    - Быстрые входы и выходы (holding period 15 минут - 2 часа)
    
    Сигналы:
    - RSI экстремумы (< 30 или > 70)
    - Volume spikes + price breakouts
    - Funding rate аномалии (если фьючерсы overheated)
    """
    
    def __init__(self, config: Dict):
        super().__init__("Intraday Delta", config)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.holding_period_min = config.get('holding_period_min', 15)  # минуты
        self.holding_period_max = config.get('holding_period_max', 120)
    
    def generate_signals(self, market_data: pd.DataFrame, 
                        options_chain: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Генерация дельта-сигналов на основе momentum индикаторов
        """
        signals = []
        
        # 1. Расчёт технических индикаторов
        rsi = self._calculate_rsi(market_data, period=self.rsi_period)
        volume_spike = self._detect_volume_spike(market_data)
        price_breakout = self._detect_breakout(market_data)
        
        # 2. Сигнал на покупку (bullish)
        if rsi < self.rsi_oversold and (volume_spike or price_breakout == 'bullish'):
            # Покупаем OTM call или ATM call
            call_options = self._filter_calls(options_chain, moneyness='ATM')
            best_call = self._select_best_delta_option(call_options, direction='bullish')
            
            signals.append({
                'action': 'open',
                'symbol': best_call['symbol'],
                'quantity': self._calculate_position_size(best_call),
                'side': 'buy',
                'direction': 'bullish',
                'reason': f'rsi_oversold_{rsi:.1f}_volume_spike',
                'entry_time': timestamp,
                'expected_exit_time': timestamp + timedelta(minutes=self.holding_period_max)
            })
        
        # 3. Сигнал на продажу (bearish)
        elif rsi > self.rsi_overbought and (volume_spike or price_breakout == 'bearish'):
            # Покупаем OTM put или ATM put
            put_options = self._filter_puts(options_chain, moneyness='ATM')
            best_put = self._select_best_delta_option(put_options, direction='bearish')
            
            signals.append({
                'action': 'open',
                'symbol': best_put['symbol'],
                'quantity': self._calculate_position_size(best_put),
                'side': 'buy',
                'direction': 'bearish',
                'reason': f'rsi_overbought_{rsi:.1f}_volume_spike',
                'entry_time': timestamp,
                'expected_exit_time': timestamp + timedelta(minutes=self.holding_period_max)
            })
        
        return signals
    
    def manage_positions(self, current_positions: List, 
                        market_data: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Быстрое закрытие позиций по времени или по достижению целей
        """
        actions = []
        
        for pos in current_positions:
            holding_time = (timestamp - pos['entry_time']).total_seconds() / 60
            pnl_pct = self._calculate_position_pnl(pos, market_data)
            
            # Закрытие по времени
            if holding_time > self.holding_period_max:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'max_holding_time_{holding_time:.0f}min'
                })
            
            # Закрытие по PnL
            elif pnl_pct > self.config['take_profit_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'take_profit_{pnl_pct:.2f}%'
                })
            elif pnl_pct < -self.config['stop_loss_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'stop_loss_{pnl_pct:.2f}%'
                })
        
        return actions
    
    def _calculate_rsi(self, data: pd.DataFrame, period: int) -> float:
        """RSI индикатор"""
        pass
    
    def _detect_volume_spike(self, data: pd.DataFrame) -> bool:
        """Детекция аномального объёма"""
        pass
    
    def _detect_breakout(self, data: pd.DataFrame) -> str:
        """Детекция breakout/breakdown"""
        pass
```

### 3.4 Positional Short Gamma (`strategy/components/positional_short_gamma.py`)

```python
class PositionalShortGamma(BaseStrategy):
    """
    Компонент 3: Позиционная продажа гаммы (держим overnight)
    
    Логика:
    - Продажа опционов с экспирацией 7-30 дней
    - Стратегии: Iron Condor, Iron Butterfly, Strangles
    - Удержание позиций несколько дней
    - Активный risk management через adjustments
    
    Сигналы входа:
    - Высокая IV rank (> 50 percentile)
    - Низкая ожидаемая волатильность в ближайшие дни
    - Технический анализ: consolidation, range-bound market
    """
    
    def __init__(self, config: Dict):
        super().__init__("Positional Short Gamma", config)
        self.min_dte = config.get('min_dte', 7)
        self.max_dte = config.get('max_dte', 30)
        self.iv_rank_threshold = config.get('iv_rank_threshold', 50)
        self.adjustment_delta_threshold = config.get('adjustment_delta_threshold', 0.3)
    
    def generate_signals(self, market_data: pd.DataFrame, 
                        options_chain: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Генерация сигналов для позиционных short gamma стратегий
        """
        signals = []
        
        # 1. Фильтрация по DTE
        eligible_options = self._filter_by_dte_range(options_chain, 
                                                     self.min_dte, self.max_dte)
        
        # 2. Проверка IV rank
        iv_rank = self._calculate_iv_rank(eligible_options, market_data, period=30)
        
        if iv_rank > self.iv_rank_threshold:
            # 3. Построение Iron Condor или Iron Butterfly
            structure = self._build_option_structure(eligible_options, 
                                                     strategy_type='iron_condor')
            
            if structure:
                signals.append({
                    'action': 'open',
                    'structure': structure,  # несколько legs
                    'strategy_type': 'iron_condor',
                    'reason': f'high_iv_rank_{iv_rank:.1f}_low_realized_vol',
                    'expected_profit': structure['max_profit'],
                    'max_loss': structure['max_loss'],
                    'breakeven_points': structure['breakevens']
                })
        
        return signals
    
    def manage_positions(self, current_positions: List, 
                        market_data: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Управление позиционными позициями: adjustments, rolls, early exits
        """
        actions = []
        
        for pos in current_positions:
            # 1. Проверка приближения к экспирации
            dte = (pos['expiry_date'] - timestamp).days
            if dte <= self.config['min_dte_before_roll']:
                # Roll позицию на следующую экспирацию
                actions.append(self._generate_roll_action(pos, market_data))
            
            # 2. Проверка delta exposure
            current_delta = self._calculate_position_delta(pos, market_data)
            if abs(current_delta) > self.adjustment_delta_threshold:
                # Adjust позицию (добавить противоположный leg)
                actions.append(self._generate_adjustment_action(pos, market_data))
            
            # 3. Проверка достижения max profit
            pnl_pct = self._calculate_position_pnl(pos, market_data)
            if pnl_pct > self.config['take_profit_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'take_profit_{pnl_pct:.2f}%'
                })
            
            # 4. Stop loss
            elif pnl_pct < -self.config['stop_loss_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'stop_loss_{pnl_pct:.2f}%'
                })
        
        return actions
    
    def _build_option_structure(self, options: pd.DataFrame, 
                                strategy_type: str) -> Dict:
        """
        Построение multi-leg опционных структур
        
        Iron Condor:
        - Sell OTM Call (дельта ~0.20)
        - Buy further OTM Call (защита)
        - Sell OTM Put (дельта ~-0.20)
        - Buy further OTM Put (защита)
        """
        pass
    
    def _generate_roll_action(self, position: Dict, market_data: pd.DataFrame) -> Dict:
        """Rolling позиции на следующую экспирацию"""
        pass
    
    def _generate_adjustment_action(self, position: Dict, 
                                    market_data: pd.DataFrame) -> Dict:
        """Adjustment позиции для снижения delta exposure"""
        pass
```

### 3.5 Positional Delta (`strategy/components/positional_delta.py`)

```python
class PositionalDelta(BaseStrategy):
    """
    Компонент 4: Позиционные дельта-стратегии
    
    Логика:
    - Направленные ставки на средний срок (3-7 дней)
    - Использование спредов для снижения стоимости
    - Комбинации с volatility plays
    
    Сигналы:
    - Технический анализ: trend following, breakouts
    - Фундаментальные события (если применимо к крипте)
    - Sentiment индикаторы
    """
    
    def __init__(self, config: Dict):
        super().__init__("Positional Delta", config)
        self.min_dte = config.get('min_dte', 7)
        self.max_dte = config.get('max_dte', 30)
        self.trend_period = config.get('trend_period', 20)  # для MA
    
    def generate_signals(self, market_data: pd.DataFrame, 
                        options_chain: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Генерация направленных сигналов для позиционной торговли
        """
        signals = []
        
        # 1. Определение тренда
        trend = self._identify_trend(market_data, period=self.trend_period)
        trend_strength = self._calculate_trend_strength(market_data)
        
        # 2. Если сильный тренд - входим
        if trend == 'bullish' and trend_strength > self.config['min_trend_strength']:
            # Bullish strategy: Bull Call Spread или Long Call
            eligible_calls = self._filter_calls_by_dte(options_chain, 
                                                       self.min_dte, self.max_dte)
            
            # Выбираем ATM или slightly OTM call
            best_call = self._select_trend_option(eligible_calls, trend='bullish')
            
            signals.append({
                'action': 'open',
                'symbol': best_call['symbol'],
                'quantity': self._calculate_position_size(best_call),
                'side': 'buy',
                'direction': 'bullish',
                'reason': f'strong_bullish_trend_{trend_strength:.2f}',
                'expected_holding_days': 5
            })
        
        elif trend == 'bearish' and trend_strength > self.config['min_trend_strength']:
            # Bearish strategy: Bear Put Spread или Long Put
            eligible_puts = self._filter_puts_by_dte(options_chain, 
                                                     self.min_dte, self.max_dte)
            
            best_put = self._select_trend_option(eligible_puts, trend='bearish')
            
            signals.append({
                'action': 'open',
                'symbol': best_put['symbol'],
                'quantity': self._calculate_position_size(best_put),
                'side': 'buy',
                'direction': 'bearish',
                'reason': f'strong_bearish_trend_{trend_strength:.2f}',
                'expected_holding_days': 5
            })
        
        return signals
    
    def manage_positions(self, current_positions: List, 
                        market_data: pd.DataFrame,
                        timestamp: datetime) -> List[Dict]:
        """
        Управление позиционными направленными позициями
        """
        actions = []
        
        for pos in current_positions:
            # 1. Проверка изменения тренда
            current_trend = self._identify_trend(market_data, period=self.trend_period)
            if current_trend != pos['direction']:
                # Тренд сменился - закрываем
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'trend_reversal_{current_trend}'
                })
                continue
            
            # 2. Trailing stop
            pnl_pct = self._calculate_position_pnl(pos, market_data)
            if pnl_pct > 20:  # если в прибыли > 20%
                # Активируем trailing stop
                if pnl_pct < pos.get('max_pnl', 0) - self.config['trailing_stop_pct']:
                    actions.append({
                        'action': 'close',
                        'position_id': pos['id'],
                        'reason': f'trailing_stop_hit_{pnl_pct:.2f}%'
                    })
            
            # 3. Standard stop loss
            if pnl_pct < -self.config['stop_loss_pct']:
                actions.append({
                    'action': 'close',
                    'position_id': pos['id'],
                    'reason': f'stop_loss_{pnl_pct:.2f}%'
                })
        
        return actions
    
    def _identify_trend(self, data: pd.DataFrame, period: int) -> str:
        """Определение тренда через MA crossover или price action"""
        pass
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Сила тренда (0-100)"""
        pass
```

### 3.6 Portfolio Manager (`strategy/portfolio_manager.py`)

```python
class PortfolioManager:
    """
    Координатор всех 4 компонентов стратегии
    """
    
    def __init__(self, total_capital: float, config: Dict):
        self.total_capital = total_capital
        self.config = config
        
        # Инициализация всех 4 компонентов
        self.components = {
            'intraday_short_gamma': IntradayShortGamma(config['intraday_short_gamma']),
            'intraday_delta': IntradayDelta(config['intraday_delta']),
            'positional_short_gamma': PositionalShortGamma(config['positional_short_gamma']),
            'positional_delta': PositionalDelta(config['positional_delta'])
        }
        
        # Распределение капитала (как в оригинальной стратегии: 85% intraday, 15% overnight)
        self.capital_allocation = {
            'intraday_short_gamma': 0.50,  # 50% от total
            'intraday_delta': 0.35,         # 35% от total
            'positional_short_gamma': 0.10, # 10% от total
            'positional_delta': 0.05        # 5% от total
        }
    
    def allocate_capital(self) -> Dict[str, float]:
        """Распределение капитала между компонентами"""
        return {
            comp: self.total_capital * allocation 
            for comp, allocation in self.capital_allocation.items()
        }
    
    def generate_all_signals(self, market_data: pd.DataFrame, 
                            options_chain: pd.DataFrame,
                            timestamp: datetime) -> Dict[str, List]:
        """
        Генерация сигналов от всех компонентов
        """
        all_signals = {}
        
        for comp_name, component in self.components.items():
            signals = component.generate_signals(market_data, options_chain, timestamp)
            all_signals[comp_name] = signals
        
        return all_signals
    
    def manage_all_positions(self, current_positions: Dict[str, List], 
                            market_data: pd.DataFrame,
                            timestamp: datetime) -> Dict[str, List]:
        """
        Управление позициями всех компонентов
        """
        all_actions = {}
        
        for comp_name, component in self.components.items():
            comp_positions = current_positions.get(comp_name, [])
            actions = component.manage_positions(comp_positions, market_data, timestamp)
            all_actions[comp_name] = actions
        
        return all_actions
    
    def calculate_portfolio_risk(self, all_positions: Dict[str, List],
                                 market_data: pd.DataFrame) -> Dict:
        """
        Расчёт портфельных метрик риска
        
        Возвращает:
        - total_delta: суммарная дельта портфеля
        - total_gamma: суммарная гамма
        - total_vega: exposure к волатильности
        - total_theta: ожидаемый дневной decay
        - var_99: Value at Risk (99%)
        - max_loss_scenario: worst case loss
        """
        pass
    
    def check_risk_limits(self, portfolio_risk: Dict) -> List[str]:
        """
        Проверка лимитов риска
        
        Лимиты (из оригинальной стратегии):
        - Overnight VaR < 5% от капитала
        - Max single position < 2% от капитала
        - Max component drawdown < 10%
        """
        violations = []
        
        if portfolio_risk['var_99'] > self.total_capital * 0.05:
            violations.append(f"VaR violation: {portfolio_risk['var_99']:.2f}")
        
        # Добавить другие проверки...
        
        return violations
```

***

## 4. МОДУЛЬ БЭКТЕСТА

### 4.1 Backtest Engine (`backtest/engine.py`)

```python
class BacktestEngine:
    """
    Основной движок бэктестирования
    """
    
    def __init__(self, db: OptionsDatabase, portfolio_manager: PortfolioManager,
                 start_date: datetime, end_date: datetime, config: Dict):
        self.db = db
        self.portfolio_manager = portfolio_manager
        self.start_date = start_date
        self.end_date = end_date
        self.config = config
        
        self.execution_engine = ExecutionEngine(config['execution'])
        self.risk_manager = RiskManager(config['risk'])
        self.performance_tracker = PerformanceTracker()
        
        self.current_positions = {comp: [] for comp in portfolio_manager.components.keys()}
        self.equity_curve = []
        self.trade_log = []
    
    def run(self, interval: str = '5m') -> Dict:
        """
        Запуск бэктеста
        
        Параметры:
        - interval: частота обновления ('1m', '5m', '15m', '1h')
        
        Возвращает:
        - результаты бэктеста с метриками
        """
        print(f"Starting backtest from {self.start_date} to {self.end_date}")
        print(f"Initial capital: ${self.portfolio_manager.total_capital:,.2f}")
        
        # Генерация таймстемпов для симуляции
        timestamps = self._generate_timestamps(self.start_date, self.end_date, interval)
        
        for i, timestamp in enumerate(timestamps):
            if i % 100 == 0:
                progress = i / len(timestamps) * 100
                print(f"Progress: {progress:.1f}% - {timestamp}")
            
            # 1. Загрузка рыночных данных на текущий момент
            market_data = self.db.get_futures_klines(
                symbol='BTCUSDT', 
                end_time=timestamp, 
                lookback_periods=100
            )
            
            options_chain = self.db.get_options_chain(
                timestamp=timestamp,
                base_coin='BTC',
                expiry_range=(timestamp, timestamp + timedelta(days=30))
            )
            
            # 2. Обновление греков для текущих позиций
            self._update_positions_greeks(self.current_positions, options_chain)
            
            # 3. Управление существующими позициями
            all_actions = self.portfolio_manager.manage_all_positions(
                self.current_positions, market_data, timestamp
            )
            self._execute_actions(all_actions, market_data, timestamp)
            
            # 4. Генерация новых сигналов
            all_signals = self.portfolio_manager.generate_all_signals(
                market_data, options_chain, timestamp
            )
            self._execute_signals(all_signals, market_data, timestamp)
            
            # 5. Расчёт портфельного риска
            portfolio_risk = self.portfolio_manager.calculate_portfolio_risk(
                self.current_positions, market_data
            )
            
            # 6. Проверка risk limits
            violations = self.portfolio_manager.check_risk_limits(portfolio_risk)
            if violations:
                print(f"Risk violations at {timestamp}: {violations}")
                # Реагировать на violation (снизить exposure, закрыть позиции)
            
            # 7. Трекинг производительности
            equity = self._calculate_total_equity(timestamp, market_data)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'portfolio_delta': portfolio_risk['total_delta'],
                'portfolio_gamma': portfolio_risk['total_gamma'],
                'var_99': portfolio_risk['var_99']
            })
        
        # 8. Финальный расчёт метрик
        results = self.performance_tracker.calculate_metrics(
            self.equity_curve, 
            self.trade_log
        )
        
        return results
    
    def _execute_signals(self, signals: Dict[str, List], 
                        market_data: pd.DataFrame, timestamp: datetime):
        """Исполнение сигналов через execution engine"""
        for comp_name, comp_signals in signals.items():
            for signal in comp_signals:
                # Симуляция исполнения с slippage и fees
                executed_trade = self.execution_engine.execute(signal, market_data, timestamp)
                
                if executed_trade:
                    # Добавляем в текущие позиции
                    self.current_positions[comp_name].append(executed_trade)
                    self.trade_log.append(executed_trade)
    
    def _execute_actions(self, actions: Dict[str, List], 
                        market_data: pd.DataFrame, timestamp: datetime):
        """Исполнение действий (закрытие, adjustment)"""
        for comp_name, comp_actions in actions.items():
            for action in comp_actions:
                if action['action'] == 'close':
                    self._close_position(comp_name, action['position_id'], 
                                        market_data, timestamp)
                elif action['action'] == 'adjust':
                    # Adjustment логика
                    pass
    
    def _close_position(self, component: str, position_id: str, 
                       market_data: pd.DataFrame, timestamp: datetime):
        """Закрытие позиции"""
        positions = self.current_positions[component]
        position = next((p for p in positions if p['id'] == position_id), None)
        
        if position:
            # Получаем текущую цену для закрытия
            close_price = self._get_current_option_price(position['symbol'], market_data)
            
            # Расчёт PnL с учётом slippage и fees
            pnl = self.execution_engine.calculate_pnl(position, close_price)
            
            # Логирование
            self.trade_log.append({
                'timestamp': timestamp,
                'component': component,
                'action': 'close',
                'symbol': position['symbol'],
                'entry_price': position['entry_price'],
                'exit_price': close_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'holding_time': (timestamp - position['entry_time']).total_seconds() / 3600
            })
            
            # Удаляем из current_positions
            positions.remove(position)
    
    def _generate_timestamps(self, start: datetime, end: datetime, 
                            interval: str) -> List[datetime]:
        """Генерация таймстемпов для бэктеста"""
        pass
    
    def _calculate_total_equity(self, timestamp: datetime, 
                               market_data: pd.DataFrame) -> float:
        """Расчёт текущей стоимости портфеля"""
        pass
```

### 4.2 Execution Engine (`backtest/execution.py`)

```python
class ExecutionEngine:
    """
    Симуляция реального исполнения ордеров
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.slippage_model = config.get('slippage_model', 'fixed')
        self.base_slippage_bps = config.get('base_slippage_bps', 10)  # 0.1%
        self.maker_fee = config.get('maker_fee', 0.02)  # 0.02%
        self.taker_fee = config.get('taker_fee', 0.055)  # 0.055% (Bybit)
    
    def execute(self, signal: Dict, market_data: pd.DataFrame, 
                timestamp: datetime) -> Dict:
        """
        Симуляция исполнения торгового сигнала
        
        Учитывает:
        - Bid-ask spread
        - Slippage (зависит от волатильности и объёма)
        - Trading fees
        - Возможность отклонения ордера (insufficient liquidity)
        """
        symbol = signal['symbol']
        side = signal['side']
        quantity = signal['quantity']
        
        # 1. Получение текущих цен (bid/ask)
        option_data = self._get_option_data(symbol, market_data, timestamp)
        
        if not option_data:
            return None  # Опцион недоступен
        
        # 2. Определение цены исполнения
        if side == 'buy':
            base_price = option_data['ask1_price']
        else:  # sell
            base_price = option_data['bid1_price']
        
        # 3. Применение slippage
        slippage = self._calculate_slippage(option_data, quantity, market_data)
        execution_price = base_price * (1 + slippage if side == 'buy' else 1 - slippage)
        
        # 4. Расчёт fees
        fee = execution_price * quantity * (self.maker_fee / 100)
        
        # 5. Проверка ликвидности (опционально)
        if not self._check_liquidity(option_data, quantity):
            print(f"Insufficient liquidity for {symbol} at {timestamp}")
            return None
        
        # 6. Создание executed trade
        executed_trade = {
            'id': self._generate_trade_id(),
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': execution_price,
            'slippage': slippage,
            'fee': fee,
            'greeks': option_data['greeks'],
            'entry_time': timestamp,
            'expiry_date': option_data['expiry_date'],
            'status': 'open'
        }
        
        return executed_trade
    
    def _calculate_slippage(self, option_data: Dict, quantity: int, 
                           market_data: pd.DataFrame) -> float:
        """
        Модель slippage на основе:
        - Bid-ask spread
        - Текущей волатильности
        - Размера ордера относительно объёма
        """
        if self.slippage_model == 'fixed':
            return self.base_slippage_bps / 10000
        
        elif self.slippage_model == 'adaptive':
            # Bid-ask spread component
            spread = (option_data['ask1_price'] - option_data['bid1_price']) / option_data['mark_price']
            
            # Volatility component (больше vol = больше slippage)
            current_iv = option_data.get('mark_iv', 0.5)
            vol_multiplier = 1 + (current_iv - 0.5) * 0.5  # +50% slippage при IV=1.0
            
            # Volume component (больший ордер = больше slippage)
            volume_multiplier = 1 + (quantity / 100) * 0.1  # +10% slippage на каждые 100 контрактов
            
            total_slippage = spread * vol_multiplier * volume_multiplier
            
            return min(total_slippage, 0.02)  # cap at 2%
        
        return self.base_slippage_bps / 10000
    
    def _check_liquidity(self, option_data: Dict, quantity: int) -> bool:
        """Проверка достаточности ликвидности"""
        # Упрощённо: если bid1/ask1 volume > quantity
        return option_data.get('volume', 0) > quantity * 2
    
    def calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """
        Расчёт PnL при закрытии позиции
        """
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']
        
        if side == 'buy':
            # Купили опцион, продаём его
            price_diff = exit_price - entry_price
        else:  # sell
            # Продали опцион, откупаем его
            price_diff = entry_price - exit_price
        
        gross_pnl = price_diff * quantity
        
        # Вычитаем fees на вход и выход
        exit_fee = exit_price * quantity * (self.taker_fee / 100)
        total_fees = position['fee'] + exit_fee
        
        net_pnl = gross_pnl - total_fees
        
        return net_pnl
```

### 4.3 Risk Manager (`backtest/risk_manager.py`)

```python
class RiskManager:
    """
    Управление рисками портфеля
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.max_portfolio_var = config.get('max_portfolio_var_pct', 5)
        self.max_single_position_pct = config.get('max_single_position_pct', 2)
        self.max_component_drawdown = config.get('max_component_drawdown', 10)
    
    def calculate_var(self, positions: List[Dict], market_data: pd.DataFrame,
                      confidence_level: float = 0.99) -> float:
        """
        Value at Risk calculation
        
        Методы:
        - Historical simulation (используем исторические returns)
        - Parametric VaR (используем распределение

[1](https://www.bybit.com/future-activity/en/developer)
[2](https://bybit-exchange.github.io/docs/v5/market/iv)
[3](https://www.youtube.com/watch?v=558k7D2alxM)
[4](https://unofficed.com/courses/mastering-algotrading-beginners-guide-nsepython/lessons/black-scholes-formula-in-python/)
[5](https://bybit-exchange.github.io/docs/v5/order/execution)
[6](https://www.amberdata.io/bybit-market-data)
[7](https://www.bybit.com/derivatives/en/history-data)
[8](https://www.reddit.com/r/options/comments/1h5ss52/i_developed_a_versatile_backtesting_tool_for_spx/)
[9](https://www.codearmo.com/python-tutorial/getting-crypto-data-bybit)
[10](https://greekslab.com/guide)
