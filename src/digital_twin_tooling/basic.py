import json
import yaml
from .rabbitmq_fmu import create_fmu_with_outputs
import subprocess
import tempfile
from pathlib import Path
import uuid
import os
import glob
import psutil
import copy
from jsonschema import validate as yml_validate
import pkg_resources
from .launchers import MaestroProcessLauncher, AmqpProviderProcessLauncher
import argparse


def validate(conf):
    # with open(Path(__file__).parent / 'schema-0.0.1.yml', 'r') as sf:
    with pkg_resources.resource_stream(__name__, 'data/schema-0.0.1.yml') as stream:
        # with open(Path(project_path) / file, mode='wb', buffering=0) as f:
        # f.write(stream.read())
        schema = yaml.load(stream, Loader=yaml.FullLoader)
        yml_validate(conf, schema)


def show(conf):
    if 'servers' in conf:
        print('## Servers ##')
        for s in conf['servers']:
            print("Server:\n\tid: %s\n\ttype:%s\n\tembedded: %s" % (s['id'], s['type'], 'embedded' in s))


def run(conf, run_index, job_dir):
    validate(conf)
    print('''###############################################################
    
    Running from ''' + str(job_dir) + '''
    
###############################################################''')

    task_providers = {'simulation_maestro': MaestroProcessLauncher(Path(conf['tools']['maestro']['path']).absolute()),
                      'data-repeater_AMQP-AMQP': AmqpProviderProcessLauncher()}

    if 'configurations' in conf:
        config = conf['configurations'][run_index]
        print("Running: '%s'" % config['name'])
        for idx, task in enumerate(config['tasks']):

            print("State %d: %s" % (idx, task['type']))

            if 'execution' in task and 'skip' in task['execution'] and task['execution']['skip']:
                print('Skipping launch of %d: %s' % (idx, task['type']))
                continue

            identifier = "{0}_{1}".format(task['type'], task['implementation'])
            if identifier not in task_providers:
                raise "No launcher for task id: %s" % identifier

            task_launcher = task_providers[identifier]
            pid = task_launcher.launch(job_dir, task)
            with open(job_dir / (identifier + '.pid'), 'w') as f:
                f.write(str(pid))


def flatten(t):
    return [item for sublist in t for item in sublist]


def prepare(conf, run_index, job_id, job_dir, fmu_dir):
    # validate sections
    validate(conf)

    # start all one at the time
    if 'configurations' in conf:
        config = conf['configurations'][run_index]
        print("Running: '%s'" % config['name'])

        current_job_id = job_id
        # check if the job has a fixed job id
        if 'fixed_job_id' in config:
            current_job_id = config['fixed_job_id']

        for idx, task in enumerate(config['tasks']):

            print("State %d: %s" % (idx, task['type']))

            if 'simulation' in task['type']:
                # we need to generate rabbitmq fmu with the right signals
                if 'spec' in task and 'spec_runtime' in task:
                    # already processed
                    del task['config']
                    continue
                signals = flatten([([(s, t['signals'][s]['target']['datatype']) for s in (t['signals'].keys()) if
                                     'target' in t['signals'][s] and 'datatype' in t['signals'][s]['target']]) for
                                   t in config['tasks'] if t['type'] == 'data-repeater'])
                # flatten([list(t['signals'].keys()) for t in config['tasks'] if t['type'] == 'data-repeater'])
                dest = task['config']['fmus']['{amqp}']
                print("\tCreating AMQP instance with the required signals")
                create_fmu_with_outputs(
                    Path(conf['tools']['rabbitmq']['path']).absolute(), Path(fmu_dir) / Path(dest).name,
                    signals)
                # configure AMQP exchange
                task['config']['parameters']['{amqp}.ext.config.routingkey'] = current_job_id
                task['config']['parameters']['{amqp}.ext.config.exchangename'] = 'fmi_digital_twin'
                task['config']['parameters']['{amqp}.ext.config.exchangetype'] = 'direct'
                for server in conf['servers']:
                    if 'embedded' in server and server['embedded'] and server['type'] == 'AMQP':
                        task['config']['parameters']['{amqp}.ext.config.hostname'] = server['host']
                        task['config']['parameters']['{amqp}.ext.config.port'] = int(server['port'])
                        task['config']['parameters']['{amqp}.ext.config.username'] = server['user']
                        task['config']['parameters']['{amqp}.ext.config.password'] = server['password']
                        break

                print("\tImporting into Maestro for spec generating")
                with tempfile.NamedTemporaryFile(suffix='.json') as fp:
                    fp.write(json.dumps(task['config']).encode('utf-8'))
                    fp.flush()
                    cmd = "java -jar {0} import -vi FMI2   sg1 {1} -output {2} --fmu-base-dir {3}".format(
                        Path(conf['tools']['maestro']['path']).absolute(),
                        fp.name,
                        "specs", fmu_dir)
                    print(cmd)
                    subprocess.run(cmd, shell=True, check=True, cwd=job_dir)
                    task['spec'] = str(Path('specs') / 'spec.mabl')
                    task['spec_runtime'] = str(Path('specs') / 'spec.runtime.json')
                    del task['config']
            if 'data-repeater' in task['type'] and 'AMQP-AMQP' in task['implementation']:
                for signal in task['signals'].keys():
                    # including HACK for wired naming implicit to the rabbitmq fmu
                    task['signals'][signal]['target']['exchange'] = 'fmi_digital_twin'  # + '_cd'
                    task['signals'][signal]['target']['routing_key'] = current_job_id  # + '.data.to_cosim'
                for server in task['servers']:
                    task['servers'][server] = copy.deepcopy(
                        [s for s in conf['servers'] if s['id'] == task['servers'][server]][0])
                    del task['servers'][server]['id']
                    del task['servers'][server]['name']
                    del task['servers'][server]['type']


