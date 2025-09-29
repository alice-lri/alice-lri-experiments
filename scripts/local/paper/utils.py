import os
import re
import pandas as pd

class __Config:
    data_path = "output/data/"
    figures_path = "output/figures/"


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


def write_paper_data(latex: str, filename: str):
    target_path = os.path.join(__Config.data_path, filename)
    with open(target_path, "w") as f:
        f.write(latex)

    print(latex)
    print(f"Data written to {target_path}")
