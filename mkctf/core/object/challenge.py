# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     file: challenge.py
#     date: 2018-02-27
#   author: paul.dautry
#  purpose:
#
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# =============================================================================
#  IMPORTS
# =============================================================================
from os import urandom
from stat import S_IRWXU
from asyncio import create_subprocess_exec, wait_for, TimeoutError
from subprocess import PIPE, CalledProcessError
from core.wrapper import lazy
from core.object.configurable import Configurable
# =============================================================================
#  CLASSES
# =============================================================================
class Challenge(Configurable):
    """[summary]

    [description]

    Extends:
        Configurable
    """
    @staticmethod
    def make_flag(repo_conf, size=32):
        """Makes a flag

        Arguments:
            repo_conf {dict} -- [description]

        Keyword Arguments:
            size {number} -- [description] (default: {32})
        """
        return "{}{}{}".format(repo_conf['flag']['prefix'],
                               urandom(size).hex(),
                               repo_conf['flag']['suffix'])

    def __init__(self, logger, chall_conf_path, repo_conf):
        """Constructs a new instance

        Arguments:
            logger {[type]} -- [description]
            chall_conf_path {[type]} -- [description]
            repo_conf {[type]} -- [description]
        """
        super().__init__(logger, chall_conf_path)
        self.repo_conf = repo_conf

    def __create_dir(self, directory):
        """Creates a directory

        Arguments:
            directory {Path or str} -- [description]

        Returns:
            bool -- [description]
        """
        dir_path = self.working_dir().joinpath(directory)

        if not dir_path.is_dir():
            dir_path.mkdir(parents=True, exist_ok=True)

            return True

        return False

    def __create_file(self, filename, executable=False):
        """Creates a file

        Arguments:
            filename {Path or str} -- [description]

        Keyword Arguments:
            executable {bool} -- [description] (default: {False})

        Returns:
            bool -- [description]
        """
        filepath = self.working_dir().joinpath(filename)

        filepath.parent.mkdir(parents=True, exist_ok=True)

        if not filepath.is_file():
            with filepath.open('w') as f:
                if executable:
                    f.write('#!/usr/bin/env bash\n')

                f.write('# file automatically generated by mkctf.\n')

                if executable:
                    f.write('>&2 echo "not implemented."\n')
                    f.write('exit 4\n')

            if executable:
                filepath.chmod(S_IRWXU)

            return True

        return False

    async def __run(self, script, timeout):
        if not script.startswith('/'):
            script = './{}'.format(script)

        proc = await create_subprocess_exec(script,
                                            stdout=PIPE,
                                            stderr=PIPE,
                                            cwd=str(self.working_dir()))

        try:
            stdout, stderr = await wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError as e:
            proc.terminate()
            return (None, e.stdout, e.stderr)
        except CalledProcessError as e:
            proc.terminate()
            return (e.returncode, e.stdout, e.stderr)

        return (proc.returncode, stdout, stderr)

    @lazy()
    def category(self):
        """Gets challenge's category

        Decorators:
            lazy

        Returns:
            [type] -- [description]
        """
        return self.working_dir().parent.name

    @lazy()
    def slug(self):
        """Gets challenge's slug

        Decorators:
            lazy

        Returns:
            [type] -- [description]
        """
        return self.working_dir().name

    def is_standalone(self):
        """Determines if challenge is static

        Returns:
            bool -- True if static, False otherwise
        """
        return self.get_conf('standalone')

    def enabled(self):
        """Determines if challenge is enabled

        Returns:
            bool -- True if enabled, False otherwise
        """
        return self.get_conf('enabled')

    def enable(self, enabled=True):
        """Enables or disables the challenge

        [description]

        Keyword Arguments:
            enabled {bool} -- [description] (default: {True})
        """
        conf = self.get_conf()
        conf['enabled'] = enabled
        self.set_conf(conf)

    def renew_flag(self, size=32):
        """Renews challenge's flag

        Arguments:
            size {int} -- number of random bytes

        Returns:
            str -- new flag
        """
        conf = self.get_conf()
        conf['flag'] = Challenge.make_flag(self.repo_conf, size)
        self.set_conf(conf)
        return conf['flag']

    def create(self):
        """Creates challenge files

        Returns:
            bool -- [description]
        """
        self.working_dir().mkdir(parents=True, exist_ok=True)

        directories = self.repo_conf['directories']['public'][::]
        directories += self.repo_conf['directories']['private']

        for directory in directories:
            if not self.__create_dir(directory):
                self.logger.warning("directory exists already: "
                                    "{}".format(directory))

        for file in self.repo_conf['files']['txt']:
            if not self.__create_file(file):
                self.logger.warning("file exists already: "
                                    "{}".format(file))

        bin_files = [
            self.repo_conf['files']['build'],
            self.repo_conf['files']['deploy'],
            self.repo_conf['files']['status']
        ]

        for file in bin_files:
            if not self.__create_file(file, executable=True):
                self.logger.warning("file exists already: "
                                    "{}".format(file))

        return True

    def exportable(self):
        """Yields files contained in public folders

        Yields:
            [type] -- [description]
        """
        wd = self.working_dir()
        for directory in self.repo_conf['directories']['public']:
            dir_path = wd.joinpath(directory)
            for de in self._scandirs(dir_path):
                yield de

    async def build(self, timeout=4):
        """Builds the challenge

        Keyword Arguments:
            timeout {int} -- subprocess timeout (seconds) (default: {4})

        Returns:
            [type] -- [description]
        """
        return await self.__run(self.repo_conf['files']['build'], timeout)

    async def deploy(self, timeout=4):
        """Deploys the challenge

        Keyword Arguments:
            timeout {int} -- subprocess timeout (seconds) (default: {4})

        Returns:
            [type] -- [description]
        """
        return await self.__run(self.repo_conf['files']['deploy'], timeout)

    async def status(self, timeout=4):
        """[summary]

        [description]

        Keyword Arguments:
            timeout {int} -- subprocess timeout (seconds) (default: {4})

        Returns:
            [type] -- [description]
        """
        return await self.__run(self.repo_conf['files']['status'], timeout)

