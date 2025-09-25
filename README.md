# ETF Sector Rotation Strategy

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python implementation of a sector rotation trading strategy that identifies and invests in the strongest performing market sectors using the MetaSync API.

## 🌟 Features

- **Real-time Market Analysis**: Monitors major sector ETFs in real-time
- **Relative Strength Scoring**: Identifies outperforming sectors
- **Interactive Dashboard**: Clean console-based dashboard with color-coded signals
- **Configurable**: Easy to modify sectors, timeframes, and parameters
- **Risk Management**: Built-in position sizing and risk controls

<img width="712" height="236" alt="Screenshot 2025-09-25 at 15 55 34" src="https://github.com/user-attachments/assets/879c677e-a19d-447c-b914-563b185ef776" />

## 📊 Strategy Overview

The strategy works by:
1. Tracking major sector ETFs (XLF, XLE, XLI, etc.) and the NASDAQ-100 (USTEC)
2. Calculating relative strength compared to the S&P 500 benchmark
3. Generating trading signals based on price momentum
4. Providing clear visual indicators for sector strength

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- MetaSync API key (get it from [RapidAPI](https://rapidapi.com/))
- (Optional) MetaTrader 5 account for live trading

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yllvar/ETF-Sector-Rotation-Strategy.git
   cd ETF-Sector-Rotation-Strategy
   ```

2. Set up a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment:
   - Copy `.env.example` to `.env`
   - Update with your API credentials
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   # MetaSync API Configuration
   RAPIDAPI_KEY=your_api_key_here
   
   # MT5 Account Details (optional)
   MT5_LOGIN=your_mt5_login
   MT5_PASSWORD=your_mt5_password
   MT5_SERVER=your_mt5_server
   ```

## 🏃 Running the Strategy

1. Start the strategy:
   ```bash
   python sector_rotation.py
   ```

2. View the interactive dashboard:
   ```
   ================================================================================
   SECTOR ROTATION DASHBOARD - 2025-09-25 15:30:00
   ================================================================================
   Sector             Symbol       Price        Daily %    Signal
   --------------------------------------------------------------------------------
   Technology         USTEC        14500.50     +1.85%    🟢 STRONG
   Financials         XLF.NYSE     38.75       +1.25%    🟡 NEUTRAL
   Healthcare         XLV.NYSE     125.30      +0.75%    🟡 NEUTRAL
   ...
   ================================================================================
   ```

## 🛠 Configuration

Edit `config.py` to customize:
- Sectors and symbols to track
- Benchmark index
- Update interval
- Signal thresholds

## 📈 Performance Metrics

The strategy includes built-in performance tracking:
- Daily/Weekly/Monthly returns
- Win/Loss ratio
- Maximum drawdown
- Sharpe ratio

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Resources

- [MetaSync API Documentation](https://docs.metasync.api)
- [Sector Rotation Investing Guide](https://www.investopedia.com/terms/s/sector-rotation.asp)
- [Modern Portfolio Theory](https://www.investopedia.com/terms/m/modernportfoliotheory.asp)

## Risk Warning

This is for educational purposes only. Always test strategies with a paper trading account before risking real capital. Past performance is not indicative of future results.
