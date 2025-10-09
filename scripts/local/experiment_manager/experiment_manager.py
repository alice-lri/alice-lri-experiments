import argparse
from enum import Enum

import paramiko
import os
import re
import time

from dataclasses import dataclass
from dataclasses_json import dataclass_json

#TODO maybe delete this file and put on README
class Config:
    BASE_DIR = """${STORE2}/alice-lri-experiments"""
    STATE_FILE = "state.json"
    SHOW_REMOTE_OUTPUT = False
    DISABLE_RELAUNCH = False
    REMOVE_TARGET_DIR_AFTER_MERGE = False

class JobType(Enum):
    ESTIMATE = "estimate"
    MAIN = "main"

class JobStatus(Enum):
    PENDING = 0
    RUNNING = 1
    FAILED = 2
    COMPLETED = 3

    @staticmethod
    def from_string(string: str):
        if string == "PENDING":
            return JobStatus.PENDING
        elif string == "RUNNING":
            return JobStatus.RUNNING
        elif string == "FAILED":
            return JobStatus.FAILED
        elif string == "COMPLETED":
            return JobStatus.COMPLETED
        else:
            raise ValueError(f"Unknown job status: {string}")

@dataclass
@dataclass_json
class Job:
    slurm_id: int
    index: int
    status: JobStatus
    type: JobType

    def __init__(self, slurm_id: int, index: int, status: JobStatus, type: JobType):
        self.slurm_id = slurm_id
        self.index = index
        self.status = status
        self.type = type


class ExperimentType(Enum):
    INTRINSICS = 1
    RANGE_IMAGE = 2
    COMPRESSION = 3
    GROUND_TRUTH = 4

    @staticmethod
    def from_string(string: str):
        types_map = ExperimentType.types_map()
        if string in ExperimentType.types_map():
            return types_map[string]
        else:
            raise ValueError(f"Unknown experiment type: {string}")

    @staticmethod
    def types_map() -> dict[str, 'ExperimentType']:
        return {
            "intrinsics": ExperimentType.INTRINSICS,
            "range_image": ExperimentType.RANGE_IMAGE,
            "compression": ExperimentType.COMPRESSION,
            "ground_truth": ExperimentType.GROUND_TRUTH,
        }

class ExperimentStatus(Enum):
    PENDING = 0
    ON_QUEUE = 1
    COMPLETED = 2

@dataclass
@dataclass_json
class Experiment:
    id: str
    label: str
    description: str
    type: ExperimentType
    status: ExperimentStatus
    build_options: dict[str, bool]
    jobs: list[Job]

    def __init__(self, id: str = "", label: str = "", description: str = "",
                 type: ExperimentType = ExperimentType.INTRINSICS,
                 status: ExperimentStatus = ExperimentStatus.PENDING,
                 build_options: dict[str, bool] = None, jobs: list[Job] = None):
        self.id = id
        self.label = label
        self.description = description
        self.type = type
        self.status = status
        self.build_options = build_options if build_options is not None else {}
        self.jobs = jobs if jobs is not None else []

@dataclass
@dataclass_json
class State:
    experiments: list[Experiment]

    def __init__(self, experiments: list[Experiment] = None):
        self.experiments = experiments if experiments is not None else []

@dataclass
@dataclass_json
class ExperimentDefinition:
    label: str
    description: str
    type: ExperimentType
    build_options: dict[str, bool] = None

    def __init__(self, label: str, description: str, type: ExperimentType, build_options: dict[str, bool]=None):
        self.label = label
        self.description = description
        self.type = type
        self.build_options = build_options if build_options is not None else {}

@dataclass
@dataclass_json
class ExperimentDefinitionSet:
    experiments: list[ExperimentDefinition]

    def __init__(self, experiments: list[ExperimentDefinition]):
        self.experiments = experiments if experiments is not None else []


