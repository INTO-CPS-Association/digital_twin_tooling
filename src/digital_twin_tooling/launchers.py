import subprocess
from pathlib import Path
from abc import ABC, abstractmethod
import shutil
import stat
import sys
import os
import yaml
import glob
import psutil


class TaskLauncher(ABC):
    @abstractmethod
    def launch(self, job_dir, task_conf) -> int:
        pass

    def launch_redirect_to_log(self, job_dir, name, cmds):
        wrapper_name = (name + '.sh')
        wrap_file_path = job_dir / wrapper_name

        with open(wrap_file_path, 'w') as wrapper:
            wrapper.write('#!/bin/bash\n')
            wrapper.write(" ".join(cmds))
            wrapper.write(" > " + name + ".log 2>&1\n")
            wrapper.flush()

        st = os.stat(str(wrap_file_path))
        os.chmod(str(wrap_file_path), st.st_mode | stat.S_IEXEC)

        p = subprocess.Popen(str(wrap_file_path.absolute()), cwd=job_dir)
        print("Process started with pid: %d" % p.pid)
        return p.pid


class MaestroProcessLauncher(TaskLauncher):

    def __init__(self, jar_path) -> None:
        self.maestro_jar = jar_path

    def launch(self, job_dir, task_conf) -> int:
        java_path = shutil.which('java')
        # maestro_args = 'interpret -runtime {0} -output {1} --no-expand {2}'.format(
        #     task_conf['spec_runtime'], ".", task_conf['spec'])

        cmd = [str(java_path), '-jar', str(self.maestro_jar), 'interpret', '-runtime',
               str(task_conf['spec_runtime']),
               '-output', ".",
               '--no-expand', str(task_conf['spec'])]

        if 'execution' in task_conf and 'capture_output' in task_conf['execution'] and \
                task_conf['execution']['capture_output']:
            return self.launch_redirect_to_log(job_dir, "maestro_launcher", cmd)

        p = subprocess.Popen(cmd, cwd=job_dir)
        print("Process started with pid: %d" % p.pid)
        return p.pid
        # try:
        #     outs, errs = p.communicate(timeout=15)
        #     print(outs)
        #     print(errs)
        # except subprocess.TimeoutExpired:
        #     p.kill()
        #     outs, errs = p.communicate()
        #     print(outs)
        #     print(errs)


class AmqpProviderProcessLauncher(TaskLauncher):
    def launch(self, job_dir, task_conf) -> int:
        print(sys.executable)
        path = "amqp-launch.yml"
        with open(job_dir / path, 'w') as f:
            f.write(yaml.dump(task_conf))

        script = (Path(__file__).parent.resolve() / 'amqp_data_repeater.py').absolute()
        cmd = [sys.executable, str(script), '--config', str(path), '--log=DEBUG']
        print(cmd)

        if 'execution' in task_conf and 'capture_output' in task_conf['execution'] and \
                task_conf['execution']['capture_output']:
            return self.launch_redirect_to_log(job_dir, "qmqp_repeater_launcher", cmd)

        p = subprocess.Popen(cmd, cwd=job_dir)
        print("Process started with pid: %d" % p.pid)
        try:
            outs, errs = p.communicate(timeout=15)
            print(outs)
            print(errs)
        except subprocess.TimeoutExpired:
            p.kill()
            outs, errs = p.communicate()
            print(outs)
            print(errs)
        return p.pid


def check_launcher_status(scan_directory):
    pid_files = glob.glob(str(scan_directory) + '/*.pid')
    # print(pid_files)
    for path in pid_files:
        try:
            with open(path, 'r') as file:
                pid = int(file.read())
            if not psutil.pid_exists(pid):
                Path(path).unlink()
            else:
                print(Path(path).name + ' -- RUNNING')
        except ValueError:
            Path(path).unlink()


def terminate_all_launcher(scan_directory):
    pid_files = glob.glob(str(scan_directory) + '/*.pid')
    for path in pid_files:
        with open(path, 'r') as file:
            pid = int(file.read())
        if psutil.pid_exists(pid):
            p = psutil.Process(pid)
            print(Path(path).name + ' -- Signaling Terminate')
            p.terminal()  # p.kill()
    check_launcher_status(scan_directory)


def check_launcher_pid_status(path):
    try:
        with open(path, 'r') as file:
            pid = int(file.read())
        if not psutil.pid_exists(pid):
            Path(path).unlink()
        else:
            return True
    except ValueError:
        Path(path).unlink()
    return False


def configure_arguments_parser(parser):
    parser.add_argument("-work", "--working-path", dest="work", type=str, required=True,
                        help='Path to a working directory')
    parser.add_argument('-s', '--show', dest='show', action='store_true', help='Show the running launchers')


def process_cli_arguments(args):
    if args.show:
        check_launcher_status(args.work)
    else:
        pid_files = glob.glob(str(args.work) + '/*.pid')
        for f in pid_files:
            check_launcher_pid_status(f)

    # pid_files = glob.glob(str(args.work / 'jobs') + '/**/*.pid')
    # print(pid_files)
    # for path in pid_files:
    #     try:
    #         with open(path, 'r') as file:
    #             pid = int(file.read())
    #         if not psutil.pid_exists(pid):
    #             Path(path).unlink()
    #     except ValueError:
    #         Path(path).unlink()
