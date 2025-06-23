import argparse
import sqlite3

parser = argparse.ArgumentParser(description='Prepare the DB for a new experiment.')
parser.add_argument('db_path', type=str, help='Path to the SQLite database')
parser.add_argument('type', type=str, choices=['intrinsics', 'compression'], help='Type of experiment (intrinsics or compression)')
args = parser.parse_args()

conn = sqlite3.connect(args.db_path)
cur = conn.cursor()

if args.type == 'intrinsics':
    cur.execute("INSERT INTO experiment(timestamp) VALUES (datetime('now', 'localtime', 'subsec'))")
elif args.type == 'compression':
    cur.execute("INSERT INTO compression_experiment(label, description, timestamp) VALUES "
                "('', '',datetime('now', 'localtime', 'subsec'))")
else:
    raise ValueError('Unknown type')

conn.commit()
conn.close()
