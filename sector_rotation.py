import requests
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import time
import os
import json
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
class Config:
    # API Configuration
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY not found in environment variables")
        
    # MT5 Credentials
    MT5_LOGIN = os.getenv('MT5_LOGIN')
    MT5_PASSWORD = os.getenv('MT5_PASSWORD')
    MT5_SERVER = os.getenv('MT5_SERVER')
    
    if not all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]):
        raise ValueError("Missing MT5 credentials in environment variables")
        
    # Updated API base URL
    API_BASE_URL = "https://metasyc.p.rapidapi.com"
    
    # Request headers
    HEADERS = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "metasyc.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    
    # Available endpoints
    ENDPOINTS = {
        'connect': '/connect',
        'shutdown': '/shutdown',
        'version': '/version',
        'terminal_info': '/terminal_info',
        'account_info': '/account_info',
        'symbols': '/symbols',
        'symbol_info': '/symbol_info',
        'tick': '/tick',
        'ticks': '/ticks',
        'ohlc': '/ohlc',
        'order_send': '/order_send',
        'positions': '/positions',
        'orders': '/orders',
        'deals': '/deals',
        'history_orders': '/history_orders'
    }
    
    # Request headers
    HEADERS = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "Content-Type": "application/json"
    }
    
    # Sector ETF symbols available through MetaSync/IC Markets
    SECTORS = {
        'Financials': 'XLF',
        'Energy': 'XLE',
        'Industrials': 'XLI',
        'Consumer Staples': 'XLP',
        'Utilities': 'XLU',
        'Healthcare': 'XLV',
        'Technology': 'USTEC'  # NASDAQ-100 as tech proxy
    }
    
    # Benchmark - the S&P 500
    BENCHMARK = 'US500'
    
    # Trading Rules
    TRADING_RULES = {
        'min_relative_strength': 1.0,      # Sector must outperform SP500 by at least 1%
        'max_positions': 2,                # Maximum number of concurrent sector positions
        'position_risk_percent': 0.02,     # Risk 2% of account per position
        'stop_loss_pct': 0.05,             # 5% stop loss from entry price
        'take_profit_pct': 0.15,           # 15% take profit target
        'min_trade_interval': 7,           # Days between rebalancing
        'require_positive_momentum': True,  # Both 1-day AND 5-day strength must be positive
    }
    
    # Risk Management
    RISK_CONFIG = {
        'max_position_risk': 0.02,     # 2% risk per position
        'max_daily_loss': 0.05,        # 5% maximum daily loss
        'max_drawdown': 0.15,          # 15% maximum portfolio drawdown
        'max_sector_exposure': 0.25,   # No more than 25% in one sector
        'overall_leverage': 3.0,       # Maximum overall leverage
        'min_market_trend': 0,         # SP500 must be above 200-day MA
        'max_volatility': 0.03,        # Avoid high volatility periods (3%+ daily move)
        'trading_hours_only': True,    # Only trade during market hours
    }

