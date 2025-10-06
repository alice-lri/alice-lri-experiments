import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def metrics_from_confusion_df(
        df: pd.DataFrame, true_col="true", pred_col="pred", count_col="count", group_cols: list[str] | None = None
) -> pd.DataFrame:

    if group_cols:
        result_df = df.groupby(group_cols).apply(
            lambda g: __metrics_single_group(g, true_col, pred_col, count_col), include_groups=False
        ).reset_index()
    else:
        result_df = __metrics_single_group(df, true_col, pred_col, count_col).to_frame().T

    return result_df.astype({"samples": np.int64, "incorrect": np.int64}, copy=False)


def __metrics_single_group(df: pd.DataFrame, true_col: str, pred_col: str, count_col: str) -> pd.Series:
    y_true = np.repeat(df[true_col].to_numpy(), df[count_col].to_numpy())
    y_pred = np.repeat(df[pred_col].to_numpy(), df[count_col].to_numpy())

    if len(y_true) == 0:
        return pd.Series({
            "samples": 0, "incorrect": 0,
            "oa": 0.0, "mp": 0.0, "mr": 0.0, "mf1": 0.0,
            "wp": 0.0, "wr": 0.0, "wf1": 0.0
        })

    return pd.Series({
        "samples": len(y_true),
        "incorrect": (y_true != y_pred).sum(),
        "oa": accuracy_score(y_true, y_pred) * 100,
        "mp": precision_score(y_true, y_pred, average="macro", zero_division=0) * 100,
        "mr": recall_score(y_true, y_pred, average="macro", zero_division=0) * 100,
        "mf1": f1_score(y_true, y_pred, average="macro", zero_division=0) * 100,
        "wp": precision_score(y_true, y_pred, average="weighted", zero_division=0) * 100,
        "wr": recall_score(y_true, y_pred, average="weighted", zero_division=0) * 100,
        "wf1": f1_score(y_true, y_pred, average="weighted", zero_division=0) * 100,
    })
