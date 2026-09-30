"""Verified sources and explicit release-lag assumptions (months after observation)."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Series:
    code: str
    name: str
    frequency: str
    units: str
    pillar: int
    lag: int = 1
    optional: bool = False
    source: str = "FRED"

    @property
    def url(self):
        return f"https://fred.stlouisfed.org/series/{self.code}"

    def metadata(self):
        return {**asdict(self), "url": self.url}


FRED = [
    Series("INDPRO", "Industrial Production: Total Index", "monthly", "2017=100, SA", 1),
    Series("RSAFS", "Advance Retail Sales: Retail Trade and Food Services", "monthly", "million USD, SA", 1),
    Series("PAYEMS", "All Employees, Total Nonfarm", "monthly", "thousand persons, SA", 1),
    Series("PCEC96", "Real Personal Consumption Expenditures (cross-check)", "monthly", "billion chained 2017 USD, SAAR", 1, 2, True),
    Series("PCE", "Personal Consumption Expenditures", "monthly", "billion USD, SAAR", 1, 2),
    Series("PCEPI", "PCE Chain-type Price Index", "monthly", "2017=100, SA", 1, 2),
    Series("BAA10Y", "Moody's Baa yield less 10Y Treasury yield", "daily", "percentage points", 2),
    Series("T10Y2Y", "10Y Treasury less 2Y Treasury", "daily", "percentage points", 2),
    Series("NFCI", "Chicago Fed National Financial Conditions Index", "weekly", "index", 2),
    Series("DRTSCILM", "Net banks tightening C&I lending standards, large/middle firms", "quarterly", "percent", 2, 2),
    Series("BAMLH0A0HYM2", "ICE BofA US High Yield Option-Adjusted Spread", "daily", "percentage points", 2, 1, True),
    Series("DRBLACBS", "Business loan delinquency rate, all commercial banks", "quarterly", "percent, SA", 2, 5, True),
    Series("CPIAUCSL", "CPI All Urban Consumers: All Items", "monthly", "1982-84=100, SA", 3),
    Series("CPILFESL", "CPI All Items Less Food and Energy", "monthly", "1982-84=100, SA", 3),
    Series("PPIACO", "Producer Price Index: All Commodities", "monthly", "1982=100, NSA", 3),
    Series("FEDFUNDS", "Effective Federal Funds Rate", "monthly", "percent", 3),
    Series("T5YIE", "5-Year Breakeven Inflation Rate", "daily", "percent", 3),
    Series("GS10", "10-Year Treasury Constant Maturity Yield", "monthly", "percent", 3),
    Series("VIXCLS", "CBOE Volatility Index: VIX", "daily", "index", 4, 0),
    Series("USREC", "NBER Recession Indicator (retrospective reference only)", "monthly", "0/1", 0, 0, True),
]
BY_CODE = {s.code: s for s in FRED}
PILLARS = {1: "Growth Momentum", 2: "Financial Conditions", 3: "Inflation & Policy", 4: "Market Signals"}
SECTORS = {
    "XLB": "Materials", "XLC": "Communication Services", "XLE": "Energy",
    "XLF": "Financials", "XLI": "Industrials", "XLK": "Technology",
    "XLP": "Consumer Staples", "XLRE": "Real Estate", "XLU": "Utilities",
    "XLV": "Health Care", "XLY": "Consumer Discretionary",
}
INCEPTION = {s: "1998-12-16" for s in SECTORS}
INCEPTION.update(XLRE="2015-10-07", XLC="2018-06-18")
MARKET = ["IVV", "RSP", "IWM", "IYW", *SECTORS]
MARKET_CORE = ["IVV", "RSP", "IWM", "IYW", "XLP", "XLV", "XLU", "XLI", "XLF"]