class MetaSyncAPI:
    """Wrapper for MetaSync API calls with rate limiting"""
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        self.connected = False
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
    
    def _make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> dict:
        """Make an API request with rate limiting and error handling"""
        self._rate_limit()
        
        url = f"{Config.API_BASE_URL}{endpoint}"
        headers = {**Config.HEADERS, **kwargs.pop('headers', {})}
        
        # Log request details (without sensitive data)
        log_params = {k: v for k, v in kwargs.items() if k not in ['password', 'api_key']}
        print(f"🔹 API Request: {method} {endpoint}")
        if log_params:
            print(f"   Params: {log_params}")
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=kwargs, timeout=15)
            elif method.upper() == 'POST':
                # For POST requests, move params to json body
                json_data = kwargs.pop('json', kwargs)
                response = requests.post(url, headers=headers, json=json_data, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Log response time
            response_time = (time.time() - start_time) * 1000  # in milliseconds
            
            # Handle rate limiting
            if response.status_code == 429:  # Too Many Requests
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f"  ⚠️  Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                # Retry the request once after waiting
                return self._make_request(endpoint, method, **kwargs)
            
            response.raise_for_status()
            
            # Log successful response
            print(f"  ✅ Response in {response_time:.2f}ms")
            
            self.last_request_time = time.time()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ API request failed for {endpoint}: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (Status: {e.response.status_code})"
                try:
                    error_details = e.response.json()
                    error_msg += f"\n  Details: {error_details}"
                except:
                    error_msg += f"\n  Response: {e.response.text[:200]}"
            
            print(error_msg)
            return {"error": True, "message": str(e)}
    
    def connect(self) -> bool:
        """Connect to MetaTrader5 terminal"""
        if self.connected:
            return True
            
        print(f"Connecting to MetaTrader5 terminal (Server: {Config.MT5_SERVER})...")
        
        # Prepare connection data
        connection_data = {
            'login': int(Config.MT5_LOGIN),
            'password': Config.MT5_PASSWORD,
            'server': Config.MT5_SERVER,
            'path': "",  # Empty path for default terminal location
            'timeout': 10000  # 10 seconds timeout
        }
        
        try:
            # Make the connection request with proper JSON payload
            result = self._make_request(
                Config.ENDPOINTS['connect'], 
                'POST', 
                json=connection_data
            )
            
            # Check the response format
            if result.get('connected', False) and result.get('status') == 'success':
                self.connected = True
                print("✅ Successfully connected to MetaTrader5")
                print(f"   Login: {result.get('login')}")
                print(f"   Server: {result.get('server')}")
            else:
                error = result.get('message', 'Unknown error')
                print(f"❌ Failed to connect to MetaTrader5: {error}")
                self.connected = False
                
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            self.connected = False
            
        return self.connected
    
    def get_ohlc(self, symbol: str, timeframe: str = 'D1', count: int = 1) -> List[dict]:
        """
        Fetch OHLC data for a given symbol
        
        Args:
            symbol: Symbol to fetch data for
            timeframe: Timeframe (e.g., 'D1' for daily, 'H1' for hourly)
            count: Number of candles to return
            
        Returns:
            List of OHLC data points as dictionaries
        """
        if not self.connected and not self.connect():
            print("❌ Error: Not connected to MetaTrader5")
            return []
            
        try:
            # Calculate date range for the requested number of candles
            end_date = datetime.now()
            if timeframe == 'D1':
                start_date = end_date - timedelta(days=count * 2)  # Add buffer
            elif timeframe == 'H1':
                start_date = end_date - timedelta(hours=count * 2)  # Add buffer
            else:
                start_date = end_date - timedelta(days=count)  # Default to daily
                
            params = {
                'symbol': symbol,
                'timeframe': timeframe,
                'date_from': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'date_to': end_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"🔹 Fetching OHLC data for {symbol} ({timeframe}) from {start_date} to {end_date}")
            result = self._make_request(Config.ENDPOINTS['ohlc'], 'GET', **params)
            
            # Ensure we return a list of candles
            if isinstance(result, list):
                # Sort by time (oldest first) and take the last 'count' candles
                result = sorted(result, key=lambda x: x.get('time', 0))[-count:]
                print(f"  ✅ Retrieved {len(result)} candles for {symbol}")
                return result
            elif isinstance(result, dict):
                if 'candles' in result:
                    candles = result['candles']
                    candles = sorted(candles, key=lambda x: x.get('time', 0))[-count:]
                    print(f"  ✅ Retrieved {len(candles)} candles for {symbol} from 'candles' key")
                    return candles
                elif 'message' in result:
                    print(f"  ⚠️  API Error for {symbol}: {result.get('message')}")
            
            print(f"  ⚠️  Unexpected OHLC response format for {symbol}")
            return []
                
        except Exception as e:
            print(f"❌ Error fetching OHLC data for {symbol}: {str(e)}")
            return []
    
    def get_tick(self, symbol: str) -> dict:
        """Get current tick data for a symbol"""
        if not self.connected and not self.connect():
            print("Error: Not connected to MetaTrader5")
            return {}
            
        return self._make_request(Config.ENDPOINTS['tick'], 'GET', symbol=symbol)
    
    def get_account_info(self) -> dict:
        """Get account information"""
        if not self.connected and not self.connect():
            print("Error: Not connected to MetaTrader5")
            return {}
            
        return self._make_request(Config.ENDPOINTS['account_info'], 'GET')
    
    def get_positions(self) -> List[dict]:
        """Get open positions"""
        if not self.connected and not self.connect():
            print("Error: Not connected to MetaTrader5")
            return []
            
        result = self._make_request(Config.ENDPOINTS['positions'], 'GET')
        return result.get('positions', [])
    
    @staticmethod
    def get_account_info() -> dict:
        """Fetch account information"""
        url = f"https://{Config.RAPIDAPI_HOST}/get_account"
        
        headers = {
            'X-RapidAPI-Key': Config.RAPIDAPI_KEY,
            'X-RapidAPI-Host': Config.RAPIDAPI_HOST
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}
    
    def get_symbol_info(self, symbol: str) -> dict:
        """
        Fetch symbol information
        
        Args:
            symbol: Symbol to fetch information for (e.g., 'XLF.NYSE')
            
        Returns:
            Dictionary containing symbol information or empty dict if not found
        """
        if not self.connected and not self.connect():
            print("Error: Not connected to MetaTrader5")
            return {}
            
        # The API expects the symbol as a query parameter
        return self._make_request(Config.ENDPOINTS['symbol_info'], 'GET', symbol=symbol)
    
    @staticmethod
    def get_open_positions() -> List[dict]:
        """Fetch current open positions"""
        # This is a placeholder - implement based on your broker's API
        return []

class SectorRotationStrategy:
    """ETF Sector Rotation Strategy Implementation"""
    
    def __init__(self):
        self.api = MetaSyncAPI()
        self.performance_tracker = PerformanceTracker()
        self.last_trade_time = None
        self.connected = False
        self.symbol_info = {}
    
    def initialize(self) -> bool:
        """Initialize the strategy and connect to the API"""
        print("Initializing Sector Rotation Strategy...")
        self.connected = self.api.connect()
        
        if not self.connected:
            print("❌ Failed to connect to MetaTrader5")
            return False
        
        # Load symbol information
        self._load_symbol_info()
        return True
        
    def _load_symbol_info(self) -> pd.DataFrame:
        """
        Load symbol information for all sectors and benchmark
        
        Returns:
            DataFrame containing sector information with prices and returns
        """
        sector_data = []
        
        # Define sector symbols with their full exchange names
        sector_symbols = {
            'Financials': 'XLF.NYSE',
            'Energy': 'XLE.NYSE',
            'Industrials': 'XLI.NYSE',
            'Consumer Staples': 'XLP.NYSE',
            'Utilities': 'XLU.NYSE',
            'Healthcare': 'XLV.NYSE',
            'Technology': 'USTEC'  # NASDAQ-100 as tech proxy (no .NASDAQ suffix needed)
        }
        
        print("Loading symbol information...")
        
        for sector_name, symbol in sector_symbols.items():
            try:
                print(f"🔹 Fetching info for {sector_name} ({symbol})...")
                full_symbol = symbol
                
                # Get symbol info
                symbol_info = self.api.get_symbol_info(full_symbol)
                if not symbol_info:
                    print(f"  ❌ No symbol info found for {sector_name} ({full_symbol})")
                    continue
                
                print(f"  ✅ Successfully loaded {sector_name} ({full_symbol}) info")
                
                # Get tick data (current price)
                print(f"  🔄 Fetching tick data...")
                tick_data = self.api.get_tick(full_symbol)
                
                if not tick_data or 'bid' not in tick_data or 'ask' not in tick_data:
                    print(f"  ❌ No valid tick data for {sector_name} ({full_symbol})")
                    continue
                
                # Calculate mid price
                current_price = (tick_data['bid'] + tick_data['ask']) / 2
                
                # Get OHLC data for daily change calculation
                print(f"  🔄 Fetching OHLC data for {sector_name} ({full_symbol})...")
                ohlc_data = self.api.get_ohlc(full_symbol, 'D1', 2)  # Get last 2 days
                
                daily_change = 0.0
                if ohlc_data and len(ohlc_data) >= 2:
                    # Calculate daily change from previous close to current price
                    prev_close = ohlc_data[0]['close']
                    if prev_close > 0:  # Avoid division by zero
                        daily_change = ((current_price - prev_close) / prev_close) * 100
                
                # Add to sector data
                sector_data.append({
                    'sector': sector_name,
                    'symbol': full_symbol,
                    'price': current_price,
                    'change': daily_change,
                    'volume': tick_data.get('volume', 0),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                print(f"  ✅ Successfully processed {sector_name} data")
                time.sleep(0.5)  # Add delay between API calls
                
            except Exception as e:
                print(f"❌ Error processing {sector_name}: {str(e)}")
        
        # Convert to DataFrame if we have data, otherwise return empty DataFrame
        if sector_data:
            return pd.DataFrame(sector_data)
        return pd.DataFrame()
        
        # Fetch benchmark data
        benchmark_data = {}
        try:
            # Get benchmark tick data (US500 for S&P 500)
            benchmark_tick = self.api.get_tick(Config.BENCHMARK)
            
            # Get OHLC data for the benchmark
            benchmark_ohlc = self.api.get_ohlc(Config.BENCHMARK, 'D1', 2)
            
            if benchmark_tick and 'last' in benchmark_tick:
                # Calculate daily return for benchmark
                benchmark_change = 0.0
                if benchmark_ohlc and len(benchmark_ohlc) >= 2:
                    prev_close = benchmark_ohlc[1].get('close')
                    current_price = benchmark_tick['last']
                    if prev_close and prev_close != 0:
                        benchmark_change = (current_price - prev_close) / prev_close * 100
                
                benchmark_data = {
                    'price': benchmark_tick['last'],
                    'change': benchmark_change,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            print(f"Error fetching benchmark data: {str(e)}")
        
        return df_sectors.T, benchmark_data
    
    def calculate_relative_strength(self, sector_data: pd.DataFrame, benchmark_data: dict) -> pd.DataFrame:
        """
        Calculate relative strength of sectors compared to benchmark
        
        Args:
            sector_data: DataFrame containing sector data with 'change' column
            benchmark_data: Dictionary containing benchmark data with 'change' key
            
        Returns:
            DataFrame with added 'relative_strength' column
        """
        if sector_data.empty or not benchmark_data:
            return sector_data
        
        # We already have the daily change percentage in the 'change' column
        # Calculate relative strength vs benchmark
        benchmark_change = benchmark_data.get('change', 0)
        sector_data['relative_strength'] = sector_data['change'] - benchmark_change
        
        return sector_data
    
    def display_dashboard(self, sector_data: pd.DataFrame, benchmark_data: dict):
        """
        Display the sector rotation dashboard
        
        Args:
            sector_data: DataFrame containing sector data
            benchmark_data: Dictionary containing benchmark data
        """
        if sector_data.empty:
            print("No sector data available to display.")
            return
        
        # Ensure we have the required columns
        if 'relative_strength' not in sector_data.columns:
            print("Warning: Relative strength data not available.")
            return
        
        # Sort by relative strength
        df_sorted = sector_data.sort_values('relative_strength', ascending=False)
        
        # Print dashboard header
        print("\n" + "="*100)
        print(f"SECTOR ROTATION DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*100)
        
        # Display benchmark info
        benchmark_price = benchmark_data.get('price', 'N/A')
        benchmark_change = benchmark_data.get('change', 0)
        print(f"{Config.BENCHMARK}: {benchmark_price} "
              f"({benchmark_change:+.2f}% daily change)")
        print("="*100)
        
        # Print sector performance table
        print(f"{'Sector':<18} {'Symbol':<12} {'Price':<12} {'Daily %':<12} "
              f"{'Rel Strength':<15} {'Signal'}")
        print("-"*100)
        
        for _, row in df_sorted.iterrows():
            # Get values with defaults to handle any missing data
            sector = row.get('sector', 'N/A')
            symbol = row.get('symbol', 'N/A')
            price = row.get('price', 0)
            change = row.get('change', 0)
            rel_strength = row.get('relative_strength', 0)
            
            # Determine signal strength
            if rel_strength > 1.0:
                signal = "🟢 STRONG"
            elif rel_strength > 0.5:
                signal = "🟡 NEUTRAL"
            else:
                signal = "🔴 WEAK"
            
            # Format the output
            print(f"{sector:<18} {symbol:<12} {price:<12.2f} "
                  f"{change:>+8.2f}%    "
                  f"{rel_strength:>+8.2f}%     {signal}")
        
        print("="*100)
        print("""Legend: 🟢 STRONG (Relative Strength > 1.0%) | """
              """🟡 NEUTRAL (0.5% < RS ≤ 1.0%) | 🔴 WEAK (RS ≤ 0.5%)""")
    
    def run_strategy(self, update_interval: int = 300):
        """
        Main method to run the sector rotation strategy
        
        Args:
            update_interval: Time between updates in seconds (default: 300s = 5 minutes)
        """
        if not self.connected:
            print("❌ Not connected to MetaTrader5. Please initialize the strategy first.")
            return
        
        print("🚀 Starting ETF Sector Rotation Strategy...")
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                # Fetch and process data
                sector_data = self._load_symbol_info()
                
                # Get benchmark data
                try:
                    benchmark_tick = self.api.get_tick(Config.BENCHMARK)
                    if benchmark_tick and 'bid' in benchmark_tick and 'ask' in benchmark_tick:
                        self.benchmark_price = (benchmark_tick['bid'] + benchmark_tick['ask']) / 2
                        benchmark_change = 0  # You might want to calculate this based on previous price
                        
                        # Prepare benchmark data
                        benchmark_data = {
                            'symbol': Config.BENCHMARK,
                            'price': self.benchmark_price,
                            'change': benchmark_change,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        if not sector_data.empty:
                            # Calculate metrics
                            sector_data = self.calculate_relative_strength(sector_data, benchmark_data)
                            
                            # Display dashboard
                            self.display_dashboard(sector_data, benchmark_data)
                            
                            # Generate trading signals (to be implemented)
                            # signals = self.generate_signals(sector_data)
                            # 
                            # # Execute trades (to be implemented)
                            # if self.should_trade():
                            #     self.execute_trades(signals)
                    else:
                        print(f"❌ Could not fetch benchmark data for {Config.BENCHMARK}")
                except Exception as e:
                    print(f"❌ Error fetching benchmark data: {str(e)}")
                
                # Wait for the next update
                print(f"\n🔄 Next update in {update_interval} seconds...")
                time.sleep(update_interval)
                    
        except KeyboardInterrupt:
            print("\n🛑 Strategy monitoring stopped by user.")
        except Exception as e:
            print(f"\n❌ Error in strategy execution: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def calculate_relative_strength(self, sector_data: pd.DataFrame, benchmark_data: dict) -> pd.DataFrame:
        """
        Calculate relative strength of sectors compared to benchmark
        
        Args:
            sector_data: DataFrame containing sector data with 'change' column
            benchmark_data: Dictionary containing benchmark data with 'change' key
            
        Returns:
            DataFrame with added 'relative_strength' column
        """
        if sector_data.empty or not benchmark_data:
            return sector_data
        
        # We already have the daily change percentage in the 'change' column
        # Calculate relative strength vs benchmark
        benchmark_change = benchmark_data.get('change', 0)
        sector_data['relative_strength'] = sector_data['change'] - benchmark_change
        
        return sector_data
    
    def display_dashboard(self, sector_data: pd.DataFrame, benchmark_data: dict):
        """
        Display the sector rotation dashboard
        
        Args:
            sector_data: DataFrame containing sector data
            benchmark_data: Dictionary containing benchmark data
        """
        if sector_data.empty:
            print("No sector data available to display.")
            return
        
        # Ensure we have the required columns
        if 'relative_strength' not in sector_data.columns:
            print("Warning: Relative strength data not available.")
            return
        
        # Sort by relative strength
        df_sorted = sector_data.sort_values('relative_strength', ascending=False)
        
        # Print dashboard header
        print("\n" + "="*100)
        print(f"SECTOR ROTATION DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*100)
        
        # Display benchmark info
        benchmark_price = benchmark_data.get('price', 'N/A')
        benchmark_change = benchmark_data.get('change', 0)
        print(f"{Config.BENCHMARK}: {benchmark_price} "
              f"({benchmark_change:+.2f}% daily change)")
        print("="*100)
        
        # Print sector performance table
        print(f"{'Sector':<18} {'Symbol':<12} {'Price':<12} {'Daily %':<12} "
              f"{'Rel Strength':<15} {'Signal'}")
        print("-"*100)
        
        for _, row in df_sorted.iterrows():
            # Get values with defaults to handle any missing data
            sector = row.get('sector', 'N/A')
            symbol = row.get('symbol', 'N/A')
            price = row.get('price', 0)
            change = row.get('change', 0)
            rel_strength = row.get('relative_strength', 0)
            
            # Determine signal strength
            if rel_strength > 1.0:
                signal = "🟢 STRONG"
            elif rel_strength > 0.5:
                signal = "🟡 NEUTRAL"
            else:
                signal = "🔴 WEAK"
            
            # Format the output
            print(f"{sector:<18} {symbol:<12} {price:<12.2f} "
                  f"{change:>+8.2f}%    "
                  f"{rel_strength:>+8.2f}%     {signal}")
        
        print("="*100)
        print("""Legend: 🟢 STRONG (Relative Strength > 1.0%) | """
              """🟡 NEUTRAL (0.5% < RS ≤ 1.0%) | 🔴 WEAK (RS ≤ 0.5%)""")
    
    def run_strategy(self, update_interval: int = 300):
        """
        Main method to run the sector rotation strategy
        
        Args:
            update_interval: Time between updates in seconds (default: 300s = 5 minutes)
        """
        if not self.connected:
            print("❌ Not connected to MetaTrader5. Please initialize the strategy first.")
            return
        
        print("🚀 Starting ETF Sector Rotation Strategy...")
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                # Fetch and process data
                sector_data = self._load_symbol_info()
                
                # Get benchmark data
                try:
                    benchmark_tick = self.api.get_tick(Config.BENCHMARK)
                    if benchmark_tick and 'bid' in benchmark_tick and 'ask' in benchmark_tick:
                        self.benchmark_price = (benchmark_tick['bid'] + benchmark_tick['ask']) / 2
                        benchmark_change = 0  # You might want to calculate this based on previous price
                        
                        # Prepare benchmark data
                        benchmark_data = {
                            'symbol': Config.BENCHMARK,
                            'price': self.benchmark_price,
                            'change': benchmark_change,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        if not sector_data.empty:
                            # Calculate metrics
                            sector_data = self.calculate_relative_strength(sector_data, benchmark_data)
                            
                            # Display dashboard
                            self.display_dashboard(sector_data, benchmark_data)
                            
                            # Generate trading signals (to be implemented)
                            # signals = self.generate_signals(sector_data)
                            # 
                            # # Execute trades (to be implemented)
                            # if self.should_trade():
                            #     self.execute_trades(signals)
                    else:
                        print(f"❌ Could not fetch benchmark data for {Config.BENCHMARK}")
                except Exception as e:
                    print(f"❌ Error fetching benchmark data: {str(e)}")
                
                # Wait for the next update
                print(f"\n🔄 Next update in {update_interval} seconds...")
                time.sleep(update_interval)
                    
        except KeyboardInterrupt:
            print("\n🛑 Strategy monitoring stopped by user.")
        except Exception as e:
            print(f"\n❌ Error in strategy execution: {str(e)}")
            import traceback
            traceback.print_exc()
    
class PerformanceTracker:
    """Tracks and analyzes strategy performance"""
    
    def __init__(self):
        self.trade_history = []
        self.daily_performance = []
    
    def record_trade(self, trade_data: dict):
        """Record a completed trade"""
        self.trade_history.append({
            **trade_data,
            'timestamp': datetime.now().isoformat()
        })
    
    def calculate_performance_metrics(self) -> dict:
        """Calculate key performance metrics"""
        if not self.trade_history:
            return {}
        
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t.get('profit', 0) > 0]
        losing_trades = [t for t in self.trade_history if t.get('profit', 0) <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t.get('profit', 0) for t in self.trade_history)
        avg_win = (sum(t.get('profit', 0) for t in winning_trades) / 
                  len(winning_trades)) if winning_trades else 0
        avg_loss = (sum(t.get('profit', 0) for t in losing_trades) / 
                   len(losing_trades)) if losing_trades else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        }


def main():
    """Main entry point for the script"""
    try:
        # Initialize and run the strategy
        strategy = SectorRotationStrategy()
        
        # First, try to connect to MT5
        if not strategy.initialize():
            print("❌ Failed to initialize strategy. Please check your credentials and connection.")
            return
            
        # Run the strategy with a 5-minute update interval
        strategy.run_strategy(update_interval=300)
        
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ Script finished")


if __name__ == "__main__":
    main()
