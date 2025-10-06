import os
import re
import sqlite3

import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

def df_to_latex(df: pd.DataFrame, **kwargs) -> str:
    latex = df.to_latex(**kwargs)
    latex = add_multi_column_rules(df, latex)
    latex = fix_multi_row(latex)

    return latex


def add_multi_column_rules(df: pd.DataFrame, latex: str) -> str:
    latex_lines = latex.splitlines()
    first_multi_idx = next((i for i, line in enumerate(latex_lines) if "\\multicolumn" in line), -1)

    first_toprule_idx = next((i for i, line in enumerate(latex_lines) if "\\toprule" in line), -1)
    first_midrule_idx = next((i for i, line in enumerate(latex_lines) if "\\midrule" in line), -1)

    if first_midrule_idx - first_toprule_idx >= 2 + df.columns.nlevels:
        top_row_line = latex_lines[first_toprule_idx + 1]
        top_row_actual_beginning = 0
        top_row_spaces = 0
        for char in top_row_line:
            if char == "&":
                top_row_spaces += 1
            elif char != " ":
                break
            top_row_actual_beginning += 1

        unneeded_line = latex_lines[first_midrule_idx - 1]
        unneeded_parts = [part.strip() for part in unneeded_line.replace("\\","").split("&") if part.strip()]
        assert len(unneeded_parts) == top_row_spaces, f"Unmatched number of columns: {len(unneeded_parts)} vs {top_row_spaces}"

        top_row_new_parts = [f"\\multirow{{{df.columns.nlevels}}}{{*}}{{{part}}}" for part in unneeded_parts]
        top_row_line = " & ".join(top_row_new_parts) + " & " + top_row_line[top_row_actual_beginning:]
        latex_lines[first_toprule_idx + 1] = top_row_line
        del latex_lines[first_midrule_idx - 1]

    if first_multi_idx == -1:
        return  "\n".join(latex_lines)

    column_rules_indices = []
    current_column_index = df.index.nlevels + 1

    if df.columns.nlevels > 1:
        for parent_column in df.columns.get_level_values(0).unique():
            child_indices = [i for i, code in enumerate(df.columns.codes[0]) if df.columns.levels[0][code] == parent_column]
            parent_column_size = len(child_indices)

            if parent_column_size == 1 and df.columns[child_indices[0]][1] == "":
                col_name = df.columns[child_indices[0]][0]
                new_column_format = f"\\multirow{{{df.columns.nlevels}}}{{*}}{{{col_name}}}"
                latex_lines[first_multi_idx] = latex_lines[first_multi_idx].replace(col_name, new_column_format)
                current_column_index += 1
                continue

            column_rules_indices.append((current_column_index, current_column_index + parent_column_size - 1))
            current_column_index += parent_column_size

        rules_commands_list = [f"\\cmidrule(l){{{i}-{j}}}" for i, j in column_rules_indices]
        rules_command = " ".join(rules_commands_list)

        latex_lines.insert(first_multi_idx + 1, rules_command)

    return "\n".join(latex_lines)


def fix_multi_row(latex: str) -> str:
    # Replace \multirow[t]{4}{*}{foo} with \multirow{4}{*}{\textbf{foo}}
    pattern = r'\\multirow(\[t\])?\{(\d+)\}\{\*\}\{([^\}]*)\}'
    replacement = r'\\multirow{\2}{*}{\\textbf{\3}}'
    latex = re.sub(pattern, replacement, latex)

    # Replace \cline with \midrule
    latex = re.sub(r'\\cline\*?\{[^\}]*\}', r'\\midrule', latex)

    # Replace \cline*\n\bottomrule with \bottomrule
    latex = re.sub(r'\\midrule\*?\n\\bottomrule', r'\\bottomrule', latex)

    return latex


def df_format_ints(df: pd.DataFrame) -> pd.DataFrame:
    return df.applymap(lambda x: f"{x:,}" if isinstance(x, int) else x)


def pd_read_sqlite_query(path: str, query: str, **kwargs) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    df = pd.read_sql_query(query, conn, **kwargs)
    conn.close()

    return df


