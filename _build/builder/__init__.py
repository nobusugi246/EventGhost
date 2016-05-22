# -*- coding: utf-8 -*-
#
# This file is part of EventGhost.
# Copyright © 2005-2016 EventGhost Project <http://www.eventghost.net/>
#
# EventGhost is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# EventGhost is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with EventGhost. If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import sys
import tempfile
from os.path import abspath, dirname, exists, join

# Local imports
import builder
from builder import VirtualEnv
from builder.Logging import LogToFile
from builder.Utils import GetGitHubConfig, GetVersion

class Task(object):
    value = None
    visible = True
    enabled = True
    activated = True

    def __init__(self, buildSetup):
        self.buildSetup = buildSetup

    def Setup(self):
        pass

    def DoTask(self):
        raise NotImplementedError

    @classmethod
    def GetId(cls):
        return cls.__module__ + "." + cls.__name__


class Builder(object):
    def __init__(self):
        if not VirtualEnv.Running() and VirtualEnv.Exists():
            VirtualEnv.Activate()

        global buildSetup
        Task.buildSetup = self
        buildSetup = self

        self.pyVersionStr = "%d%d" % sys.version_info[:2]
        self.buildDir = abspath(join(dirname(__file__), ".."))
        self.sourceDir = abspath(join(self.buildDir, ".."))
        self.libraryName = "lib%s" % self.pyVersionStr
        self.libraryDir = join(self.sourceDir, self.libraryName)
        self.dataDir = join(self.buildDir, "data")
        self.docsDir = join(self.dataDir, "docs")
        self.pyVersionDir = join(self.dataDir, "Python%s" % self.pyVersionStr)
        self.outputDir = join(self.buildDir, "output")
        self.websiteDir = join(self.outputDir, "website")

        sys.path.append(self.sourceDir)
        sys.path.append(join(self.libraryDir, "site-packages"))

        self.args = self.ParseArgs()
        self.showGui = not (
            self.args.build or
            self.args.check or
            self.args.package or
            self.args.release or
            self.args.sync
        )

        os.chdir(self.buildDir)

        if not exists(self.outputDir):
            os.mkdir(self.outputDir)

        LogToFile(join(self.outputDir, "Build.log"))

        from CheckDependencies import CheckDependencies
        if not CheckDependencies(self):
            sys.exit(1)

        try:
            self.gitConfig = GetGitHubConfig()
        except:
            print(
                "WARNING: Can't release to GitHub until you do the following:\n"
                "    $ git config --global github.user <your github username>\n"
                "    $ git config --global github.token <your github token>\n"
                "To create a token, go to: https://github.com/settings/tokens\n"
            )
            self.gitConfig = {
                "all_repos": {
                    "EventGhost/EventGhost": {
                        "all_branches": ["master"],
                        "def_branch": "master",
                        "name": "EventGhost",
                    },
                },
                "branch": "master",
                "repo": "EventGhost",
                "repo_full": "EventGhost/EventGhost",
                "token": "",
                "user": "EventGhost",
            }

        self.appVersion = None
        self.appVersionInfo = None
        self.tmpDir = tempfile.mkdtemp()
        self.appName = self.name

    def ParseArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-b", "--build",
            action="store_true",
            help="build imports, lib%s, and interpreters" % self.pyVersionStr,
        )
        parser.add_argument(
            "-c", "--check",
            action="store_true",
            help="check source code for issues",
        )
        parser.add_argument(
            "-m", "--make-env",
            action="store_true",
            help="auto-install dependencies into a virtualenv",
        )
        parser.add_argument(
            "-p", "--package",
            action="store_true",
            help="build changelog, docs, and setup.exe",
        )
        parser.add_argument(
            "-r", "--release",
            action="store_true",
            help="release to github and web if credentials available",
        )
        parser.add_argument(
            "-s", "--sync",
            action="store_true",
            help="build and synchronize website",
        )
        parser.add_argument(
            "-v", "--version",
            action="store",
            help="package as the specified version",
        )
        return parser.parse_args()

    def Start(self):
        from Tasks import TASKS
        self.tasks = [task(self) for task in TASKS]
        from Config import Config
        self.config = Config(self, join(self.outputDir, "Build.ini"))
        for task in self.tasks:
            task.Setup()
        GetVersion(self)
        if self.showGui:
            import Gui
            Gui.Main(self)
        else:
            builder.Tasks.Main(self)