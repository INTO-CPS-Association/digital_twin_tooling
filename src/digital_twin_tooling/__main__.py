from digital_twin_tooling import basic, launchers

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title='Subcommands',
                                       description='Use any of the subcommands',
                                       help='additional help')

    project_parser = subparsers.add_parser("project")
    basic.configure_arguments_parser(project_parser)
    project_parser.set_defaults(func=basic.process_cli_arguments)

    launcher_parser = subparsers.add_parser("launcher")
    launchers.configure_arguments_parser(launcher_parser)
    launcher_parser.set_defaults(func=launchers.process_cli_arguments)

    args = parser.parse_args()
    args.func(args)