class HPCCluster:
    __ssh: paramiko.SSHClient

    def start_connection(self):
        ssh_config = paramiko.SSHConfig()
        with open(os.path.expanduser('~/.ssh/config')) as f:
            ssh_config.parse(f)

        host_alias = 'cesga'
        host_config = ssh_config.lookup(host_alias)

        self.__ssh = paramiko.SSHClient()
        self.__ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.__ssh.connect(
            hostname=host_config['hostname'],
            username=host_config.get('user'),
            port=int(host_config.get('port', 22)),
            key_filename=host_config.get('identityfile', [None])[0],
            look_for_keys=True,
        )

    def end_connection(self):
        self.__ssh.close()

    def launch_experiment(self, experiment: Experiment) -> bool:
        script_dir, script_input = HPCCluster.__get_script_dir_and_input(experiment.type)

        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Config.BASE_DIR, script_dir)} && "
            f"./prepare_and_launch.sh {HPCCluster.__build_options_arg(experiment)}"
        )
        script_input_str = "\n".join(script_input) + "\n"
        stdin.write(script_input_str)
        stdin.flush()

        experiment.jobs = []
        job_index = 0 if experiment.type in [ExperimentType.INTRINSICS, ExperimentType.GROUND_TRUTH] else -1
        for line in iter(stdout.readline, ''):
            if Config.SHOW_REMOTE_OUTPUT:
                print(line, end="")

            batch_id_match = re.search(r"Batch ID: (\w+)", line)
            if batch_id_match:
                experiment.id = batch_id_match.group(1)

            job_id_match = re.search(r"Submitted batch job (\d+)", line)
            if job_id_match:
                job_type = JobType.ESTIMATE if job_index < 0 else JobType.MAIN
                experiment.jobs.append(Job(slurm_id=int(job_id_match.group(1)), index=job_index,
                                           status=JobStatus.PENDING, type=job_type))
                job_index += 1

        experiment.status = ExperimentStatus.ON_QUEUE
        return stdout.channel.recv_exit_status() == 0

    def relaunch_jobs(self, experiment: Experiment, job_indices: list[int], skip_estimation: bool) -> list[str]:
        script_dir, script_input = HPCCluster.__get_script_dir_and_input(experiment.type)

        job_indices_str = " ".join(map(str, job_indices))
        skip_estimation_arg = "--skip-estimation" if skip_estimation else ""
        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Config.BASE_DIR, script_dir)} && "
            f"./prepare_and_launch.sh "
            f"--relaunch {experiment.id} {job_indices_str} "
            f"--skip-build {skip_estimation_arg} "
            f"{HPCCluster.__build_options_arg(experiment)}"
        )

        script_input_str = "\n".join(script_input) + "\n"
        stdin.write(script_input_str)
        stdin.flush()

        new_slurm_ids = []
        for line in iter(stdout.readline, ''):
            if Config.SHOW_REMOTE_OUTPUT:
                print(line, end="")

            job_id_match = re.search(r"Submitted batch job (\d+)", line)
            if job_id_match:
                new_slurm_ids.append(int(job_id_match.group(1)))

        return new_slurm_ids

    def merge_experiment(self, experiment: Experiment) -> bool:
        script_inputs = [str(experiment.type.value), experiment.label, experiment.description]
        script_input_str = "\n".join(script_inputs) + "\n"
        remove_target_arg = "--remove-target-dir" if Config.REMOVE_TARGET_DIR_AFTER_MERGE else ""
        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Config.BASE_DIR, "scripts/merge")} && "
            f"./merge_db.sh --target-dir {experiment.id} {remove_target_arg}"
        )

        stdin.write(script_input_str)
        stdin.flush()

        for line in iter(stdout.readline, ''):
            if Config.SHOW_REMOTE_OUTPUT:
                print(line, end="")

        return stdout.channel.recv_exit_status() == 0

    def job_status_by_id(self, job_id: int) -> JobStatus | None:
        stdin, stdout, stderr = self.__ssh.exec_command(f"sacct -n -X -P -j {job_id} --format=State")
        status_str = stdout.read().decode().strip()

        try:
            return JobStatus.from_string(status_str)
        except ValueError:
            return None

    @staticmethod
    def __build_options_arg(experiment: Experiment) -> str:
        build_options_str = ""
        if experiment.build_options:
            build_options_str = " ".join(f"{key}={'ON' if value else 'OFF'}" for key, value in experiment.build_options.items())
            build_options_str = f"--build-options {build_options_str}"

        return build_options_str

    @staticmethod
    def __get_script_dir_and_input(experiment_type: ExperimentType) -> tuple[str, list[str]]:
        if experiment_type == ExperimentType.INTRINSICS:
            script_dir = "scripts/slurm/intrinsics"
            script_input = ["y"]
        elif experiment_type == ExperimentType.GROUND_TRUTH:
            script_dir = "scripts/slurm/ground_truth"
            script_input = ["y"]
        else:
            script_dir = "scripts/slurm/ri_compression"
            script_input = ["y", str(experiment_type.value - 1)]

        return script_dir, script_input


