import json
import yaml
from .rabbitmq_fmu import create_fmu_with_outputs
import subprocess
import tempfile
from pathlib import Path
import uuid
import os
import copy
from jsonschema import validate as yml_validate
import pkg_resources
from .launchers import MaestroProcessLauncher, AmqpProviderProcessLauncher
import argparse
from .tools import fetch_tools
import jsonschema


def validate(conf, version="0.0.1"):
    # with open(Path(__file__).parent / 'schema-0.0.1.yml', 'r') as sf:
    with get_schema(version) as stream:
        # with open(Path(project_path) / file, mode='wb', buffering=0) as f:
        # f.write(stream.read())
        schema = yaml.load(stream, Loader=yaml.FullLoader)
        try:
            yml_validate(conf, schema)
        except jsonschema.exceptions.ValidationError as exc:

            print(exc)
            print(yaml.dump(conf))
            raise exc


def get_schema(version):
    return pkg_resources.resource_stream(__name__, 'data/schema-' + version + '.yml')


def show(conf):
    if 'servers' in conf:
        print('## Servers ##')
        for s in conf['servers']:
            print("Server:\n\tid: %s\n\ttype:%s\n\tembedded: %s" % (s['id'], s['type'], 'embedded' in s))


def run(conf, run_index, job_dir, base_dir=Path(os.getcwd())):
    print("""
                     __               __  
|     /\  |  | |\ | /  ` |__| | |\ | / _` 
|___ /~~\ \__/ | \| \__, |  | | | \| \__> 
                                          """)
    print("Checking config")
    validate(conf, version='0.0.2')
    print('''###############################################################
    
    Running from ''' + str(job_dir) + '''
    
###############################################################''')

    print("Launch config")
    if 'configurations' in conf:
        config = conf['configurations'][run_index]
        print("Running: '%s'" % config['name'])
        for idx, task_group in enumerate(config['tasks']):

            for key in task_group.keys():
                if key in ['id', 'name']:
                    continue

                task = task_group[key]

                print("State %d: %s" % (idx, key))

                if 'execution' in task and 'skip' in task['execution'] and task['execution']['skip']:
                    print('Skipping launch of %d: %s' % (idx, task['type']))
                    continue

                task_launcher = None
                if key == 'amqp-repeater':
                    task_launcher = AmqpProviderProcessLauncher()
                elif key == 'simulation':
                    if 'execution' in task and 'tool' in task['execution']:
                        tool_id = task['execution']['tool']
                        if tool_id in conf["tools"]:
                            tool = conf['tools'][tool_id]
                            tool_path = tool['path']
                            task_launcher = MaestroProcessLauncher(Path(tool_path).absolute())
                        else:
                            raise Exception("Required tool : " + tool_id + " not found")
                else:
                    raise "No launcher for task id: %s".format(key)

                pid = task_launcher.launch(job_dir, task)
                with open(job_dir / (key + '.pid'), 'w') as f:
                    f.write(str(pid))


def flatten(t):
    return [item for sublist in t for item in sublist]


