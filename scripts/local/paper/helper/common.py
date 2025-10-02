from scripts.local.paper.helper.utils import pd_read_sqlite_query


def fetch_main_experiment_id(db_path: str) -> int:
    query = """
            SELECT id FROM experiment
            WHERE use_hough_continuity AND use_scanline_conflict_solver
              AND use_vertical_heuristics AND use_horizontal_heuristics \
            """

    df = pd_read_sqlite_query(db_path, query)
    assert len(df) == 1, f"Expected exactly one experiment, got {len(df)}"

    return int(df.iloc[0]["id"])
