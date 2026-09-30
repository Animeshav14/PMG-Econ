"""Backward-looking activity growth; retail sales remain nominal."""
def build(raw):
    f, lags = {}, {}
    for code in ["INDPRO", "RSAFS", "PAYEMS", "REAL_PCE"]:
        f[code + "_yoy"] = raw[code].pct_change(12, fill_method=None) * 100
        f[code + "_3m_ann"] = ((raw[code] / raw[code].shift(3)) ** 4 - 1) * 100
        lags[code + "_yoy"] = lags[code + "_3m_ann"] = 2 if code == "REAL_PCE" else 1
    for code in ["ISM_MANUFACTURING", "ISM_SERVICES"]:
        if code in raw:
            f[code + "_level"] = raw[code] - 50
            lags[code + "_level"] = 1
    return f, lags
