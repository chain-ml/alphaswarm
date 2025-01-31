# Price Momentum Strategy

This strategy monitors USDC-denominated price changes across three timeframes: 5min, 1h, and 24h.

## General Rules

### Price Changes
- 5min: Alert on ±1.5% price change
- 1h: Alert on ±3% price change
- 24h: Alert on ±10% price change

## Token-specific Rules

### VIRTUAL
- Higher volatility profile:
  - 5min: ±3% price change
  - 1h: ±8% price change
  - 24h: ±25% price change

### AIXBT
- Moderate volatility profile:
  - 5min: ±2% price change
  - 1h: ±6% price change
  - 24h: ±20% price change