def prepare(conf, run_index, job_id, job_dir, fmu_search_paths: list[str], base_dir=Path(os.getcwd()),
            prepare_rabbitmq=False):
    print("""
 __   __   ___  __        __          __  
|__) |__) |__  |__)  /\  |__) | |\ | / _` 
|    |  \ |___ |    /~~\ |  \ | | \| \__> 
                                          """)
    # validate sections
    print("Checking config")
    validate(conf, version='0.0.2')
    print("Preparing")
    # start all one at the time
    if 'configurations' in conf:
        config = conf['configurations'][run_index]
        print("Running: '%s'" % config['name'])

        current_job_id = job_id
        # check if the job has a fixed job id
        if 'fixed_job_id' in config:
            current_job_id = config['fixed_job_id']

        for idx, task_group in enumerate(config['tasks']):

            print("State %d: %s" % (idx, "".join(task_group.keys())))

            if 'simulation' in task_group:
                task = task_group['simulation']
                # we need to generate rabbitmq fmu with the right signals
                if 'spec' in task and 'spec_runtime' in task:
                    # already processed
                    del task['config']
                    continue

                if prepare_rabbitmq:
                    prepare_rabbitmq_fmu_for_from_maestro_config(base_dir, conf, config, base_dir, task)
                # configure AMQP exchange
                task['config']['parameters']['{amqp}.ext.config.routingkey'] = current_job_id
                task['config']['parameters']['{amqp}.ext.config.exchangename'] = 'fmi_digital_twin'
                task['config']['parameters']['{amqp}.ext.config.exchangetype'] = 'direct'
                for server_id in conf['servers'].keys():
                    if 'embedded' in conf['servers'][server_id] and conf['servers'][server_id]['embedded'] and \
                            conf['servers'][server_id]['type'] == 'AMQP':
                        task['config']['parameters']['{amqp}.ext.config.hostname'] = conf['servers'][server_id]['host']
                        task['config']['parameters']['{amqp}.ext.config.port'] = int(conf['servers'][server_id]['port'])
                        task['config']['parameters']['{amqp}.ext.config.username'] = conf['servers'][server_id]['user']
                        task['config']['parameters']['{amqp}.ext.config.password'] = conf['servers'][server_id][
                            'password']
                        break

                print("\tImporting into Maestro for spec generating")
                with tempfile.NamedTemporaryFile(suffix='.json', delete=os.name != 'nt') as fp:
                    fp.write(json.dumps(task['config']).encode('utf-8'))
                    fp.flush()
                    if os.name == 'nt':
                        fp.close()
                    # fp.file.close()
                    simulation_prepare_tool_id = task['prepare']['tool']
                    maestro_tool = Path(conf['tools'][simulation_prepare_tool_id]['path'])
                    if not maestro_tool.is_absolute():
                        maestro_tool = base_dir / maestro_tool

                    cmd = "java -jar {0} import -vi FMI2 sg1 {1} -output {2} ".format(
                        maestro_tool.absolute(),
                        fp.name,
                        "specs")

                    if fmu_search_paths:
                        cmd += ' --fmu-search-path ' + (" --fmu-search-path ".join(fmu_search_paths))

                    try:
                        subprocess.run(cmd, shell=True, check=True, cwd=job_dir, stderr=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        raise RuntimeError(
                            "command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

                    task['spec'] = str(Path('specs') / 'spec.mabl')
                    task['spec_runtime'] = str(Path('specs') / 'spec.runtime.json')
                    del task['config']

            if 'amqp-repeater' in task_group:
                task = task_group['amqp-repeater']
                for signal in task['signals'].keys():
                    # including HACK for wired naming implicit to the rabbitmq fmu
                    task['signals'][signal]['target']['exchange'] = 'fmi_digital_twin'  # + '_cd'
                    task['signals'][signal]['target']['routing_key'] = current_job_id  # + '.data.to_cosim'

                for server in task['servers'].keys():

                    server_id = task['servers'][server]
                    task['servers'][server] = copy.deepcopy(conf['servers'][server_id])
                    # do not delete name, if so it will check as string and not be valid
                    if 'type' in task['servers'][server]:
                        del task['servers'][server]['type']


def prepare_rabbitmq_fmu_for_from_maestro_config(base_dir, conf, config, fmu_dir, task):
    signals = flatten([([(s, t['amqp-repeater']['signals'][s]['target']['datatype']) for s in
                         (t['amqp-repeater']['signals'].keys()) if
                         'target' in t['amqp-repeater']['signals'][s] and 'datatype' in
                         t['amqp-repeater']['signals'][s]['target']]) for
                       t in config['tasks'] if 'amqp-repeater' in t])
    rabbitmq_tool_ids = [t['amqp-repeater']['prepare']['tool'] for t in config['tasks'] if
                         'amqp-repeater' in t and 'prepare' in t['amqp-repeater'] and 'tool' in
                         t['amqp-repeater']['prepare']]
    if len(rabbitmq_tool_ids) >= 1:
        rabbitmq_tool_id = rabbitmq_tool_ids[0]
    else:
        raise Exception('Could not find amqp-repeater for simulation that has a tool')
    # flatten([list(t['signals'].keys()) for t in config['tasks'] if t['type'] == 'amqp-repeater'])
    dest = task['config']['fmus']['{amqp}']
    print("\tCreating AMQP instance with the required signals")
    rabbitmq_fmu_tool = Path(conf['tools'][rabbitmq_tool_id]['path'])
    if not rabbitmq_fmu_tool.is_absolute():
        rabbitmq_fmu_tool = base_dir / rabbitmq_fmu_tool
    create_fmu_with_outputs(
        rabbitmq_fmu_tool.absolute(), Path(fmu_dir) / Path(dest).name,
        signals)


def prepare_task(conf, task, output_dir: Path, base_dir=Path(os.getcwd())):
    fetch_tools(conf, quite=True, base_dir=base_dir)
    if 'amqp-repeater' in task:
        return prepare_data_repeater(conf, task['amqp-repeater'], output_dir, base_dir=base_dir)
    elif 'simulation' in task:
        pass

    return {}


def prepare_data_repeater(conf, data_repeater_conf, output_dir: Path, base_dir=Path(os.getcwd())):
    if "signals" not in data_repeater_conf:
        raise Exception("Signals not in config")

    signals = [(s, data_repeater_conf['signals'][s]['target']['datatype']) for s in
               data_repeater_conf['signals'].keys()]

    print("\tCreating AMQP instance with the required signals")
    import tempfile
    with tempfile.NamedTemporaryFile(prefix="AMQP-PROXY", suffix=".fmu", dir=str(output_dir),
                                     delete=False) as output_file:

        tool_path = Path(conf['tools']['rabbitmq']['path'])
        if not tool_path.is_absolute():
            tool_path = base_dir / tool_path

        create_fmu_with_outputs(tool_path.absolute(), output_file.name, signals)
        return {"file": str(Path(output_file.name).relative_to(base_dir.absolute())), "signals": signals}


def configure_arguments_parser(parser):
    parser.add_argument("-project", "--project-path", dest="project", type=str, required=True,
                        help='Path to the project *.yml file')
    # options.add_argument("-project", "--project-path", dest="project", type=str, required=False,
    #                      help='Path to the project root containing the .env')
    parser.add_argument("-work", "--working-path", dest="work", type=str, required=False,
                        help='Optional path to a working directory')
    parser.add_argument("--fetch-tools", dest="fetch_tools", action="store_true", required=False,
                        help='Optional path to a working directory')
    parser.add_argument("-fmus", "--fmu-dir-path", dest="fmus", type=str, required=False,
                        help='Optional path to a working directory')
    parser.add_argument("-run", "--run-index", dest="run_index", type=int, required=False,
                        help='The index of the simulation to run')
    # options.add_argument("-reload", "--reload-pipe", dest="reload", type=bool, required=False,
    #                      help='If the pipeline should be reloaded instead of configured')
    parser.add_argument("-show", "--show", required=False, help='Show the pipeline', action="store_true")


def process_cli_arguments(args):
    configuration_file = args.project

    with open(configuration_file, 'r') as f:
        try:
            conf = yaml.load(f, Loader=yaml.FullLoader)
            if args.show:
                # show(conf)
                print(yaml.dump(conf))

            if 'version' in conf:
                version = conf['version']
            else:
                version = '0.0.2'

            if version == '0.0.2':

                if args.fetch_tools:
                    fetch_tools(conf)

                if args.run_index:
                    if args.fmus is None:
                        print("Missing fmus directory")
                        exit(-1)
                    job_id = str(uuid.uuid4())

                    if args.work:
                        job_dir = Path(args.work)
                    else:
                        job_dir = Path(os.curdir) / 'jobs' / job_id
                        os.makedirs(job_dir, exist_ok=True)

                    print("Starting new job with id: %s in %s" % (job_id, str(job_dir)))
                    prepare(conf, args.run_index, job_id, job_dir=job_dir,
                            fmu_dir=args.fmus)  # '/Users/kgl/data/au/into-cps-association/digital-twin-platform/src/dtpt/fmus'

                    with open(job_dir / 'job.yml', 'w') as f:
                        f.write(yaml.dump(conf))
                    # print(yaml.dump(conf))
                    run(conf, args.run_index, job_dir)
            else:
                print("Version not supported by run: " + version)
                raise Exception("Version not supported")
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
