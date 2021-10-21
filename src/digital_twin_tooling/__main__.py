from digital_twin_tooling import project_mgmt, launchers
from digital_twin_tooling.app import server

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title='Subcommands',
                                       description='Use any of the subcommands',
                                       help='additional help')

    project_parser = subparsers.add_parser("project")
    project_mgmt.configure_arguments_parser(project_parser)
    project_parser.set_defaults(func=project_mgmt.process_cli_arguments)

    launcher_parser = subparsers.add_parser("launcher")
    launchers.configure_arguments_parser(launcher_parser)
    launcher_parser.set_defaults(func=launchers.process_cli_arguments)

    webapi_parser = subparsers.add_parser("webapi")
    server.configure_arguments_parser(webapi_parser)
    webapi_parser.set_defaults(func=server.process_cli_arguments)

    args = parser.parse_args()
    args.func(args)
