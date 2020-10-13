#   -*- coding: utf-8 -*-
from pybuilder.core import use_plugin, init, Author

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
# use_plugin("python.distutils")

name = "BuildTorrent"
summary = "Ingegneria del Software Avanzata project"
version = "1.0"
authors = [Author("Manuel Furini", ""), Author("Luca Pasquali", "")]
license = "None"
url = "https://github.com/manuelfurini/isa"

default_task = ['clean', 'analyze', 'publish']


@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src/main")
    project.set_property("dir_source_unittest_python", "src/test")
    project.set_property("dir_source_main_scripts", "src/main")
    project.set_property("coverage_exceptions", ['Peer', 'Tracker', 'v4v6'])


@init
def initialize(project):
    project.build_depends_on("flask")
