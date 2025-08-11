import argparse
from enum import Enum

import paramiko
import os
import re


class Constant:
    BASE_DIR = """${STORE2}/accurate-ri-hpc"""

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

class Job:
    slurm_id: int
    index: int
    status: JobStatus

    def __init__(self, slurm_id: int, index: int, status: JobStatus):
        self.slurm_id = slurm_id
        self.index = index
        self.status = status


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
    ON_QUEUE = 1
    COMPLETED = 2

class Experiment:
    id: str
    label: str
    description: str
    type: ExperimentType
    status: ExperimentStatus
    build_options: dict[str, bool]
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

    def launch_experiment(self, experiment: Experiment) -> bool:
        if experiment.type == ExperimentType.INTRINSICS:
            script_dir = "slurm/estimate"
        else: #TODO
            raise ValueError(f"Unsupported experiment type: {experiment.type}")

        build_options = " ".join(f"{key}={'ON' if value else 'OFF'}" for key, value in experiment.build_options.items())
        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Constant.BASE_DIR, script_dir)} && "
            f"yes | ./prepare_and_launch.sh --build-options {build_options}"
        )

        experiment.jobs = []
        job_index = 0
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.readline()
                print(line, end="")

                batch_id_match = re.search(r"Batch ID: (\w)", line)
                if batch_id_match:
                    experiment.id = batch_id_match.group(1)

                job_id_match = re.search(r"Submitted batch job (\d+)", line)
                if job_id_match:
                    experiment.jobs.append(Job(slurm_id=int(job_id_match.group(1)), index=job_index, status=JobStatus.PENDING))
                    job_index += 1

        experiment.status = ExperimentStatus.ON_QUEUE
        return stdout.channel.recv_exit_status() == 0

    def relaunch_jobs(self, experiment_type: ExperimentType, experiment_id: str, job_indices: list[int]) -> list[str]:
        if experiment_type == ExperimentType.INTRINSICS:
            script_dir = "slurm/estimate"
        else: #TODO
            raise ValueError(f"Unsupported experiment type: {experiment_type}")

        job_indices_str = " ".join(map(str, job_indices))
        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Constant.BASE_DIR, script_dir)} && "
            f"yes | ./prepare_and_launch.sh --relaunch {experiment_id} {job_indices_str}"
        )

        new_slurm_ids = []
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.readline()
                print(line, end="")

                job_id_match = re.search(r"Submitted batch job (\d+)", line)
                if job_id_match:
                    new_slurm_ids.append(int(job_id_match.group(1)))

        return new_slurm_ids

    def merge_experiment(self, experiment: Experiment) -> bool:
        script_inputs = [str(experiment.type), experiment.label, experiment.description]
        script_input_str = "\n".join(script_inputs)
        stdin, stdout, stderr = self.__ssh.exec_command(
            f"cd {os.path.join(Constant.BASE_DIR, "merge")} && echo {script_input_str} | ./merge_experiments_db.sh {experiment.id}"
        )

        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.readline()
                print(line, end="")

        return stdout.channel.recv_exit_status() == 0

    def job_status_by_id(self, job_id: int) -> JobStatus:
        stdin, stdout, stderr = self.__ssh.exec_command(f"sacct -n -X -P -j {job_id} --format=State")
        status_str = stdout.read().decode().strip()

        return JobStatus.from_string(status_str)


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

        experiment = self.__state.experiments[0]

        if experiment.status == ExperimentStatus.PENDING:
            self.__launch_experiment(experiment)

        finished_now = True
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

    def __monitor_experiment(self, experiment: Experiment) -> bool:
        jobs_to_relaunch = []
        for job in experiment.jobs:
            if job.status == JobStatus.COMPLETED:
                continue

            if job.status == JobStatus.FAILED:
                raise RuntimeError(f"Failed job: {job.slurm_id}")

            job.status = self.__cluster.job_status_by_id(job.slurm_id)

            if job.status == JobStatus.RUNNING:
                print(f"Job {job.index} is currently running.")
            elif job.status == JobStatus.COMPLETED:
                print(f"Job {job.index} completed successfully.")
            elif job.status == JobStatus.FAILED:
                jobs_to_relaunch.append(job)

        if len(jobs_to_relaunch) > 0:
            print(f"Will relaunch the following jobs: {jobs_to_relaunch}")
            new_slurm_ids = self.__cluster\
                .relaunch_jobs(experiment.type, experiment.id, [job.index for job in jobs_to_relaunch])

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


def parse_args() -> State:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["launch", "monitor"])
    parser.add_argument("--type", type=str, choices=["intrinsics", "range_image", "compression"])
    parser.add_argument("--build-options", type=str, nargs="*")
    parser.add_argument("--name", type=str)
    parser.add_argument("--description", type=str)

    args = parser.parse_args()
    experiment = Experiment()
    state = State()

    if args.mode == "launch":
        experiment.label = args.name
        experiment.description = args.description
        experiment.type = ExperimentType.from_string(args.type)
        experiment.status = ExperimentStatus.PENDING
        experiment.build_options = {
            key: (value.upper() == "ON")
            for key, value in (opt.split("=", 1) for opt in (args.build_options or []))
        }

        state.experiments = [experiment]
    else:
        raise ValueError("Unsupported mode")

    return state

def main():
    state = parse_args()
    manager = Manager(state)

    manager.tick()
    #todo save state

if __name__ == "__main__":
    main()