class Manager:
    __state: State
    __cluster: HPCCluster

    def __init__(self, state: State):
        self.__state = state
        self.__cluster = HPCCluster()

    def tick(self):
        print("Tick!")
        if len(self.__state.experiments) == 0:
            print("No experiments to process.")
            return
        else:
            print(f"{len(self.__state.experiments)} experiments remaining.")

        self.__cluster.start_connection()

        experiment = self.__state.experiments[0]

        if experiment.status == ExperimentStatus.PENDING:
            self.__launch_experiment(experiment)
            return

        finished_now = False
        if experiment.status == ExperimentStatus.ON_QUEUE:
            finished_now = self.__monitor_experiment(experiment)
        if experiment.status == ExperimentStatus.COMPLETED or finished_now:
            self.__merge_experiment(experiment)
            self.__state.experiments.pop(0)

        self.__cluster.end_connection()

    def __launch_experiment(self, experiment: Experiment):
        print(f"Launching experiment: {experiment.label}")
        success = self.__cluster.launch_experiment(experiment)

        if not success:
            raise RuntimeError(f"Failed to launch experiment: {experiment.label}")

        print(f"Launched Batch ID: {experiment.id}")
        print("Jobs:")

        for job in experiment.jobs:
            print(f"  - Job {job.index}: SLURM ID {job.slurm_id}")

    def __monitor_experiment(self, experiment: Experiment) -> bool:
        jobs_to_relaunch = []
        skip_estimation = True
        for job in experiment.jobs:
            if job.status == JobStatus.COMPLETED:
                continue

            new_status = self.__cluster.job_status_by_id(job.slurm_id)
            if new_status:
                job.status = new_status

            if job.status == JobStatus.RUNNING:
                print(f"Job {job.slurm_id} ({job.index}) is currently running.")
            elif job.status == JobStatus.COMPLETED:
                print(f"Job {job.slurm_id} ({job.index}) completed successfully.")
            elif job.status == JobStatus.FAILED:
                print(f"Job {job.slurm_id} ({job.index}) failed.")

                if job.type == JobType.ESTIMATE:
                    jobs_to_relaunch = [] + experiment.jobs
                    skip_estimation = False
                    break
                else:
                    jobs_to_relaunch.append(job)

        if len(jobs_to_relaunch) > 0 and not Config.DISABLE_RELAUNCH:
            indices_to_relaunch = [job.index for job in jobs_to_relaunch]
            print(f"Will relaunch the following jobs: {indices_to_relaunch}")
            new_slurm_ids = self.__cluster.relaunch_jobs(experiment, indices_to_relaunch, skip_estimation)

            for job, new_slurm_id in zip(jobs_to_relaunch, new_slurm_ids):
                print(f"Relaunched job {job.index} with new SLURM ID: {new_slurm_id}")
                job.slurm_id = new_slurm_id
                job.status = JobStatus.PENDING

        if all(job.status == JobStatus.COMPLETED for job in experiment.jobs):
            experiment.status = ExperimentStatus.COMPLETED
            print(f"Experiment {experiment.label} completed successfully.")
            return True

        return False

    def __merge_experiment(self, experiment: Experiment):
        print(f"Merging experiment: {experiment.label}")
        success = self.__cluster.merge_experiment(experiment)

        if not success:
            raise RuntimeError(f"Failed to merge experiment: {experiment.label}")


def load_state() -> State:
    if not os.path.exists(Config.STATE_FILE):
        raise FileNotFoundError(f"{Config.STATE_FILE} not found")

    with open(Config.STATE_FILE, "r") as f:
        return State.from_json(f.read())


def load_definition_file(definition_file: str) -> ExperimentDefinitionSet:
    if not os.path.exists(definition_file):
        raise FileNotFoundError(f"{definition_file} not found")

    with open(definition_file, "r") as f:
        return ExperimentDefinitionSet.from_json(f.read())


def load_state_from_args(args: argparse.Namespace, experiment: Experiment):
    experiment.label = args.name
    experiment.description = args.description
    experiment.type = ExperimentType.from_string(args.type)
    experiment.status = ExperimentStatus.PENDING
    experiment.build_options = {}

    if args.build_options:
        build_opts = args.build_options.split()
        for opt in build_opts:
            key, value = opt.split("=", 1)
            experiment.build_options[key] = (value.upper() == "ON")

    return State(experiments=[experiment])


def load_state_from_definition(definition: ExperimentDefinitionSet):
    experiments = []
    for defn in definition.experiments:
        experiment = Experiment(
            id="",
            label=defn.label,
            description=defn.description,
            type=defn.type,
            status=ExperimentStatus.PENDING,
            build_options=defn.build_options.copy() if defn.build_options else {},
            jobs=[]
        )
        experiments.append(experiment)

    return State(experiments=experiments)


def parse_args() -> State:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["launch", "monitor"])
    parser.add_argument("--type", type=str, choices=ExperimentType.types_map().keys())
    parser.add_argument("--build-options", type=str, help="Build options string (e.g., '-Dflag1=ON -Dflag2=OFF')")
    parser.add_argument("--name", type=str)
    parser.add_argument("--description", type=str)
    parser.add_argument("--definition-file", type=str)
    parser.add_argument("--show-remote-output", action="store_true")
    parser.add_argument("--disable-relaunch", action="store_true")
    parser.add_argument("--remove-target-dir-after-merge", action="store_true")

    args = parser.parse_args()
    experiment = Experiment()

    Config.SHOW_REMOTE_OUTPUT = args.show_remote_output
    Config.DISABLE_RELAUNCH = args.disable_relaunch
    Config.REMOVE_TARGET_DIR_AFTER_MERGE = args.remove_target_dir_after_merge

    if args.mode == "launch":
        if args.definition_file:
            state = load_state_from_definition(load_definition_file(args.definition_file))
            print(f"Loaded {len(state.experiments)} experiments from definition file.")
        else:
            state = load_state_from_args(args, experiment)
    elif args.mode == "monitor":
        state = load_state()
    else:
        raise ValueError("Unsupported mode")

    return state


def save_state(state: State):
    with open(Config.STATE_FILE, "w") as f:
        f.write(state.to_json(indent=4))


def main():
    state = parse_args()
    manager = Manager(state)
    save_state(state)

    while True:
        manager.tick()
        save_state(state)
        time.sleep(1 * 60)

if __name__ == "__main__":
    main()
