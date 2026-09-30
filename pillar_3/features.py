"""Realized inflation, nominal policy and an ex-post long real-yield proxy."""
def build(raw):
    f = {code + "_yoy": raw[code].pct_change(12, fill_method=None) * 100
         for code in ["CPIAUCSL", "CPILFESL", "PPIACO"]}
    f.update({code: raw[code] for code in ["FEDFUNDS", "T5YIE"]})
    f["real_10y_expost"] = raw["GS10"] - f["CPIAUCSL_yoy"]
    return f, {code: 1 for code in f}
