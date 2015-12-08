"""We want to make a set of comparisons factoring in popular browser/OS variations
    Comparisons are determined from usage stats:
        - OS usage stats: http://www.w3schools.com/browsers/browsers_os.asp
        - Browser usage stats: http://www.w3schools.com/browsers/browsers_stats.asp

    Configs are made based on supported capabilities:
    - saucelabs:
    https://wiki.saucelabs.com/display/DOCS/Platform+Configurator#/
    - browserstack:
    https://www.browserstack.com/list-of-browsers-and-platforms?product=automate
"""
import itertools
import os

import logger
import output
import settings
import image
import placelocal


LOGGER = logger.Logger("compare", writefile=True).get()


def compare_campaign(cid):
    pb = output.PathBuilder(cid=cid)
    compare_configs(pathbuilder=pb, configs=settings.DEFAULT.configs)


def compare_configs(pathbuilder, configs):
    # TODO: Should we check if configs are enabled before comparing?
    assert pathbuilder, "No pathbuilder object!"
    assert configs, "No configs!"

    compare_build = output.DEFAULT_BUILD_NAME
    sizes = settings.DEFAULT.tagsizes
    types = settings.DEFAULT.tagtypes
    count = 0
    errorcount = 0
    skipcount = 0

    # Compare all combinations of configs
    for a, b in itertools.combinations(configs, 2):
        for s in sizes:
            for t in types:
                pba = pathbuilder.clone(build=compare_build, config=a, size=s, type=t,
                                        cid=pathbuilder.cid)
                pbb = pathbuilder.clone(build=compare_build, config=b, size=s, type=t,
                                        cid=pathbuilder.cid)
                pba_img = pba.tagimage
                pbb_img = pbb.tagimage
                count += 1
                compare_result = compare_images(pba_img, pbb_img, pathbuilder=pathbuilder)
                if compare_result is None:
                    skipcount += 1
                elif compare_result is False:
                    errorcount += 1

    LOGGER.debug("Compared %s images: %s errors, %s skipped", count, errorcount,
                 skipcount)
    return errorcount, count, skipcount


def compare_images(file1, file2, pathbuilder):
    """Compares two image files, returns True if compare took place, False otherwise
    :param file1:
    :param file2:
    :return:
    """
    compare_name = __get_compare_name(file1, file2)
    if not os.path.exists(file1):
        LOGGER.warn("SKIPPING %s - %s not found!", compare_name, file1)
        return None
    if not os.path.exists(file2):
        LOGGER.warn("SKIPPING %s - %s not found!", compare_name, file2)
        return None

    diff = image.compare(file1, file2)
    if diff is False:
        # Unable to produce diff due to errors
        return False

    if diff > image.ERROR_THRESHOLD:
        __write_merged_image(file1, file2, diff, pathbuilder=pathbuilder)
        return False

    return True


def __get_compare_name(file1, file2):
    filename1 = os.path.basename(file1)
    filename2 = os.path.basename(file2)
    compare_name = str.format("{}__vs__{}".format(
        os.path.splitext(filename1)[0], os.path.splitext(filename2)[0]))
    return compare_name


def __write_merged_image(file1, file2, diff, pathbuilder):
    assert os.path.exists(file1), "file1 doesn't exist at path {}".format(file1)
    assert os.path.exists(file2), "file2 doesn't exist at path {}".format(file2)
    compare_name = __get_compare_name(file1, file2)

    # Generate additional info in output
    mergedimg = image.merge_images(file1, file2)
    info = {"name": compare_name, "diff": diff}
    mergedimg2 = image.add_info(mergedimg, info)
    build_dir = pathbuilder.buildpath
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    merged_path = os.path.join(build_dir, compare_name + ".png")
    if not settings.TEST_MODE:
        mergedimg2.save(open(merged_path, 'wb'))
    LOGGER.warning("%s produced diff=%s. See %s", compare_name, diff, merged_path)


def do_all_comparisons(cids=settings.DEFAULT.campaigns,
                       pids=settings.DEFAULT.publishers, pathbuilder=None):
    cids = placelocal.get_cids(cids=cids, pids=pids)

    total_compares = 0
    total_errors = 0
    total_skipped = 0

    # Always compare against default job path
    if not pathbuilder:
        pathbuilder = output.PathBuilder(build=output.generate_build_string())

    for cid in cids:
        pathbuilder.cid = cid
        comparisons = settings.DEFAULT.comparisons
        for name in comparisons:
            LOGGER.debug("*** Comparing set: %s...", name)
            configs_to_compare = comparisons[name]
            errors, count, skipped = compare_configs(pathbuilder=pathbuilder,
                                                     configs=configs_to_compare)
            total_errors += errors
            total_compares += count
            total_skipped += skipped

    LOGGER.info("*** RESULTS ***\nCompared %s images: %s errors, %s skipped",
                total_compares, total_errors,
                total_skipped)
    LOGGER.info("See additional logs at: %s", pathbuilder.buildpath)


def main(jobname=None):
    output.aggregate()
    if not jobname:
        jobname = output.generate_build_string()
    pb = output.PathBuilder(build=jobname)
    do_all_comparisons(cids=settings.DEFAULT.campaigns,
                       pids=settings.DEFAULT.publishers, pathbuilder=pb)


if __name__ == '__main__':
    main()