def df_from_sql_table(connection, table: str, where: str|None=None, params: tuple|None=None) -> pd.DataFrame:
    clause = f"WHERE {where}" if where else ""
    query = f"SELECT * FROM {table} {clause}"
    df = pd.read_sql_query(query, connection, params=params)

    return df


def write_paper_data(content: str, filename: str):
    target_path = os.path.join(os.getenv("PAPER_DATA_DIR"), filename)
    with open(target_path, "w") as f:
        f.write(content)

    print(content)
    print(f"Data written to {target_path}")


def metrics_from_labels(y_true, y_pred, labels=None):
    if labels is None:
        labels = np.unique(np.concatenate([y_true, y_pred]))

    oa = accuracy_score(y_true, y_pred)
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    mp = p.mean()
    mr = r.mean()
    mf1 = f1.mean()

    pw, rw, f1w, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="weighted", zero_division=0
    )

    return {
        "samples": int(len(y_true)),
        "incorrect": int((np.array(y_true) != np.array(y_pred)).sum()),
        "oa": oa * 100,
        "mp": mp * 100, "mr": mr * 100, "mf1": mf1 * 100,
        "wp": pw * 100, "wr": rw * 100, "wf1": f1w * 100,
    }


def compute_metrics(df, true_col, pred_col):
    y_true = df[true_col].to_numpy()
    y_pred = df[pred_col].to_numpy()

    return pd.Series(metrics_from_labels(y_true, y_pred))


def save_point_cloud_visualization(path, points, intensity, cmap='viridis', point_size=0.01, figure_size=(12, 8), elev=30, azim=30, zoom=1.0):
    fig = plt.figure(figsize=figure_size)
    ax = fig.add_subplot(111, projection='3d', facecolor='black')  # Set axes background to black

    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=intensity, cmap=cmap, s=point_size, vmin=0, vmax=1)
    ax.set_axis_off()

    ax.view_init(elev=elev, azim=azim)

    max_range = np.array([points[:, 0].max()-points[:, 0].min(),
                          points[:, 1].max()-points[:, 1].min(),
                          points[:, 2].max()-points[:, 2].min()]).max() / 2.0 / zoom

    mid_x = mid_y = mid_z = 0

    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)

    fig.patch.set_facecolor('black')  # Set figure background to black
    plt.tight_layout(pad=0)  # Reduce padding and margins

    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)


def save_range_image(path, range_image, elevation_range=None, aspect_ratio=None, cmap='nipy_spectral', origin="lower", show_colorbar=True):
    x_range = 2 * np.pi
    x_ticks_count = 9
    y_label = 'Pixel Index (Phi)'

    plt.figure(figsize=(12, 4))

    if elevation_range:
        y_range = elevation_range[1] - elevation_range[0]
        calc_aspect_ratio = (range_image.shape[1] / x_range) / (range_image.shape[0] / y_range)
        aspect_ratio = calc_aspect_ratio if aspect_ratio is None else aspect_ratio
        y_label = 'Phi (Degrees)'

        y_ticks_count = int(32 * y_range / np.pi)
        y_ticks = np.linspace(0, range_image.shape[0] - 1, num=y_ticks_count)
        y_tick_labels = np.linspace(elevation_range[0], elevation_range[1], num=y_ticks_count)

        if origin == "upper":
            y_tick_labels = list(reversed(y_tick_labels))

        plt.yticks(y_ticks, [f"{label:.0f}°" for label in np.rad2deg(y_tick_labels)])

    if aspect_ratio is None:
        aspect_ratio = 10

    plt.ylabel(y_label)
    plt.xlabel('Theta (Degrees)')
    x_ticks = np.linspace(0, range_image.shape[1] - 1, num=x_ticks_count)
    x_tick_labels = np.linspace(0, x_range, num=x_ticks_count)
    plt.xticks(x_ticks, [f"{label:.0f}°" for label in np.rad2deg(x_tick_labels)])

    plt.imshow(range_image, cmap=cmap, interpolation='none', origin=origin, aspect=aspect_ratio)

    if show_colorbar:
        plt.colorbar(label='Range (meters)')

    plt.grid(False)

    plt.savefig(path, bbox_inches='tight')
    plt.tight_layout()
    plt.close()
