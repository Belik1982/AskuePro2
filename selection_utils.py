import pandas as pd

def compute_detailed_selection_stats(df: pd.DataFrame, selected_xrange):
    if not selected_xrange or len(selected_xrange) != 2:
        return None, None
    
    xmin, xmax = selected_xrange
    mask = (df["DateTime"] >= xmin) & (df["DateTime"] <= xmax)
    sel = df.loc[mask]
    
    if sel.empty: return None, None

    stats_list = []
    grouped = sel.groupby(["MeterID", "Type"])
    
    for (meter, typ), group in grouped:
        val = group["Value"]
        stats_list.append({
            "name": f"{meter} {typ}",
            "sum": val.sum(),
            "avg": val.mean(),
            "min": val.min(),
            "max": val.max()
        })
    
    stats_list.sort(key=lambda x: x["name"])
    actual_range = [sel["DateTime"].min(), sel["DateTime"].max()]
    return stats_list, actual_range