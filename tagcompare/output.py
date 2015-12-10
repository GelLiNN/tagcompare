"""Handles output files from the tagcompare tool
    - Creates output directories before a run
    - Compares the test configs with the result/output configs
    - Utility methods for getting the right path to outputs
"""
import os
import time
import glob
from distutils import dir_util
import shutil

import settings
import logger


OUTPUT_DIR = settings.OUTPUT_DIR
DEFAULT_BUILD_NAME = "default"
DEFAULT_BUILD_PATH = os.path.join(OUTPUT_DIR, DEFAULT_BUILD_NAME)
LOGGER = logger.Logger(name=__name__, writefile=False).get()

_NUM_PARTS = 5


class PathBuilder(object):
    """Class to store & build paths/partial paths to outputs of tagcompare
    """
    # TODO: Consider making this class immutable
    def __init__(self, parts, basepath=OUTPUT_DIR):
        if not basepath:
            raise ValueError("basepath is undefined!")
        if not parts:
            raise ValueError("array is undefined!")
        if len(parts) != _NUM_PARTS:
            raise ValueError("array doesn't have %s parts!" % _NUM_PARTS)

        self.__parts = parts
        self.basepath = basepath

    """
    Properties
    """

    @property
    def config(self):
        return self.__parts[1]

    @config.setter
    def config(self, value):
        if value:
            self.__parts[1] = str(value)

    @property
    def cid(self):
        return self.__parts[2]

    @cid.setter
    def cid(self, value):
        if value:
            self.__parts[2] = str(value)

    @property
    def tagsize(self):
        return self.__parts[3]

    @tagsize.setter
    def tagsize(self, value):
        if value:
            self.__parts[3] = str(value)

    @property
    def tagtype(self):
        return self.__parts[4]

    @tagtype.setter
    def tagtype(self, value):
        if value:
            self.__parts[4] = str(value)

    @property
    def build(self):
        """
        Read-only property - can only be set on init or internally
        :return:
        """
        return self.__parts[0]

    @property
    def path(self):
        """Gets the output path for a given config, cid and tagsize
        Returns partial paths if optional parameters aren't provided
        """
        return self._getpath(allow_partial=True)

    @property
    def tagname(self):
        result = str.format("{}-{}-{}-{}",
                            self.config, self.cid, self.tagsize, self.tagtype)
        return result

    @property
    def tagimage(self):
        result = os.path.join(self._getpath(allow_partial=False),
                              self.tagname + ".png")
        return result

    @property
    def taghtml(self):
        result = os.path.join(self._getpath(allow_partial=False),
                              self.tagname + ".html")
        return result

    @property
    def buildpath(self):
        result = os.path.join(self.basepath, self.build)
        return result

    """
    Functions
    """

    def _getpath(self, count=_NUM_PARTS, allow_partial=False):
        result = self.basepath
        for i in range(0, count):
            p = self.__parts[i]
            if not p:
                if not allow_partial:
                    raise ValueError("part %s is not set!" % i)
                return result
            p = str(p)
            result = os.path.join(result, p)
        LOGGER.debug("_getpath result: %s", result)
        return result

    def __eq__(self, other):
        if not isinstance(other, PathBuilder):
            return False
        return self.path == other.path

    def __str__(self):
        return str("{}-{}".format(
            self.build, self.tagname)) \
            .replace('None', '').rstrip('-')

    def clone(self, build=None, config=None,
              cid=None, tagsize=None, tagtype=None, basepath=None):
        """Clones the object with default values from self.  Can override specifics
        """
        original_parts = self.__parts
        new_parts = create(
            build=build, config=config, cid=cid, tagsize=tagsize, tagtype=tagtype).__parts
        result_parts = original_parts[:]

        if not basepath:
            basepath = self.basepath
        for i in range(0, _NUM_PARTS):
            p = new_parts[i]
            if p:
                result_parts[i] = p
        return PathBuilder(parts=result_parts, basepath=basepath)

    def pathexists(self):
        return os.path.exists(self.path)

    def create(self, allow_partial=False):
        # Throw if one of the parameters is not set
        result = self._getpath(allow_partial=allow_partial)
        if not os.path.exists(result):
            os.makedirs(result)
        return result

    def rmbuild(self):
        """Cleans up the files in the build path
        """
        buildpath = self.buildpath
        if os.path.exists(buildpath):
            LOGGER.debug("rmbuild for path %s", buildpath)
            shutil.rmtree(buildpath)
            return True
        return False


"""
Factory methods
"""


def create(build, config=None, cid=None, tagsize=None, tagtype=None, basepath=OUTPUT_DIR):
    parts = [build, config, cid, tagsize, tagtype]
    return PathBuilder(parts=parts, basepath=basepath)


def create_from_path(dirpath):
    """
    Given a 'dirpath' which corresponds to a path produced by PathBuilder,
    make the PathBuilder object
    :param dirpath: should be a real path ending in
    '{OUTPUT_DIR}/{build}/{config}/{cid}/{tagsize}/{tagtype}'
    """
    if not dirpath or not isinstance(dirpath, basestring):
        raise ValueError(
            'path is not defined or not a string.  path: {}'.format(
                dirpath))
    if not os.path.exists(dirpath):
        raise ValueError('path does not exist!  path: {}'.format(dirpath))

    parts = _split_pathstr(dirpath, count=_NUM_PARTS)
    return PathBuilder(parts=parts)


"""
Static helper methods:
"""


def _split_pathstr(pathstr, count):
    """
    Split a path string into parts
    :param pathstr:
    :param numparts:
    :return:
    """
    allparts = []
    tmp_path = pathstr
    for i in range(0, count):
        parts = os.path.split(tmp_path)
        assert len(parts) == 2, \
            "Not enough parts to the path! parts={}, dirpath={}".format(
                parts, pathstr)
        tmp_path = parts[0]
        allparts.insert(0, parts[1])

    allparts = [p for p in allparts if p]
    if len(allparts) != count:
        raise ValueError("path string %s doesn't have %s parts!", pathstr, count)

    return allparts


def aggregate(outputdir=OUTPUT_DIR):
    """
    Aggregates the captures from various campaigns to the 'default'
    :return:
    """
    if not os.path.exists(outputdir):
        raise ValueError("outputdir does not exist at %s!" % outputdir)

    outputdir = str(outputdir).rstrip('/')
    buildpaths = glob.glob(outputdir + '/*/')
    aggregate_path = os.path.join(outputdir, DEFAULT_BUILD_NAME)

    if not os.path.exists(aggregate_path):
        LOGGER.debug("Creating path for aggregates at %s", aggregate_path)
        os.makedirs(aggregate_path)

    LOGGER.info("Aggregating build data to %s", aggregate_path)
    # Workaround bug with dir_util
    # See http://stackoverflow.com/questions/9160227/
    dir_util._path_created = {}
    for buildpath in buildpaths:
        if str(buildpath).endswith(DEFAULT_BUILD_NAME + "/"):
            # Don't do this for the default build
            continue

        buildpath = os.path.join(outputdir, buildpath)
        LOGGER.debug("Copying from %s to %s", buildpath,
                     aggregate_path)

        dir_util.copy_tree(buildpath, aggregate_path, update=1)
    return aggregate_path


def generate_build_string():
    build = str.format(time.strftime("%Y%m%d-%H%M%S"))
    return build


if __name__ == '__main__':
    aggregate()