def configure_arguments_parser(parser):
    parser.add_argument("-project", "--project-path", dest="project", type=str, required=True,
                        help='Path to the project *.yml file')
    # options.add_argument("-project", "--project-path", dest="project", type=str, required=False,
    #                      help='Path to the project root containing the .env')
    parser.add_argument("-work", "--working-path", dest="work", type=str, required=False,
                        help='Optional path to a working directory')
    parser.add_argument("-fmus", "--fmu-dir-path", dest="fmus", type=str, required=False,
                        help='Optional path to a working directory')
    parser.add_argument("-run", "--run-index", dest="run_index", type=int, required=False,
                        help='The index of the simulation to run')
    # options.add_argument("-reload", "--reload-pipe", dest="reload", type=bool, required=False,
    #                      help='If the pipeline should be reloaded instead of configured')
    parser.add_argument("-show", "--show", required=False, help='Show the pipeline', action="store_true")


def process_cli_arguments(args):
    configuration_file = args.project  # '/Users/kgl/data/au/into-cps-association/digital-twin-platform/src/dtpt/basic.yml'

    # rabbitmq_fmu_path = '/Users/kgl/data/au/into-cps-association/digital-twin-platform/src/dtpt/rabbitmq.fmu'
    # maestro_jar = '/Users/kgl/data/au/into-cps-association/maestro/maestro/target/maestro-2.1.6-SNAPSHOT-jar-with-dependencies.jar'

    job_id = str(uuid.uuid4())

    if args.work:
        job_dir = args.work
    else:
        job_dir = Path(os.curdir) / 'jobs' / job_id
        os.makedirs(job_dir, exist_ok=True)
    # project_dir = Path(__file__).parent.resolve()

    # bookkeeping
    # pid_files = glob.glob(str(project_dir / 'jobs') + '/**/*.pid')
    # print(pid_files)
    # for path in pid_files:
    #     try:
    #         with open(path, 'r') as file:
    #             pid = int(file.read())
    #         if not psutil.pid_exists(pid):
    #             Path(path).unlink()
    #     except ValueError:
    #         Path(path).unlink()

    with open(configuration_file, 'r') as f:
        try:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            if args.show:
                # show(conf)
                print(yaml.dump(conf))

            if args.run_index:
                if args.fmus is None:
                    print("Missing fmus directory")
                    exit(-1)
                job_id = str(uuid.uuid4())
                print("Starting new job with id: %s in %s" % (job_id, str(job_dir)))
                prepare(conf, args.run_index, job_id, job_dir=job_dir,
                        fmu_dir=args.fmus)  # '/Users/kgl/data/au/into-cps-association/digital-twin-platform/src/dtpt/fmus'

                with open(job_dir / 'job.yml', 'w') as f:
                    f.write(yaml.dump(conf))
                # print(yaml.dump(conf))
                run(conf, args.run_index, job_dir)
        except yaml.YAMLError as exc:
            print(exc)
            raise exc


def main():
    parser = argparse.ArgumentParser(prog="digital_twin_tooling", epilog="""

        python -m "digital_twin_tooling" ....

        """)

    configure_arguments_parser(parser)
    args = parser.parse_args()
    process_cli_arguments(args)


if __name__ == '__main__':
    main()
