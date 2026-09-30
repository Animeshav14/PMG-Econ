"""Credit spreads, tighter financial conditions and lending standards."""
def build(raw):
    f = {code: raw[code] for code in ["BAA10Y", "NFCI", "DRTSCILM"]}
    f["curve_inversion"] = -raw["T10Y2Y"]
    return f, {"BAA10Y": 1, "NFCI": 1, "DRTSCILM": 2, "curve_inversion": 1}
