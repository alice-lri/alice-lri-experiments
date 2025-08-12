import argparse
import sqlite3

parser = argparse.ArgumentParser(description='Prepare the DB for a new experiment.')
parser.add_argument('db_path', type=str, help='Path to the SQLite database')
parser.add_argument('type', type=str, choices=['intrinsics', 'compression'], help='Type of experiment (intrinsics or compression)')
parser.add_argument("--build-options", type=str, nargs="*")
args = parser.parse_args()

conn = sqlite3.connect(args.db_path)
cur = conn.cursor()

if args.type == 'intrinsics':
    build_options = {
        "use_hough_continuity": True,
        "use_scanline_conflict_solver": True,
        "use_vertical_heuristics": True,
        "use_horizontal_heuristics": True
    }
    input_build_options = {
        key: (value.upper() == "ON")
        for key, value in (opt.split("=", 1) for opt in (args.build_options or []))
    }

    for key, value in input_build_options.items():
        mapped_key = key.lower().replace('-dflag', '')
        build_options[mapped_key] = value

    cur.execute("""
        INSERT INTO experiment(timestamp, use_hough_continuity, use_scanline_conflict_solver, 
                               use_vertical_heuristics, use_horizontal_heuristics)
        VALUES (datetime('now', 'localtime', 'subsec'), ?, ?, ?, ?)""",
        (build_options['use_hough_continuity'], build_options['use_scanline_conflict_solver'],
         build_options['use_vertical_heuristics'], build_options['use_horizontal_heuristics'])
    )
elif args.type == 'compression':
    cur.execute("INSERT INTO compression_experiment(label, description, timestamp) VALUES "
                "('', '',datetime('now', 'localtime', 'subsec'))")
elif args.type == 'ri':
    cur.execute("INSERT INTO ri_experiment(label, description, timestamp) VALUES "
                "('', '',datetime('now', 'localtime', 'subsec'))")
else:
    raise ValueError('Unknown type')

conn.commit()
conn.close()
