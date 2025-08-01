import argparse
from enum import Enum

import paramiko
import os

class Constant:
    BASE_DIR = """${STORE2}/accurate-ri-hpc"""

class JobStatus(Enum):
    PENDING = 0
    RUNNING = 1
    FAILED = 2
    COMPLETED = 3

class Job:
    index: int
    status: JobStatus

class ExperimentType(Enum):
    INTRINSICS = 1
    RANGE_IMAGE = 2
    COMPRESSION = 3

    @staticmethod
    def from_string(string: str):
        if string == "intrinsics":
            return ExperimentType.INTRINSICS
        elif string == "range_image":
            return ExperimentType.RANGE_IMAGE
        elif string == "compression":
            return ExperimentType.COMPRESSION
        else:
            raise ValueError(f"Unknown experiment type: {string}")

class ExperimentStatus(Enum):
    PENDING = 0
    RUNNING = 1
    COMPLETED = 2

class Experiment:
    id: str
    name: str
    description: str
    type: ExperimentType
    status: ExperimentStatus
    jobs: list[Job]

class State:
    experiments: list[Experiment]

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

    def launch_experiment(self, experiment_type: ExperimentType) -> bool:
        if experiment_type == ExperimentType.INTRINSICS:
            script_dir = "slurm/estimate"
        else:
            raise ValueError(f"Unsupported experiment type: {experiment_type}")

        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Constant.BASE_DIR, script_dir)} && yes 'n' | ./prepare_and_launch.sh"
        )

        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.readline()
                print(line, end="")

        return stdout.channel.recv_exit_status() == 0


class Manager:
    __state: State
    __cluster: HPCCluster

    def __init__(self, state: State):
        self.__state = state
        self.__cluster = HPCCluster()

    def tick(self):
        if len(self.__state.experiments) == 0:
            return

        self.__cluster.start_connection()

        do_tick = True
        experiment = self.__state.experiments[0]

        while do_tick:
            do_tick = False
            if experiment.status == ExperimentStatus.PENDING:
                self.__launch_experiment(experiment)
            if experiment.status == ExperimentStatus.RUNNING:
                do_tick = self.__monitor_experiment(experiment)
            if experiment.status == ExperimentStatus.COMPLETED or do_tick:
                self.__merge_experiment(experiment)
                self.__state.experiments.pop(0)

        self.__cluster.end_connection()

    def __launch_experiment(self, experiment: Experiment):
        print(f"Launching experiment: {experiment.name}")
        success = self.__cluster.launch_experiment(experiment.type)

        if not success:
            raise RuntimeError(f"Failed to launch experiment: {experiment.name}")

    def __monitor_experiment(self, experiment: Experiment):
        pass

    def __merge_experiment(self, experiment: Experiment):
        pass


def parse_args() -> State:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["launch", "monitor"])
    parser.add_argument("--type", type=str, choices=["intrinsics", "range_image", "compression"])
    parser.add_argument("--name", type=str)
    parser.add_argument("--description", type=str)

    args = parser.parse_args()
    experiment = Experiment()
    state = State()

    if args.mode == "launch":
        experiment.name = args.name
        experiment.description = args.description
        experiment.type = ExperimentType.from_string(args.type)
        experiment.status = ExperimentStatus.PENDING

        state.experiments = [experiment]
    else:
        raise ValueError("Unsupported mode")

    return state

def main():
    state = parse_args()
    manager = Manager(state)

    manager.tick()

if __name__ == "__main__":
    main()