from digital_twin_tooling.app import app
import argparse


def configure_arguments_parser(parser):
    parser.add_argument("-base", "--base-directory", dest="base", type=str, required=True,
                        help='Path where projects exists')


def process_cli_arguments(args):
    app.config["PROJECT_BASE"] = args.base
    app.run(host='0.0.0.0', debug=True, port=80)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    configure_arguments_parser(p)
    process_cli_arguments(p.parse_args())
