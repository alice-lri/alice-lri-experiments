from scripts.common.helper.entities import IntrinsicsExperiment, RangeImageExperiment, CompressionExperiment
from scripts.common.helper.orm import Database
from scripts.local.paper.helper.utils import pd_read_sqlite_query


def fetch_main_experiment_id(db_path: str) -> int:
    with Database(db_path) as db:
        experiments = IntrinsicsExperiment.all(db)
        experiments = [exp for exp in experiments if exp.all_flags_enabled()]

        assert(len(experiments) == 1), f"Expected exactly one experiment with all flags enabled, got {len(experiments)}"

        return experiments[0].id


def fetch_ri_experiment_id(db_path: str) -> int:
    with Database(db_path) as db:
        experiments = RangeImageExperiment.all(db)
        assert len(experiments) == 1, f"Expected exactly one experiment, got {len(experiments)}"
        return experiments[0].id


def fetch_compression_experiment_id(db_path: str) -> int:
    with Database(db_path) as db:
        experiments = CompressionExperiment.all(db)
        assert len(experiments) == 1, f"Expected exactly one experiment, got {len(experiments)}"
        return experiments[0].id
