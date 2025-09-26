import argparse

from scripts.common.helper.entities import *
from scripts.common.helper.orm import Database


def main():
    parser = argparse.ArgumentParser(description='Prepare the DB for a new experiment.')
    parser.add_argument('db_path', type=str, help='Path to the SQLite database')
    parser.add_argument('type', type=str, choices=['intrinsics', 'compression', 'ri'],
                        help='Type of experiment (intrinsics, ri, or compression)')
    parser.add_argument("--build-options", type=str, help="Build options string (e.g., '-Dflag1=ON -Dflag2=OFF')")
    args = parser.parse_args()

    with Database(args.db_path) as db:
        if args.type == 'intrinsics':
            build_options = {
                "use_hough_continuity": True,
                "use_scanline_conflict_solver": True,
                "use_vertical_heuristics": True,
                "use_horizontal_heuristics": True
            }

            if args.build_options:
                input_build_options = args.build_options.split()
                for option in input_build_options:
                    key, value = option.split("=", 1)
                    mapped_key = key.lower().replace('-dflag_', '')
                    build_options[mapped_key] = (value.upper() == "ON")

            experiment = IntrinsicsExperiment(
                label="",
                description="",
                timestamp=SQLExpr("datetime('now', 'localtime', 'subsec')"),
                use_hough_continuity=build_options['use_hough_continuity'],
                use_scanline_conflict_solver=build_options['use_scanline_conflict_solver'],
                use_vertical_heuristics=build_options['use_vertical_heuristics'],
                use_horizontal_heuristics=build_options['use_horizontal_heuristics']
            )

            experiment.save(db)
        elif args.type == 'compression':
            experiment = CompressionExperiment(
                label="",
                description="",
                timestamp=SQLExpr("datetime('now', 'localtime', 'subsec')")
            )
            experiment.save(db)
        elif args.type == 'ri':
            experiment = RangeImageExperiment(
                label="",
                description="",
                timestamp=SQLExpr("datetime('now', 'localtime', 'subsec')")
            )
            experiment.save(db)
        else:
            raise ValueError('Unknown type')


if __name__ == "__main__":
    main()
