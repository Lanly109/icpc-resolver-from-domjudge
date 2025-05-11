from argparse import ArgumentParser

from classes.domjudge import DOMjudge
from classes.pta import PTA_school

from utils.argument_parser import argument_parser
from utils.config_loader import config_loader
import subprocess

def main():
    argument = argument_parser()
    config = config_loader(argument['config'])
    DOMjudge(config).export(config['json'])
    # PTA_school(config).export(config['json'])

if __name__ == '__main__':
    main()
