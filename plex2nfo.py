#!/usr/bin/env python3

#### PYTHON IMPORTS ################################################################################
import os
import sys
from collections import defaultdict
from xml.sax.saxutils import escape


#### PACKAGE IMPORTS ###############################################################################
from plexapi.server import PlexServer


#### GLOBALS #######################################################################################
CONFIGS_PATH = None
DRY_RUN = None
OVERWRITE_NFO = None
VERBOSE = None
PLEX = None
MOVIE_NFO_STRING = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{title}</title>
    <sorttitle>{titleSort}</sorttitle>
    <plot>{summary}</plot>
    <releasedate>{originallyAvailableAt}</releasedate>
    <year>{year}</year>
    <edition>{edition}</edition>
</movie>
"""
SHOW_NFO_STRING = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
    <title>{title}</title>
    <sorttitle>{titleSort}</sorttitle>
    <plot>{summary}</plot>
    <releasedate>{originallyAvailableAt}</releasedate>
    <year>{year}</year>
</tvshow>
"""
EPISODE_NFO_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
"""
EPISODE_NFO_STRING = """<episodedetails>
    <title>{title}</title>
    <season>{parentIndex}</season>
    <episode>{index}</episode>
    <plot>{summary}</plot>
    <aired>{originallyAvailableAt}</aired>
</episodedetails>
"""
STATS = {
    "MOVIE": {
        "wrote": 0,
        "overwrote": 0,
        "skipped": 0,
        "failed": 0,
    },
    "SHOW": {
        "wrote": 0,
        "overwrote": 0,
        "skipped": 0,
        "failed": 0,
    },
    "EPISODE": {
        "wrote": 0,
        "overwrote": 0,
        "skipped": 0,
        "failed": 0,
    },

}
FAILURES = list()


#### FUNCTIONS #####################################################################################
def createServer(configs_path):
    """
    Set up server connection.
    """
    with open(configs_path, "r") as f:
        lines = f.readlines()
        baseurl = lines[0].rstrip()
        token = lines[1].rstrip()
        plex = PlexServer(baseurl, token)

    return plex


def getTVLibraries():
    """
    Get a list of TV libraries.
    """
    tv_libraries = list()
    tv_libraries = [section for section in PLEX.library.sections() if section.type == "show"]
    return tv_libraries


def getMovieLibraries():
    """
    Get a list of Movie libraries.
    """
    movie_libraries = list()
    movie_libraries = [section for section in PLEX.library.sections() if section.type == "movie"]
    return movie_libraries


def getListLibraryItems(library):
    """
    Get a list of Library items (e.g. shows, movies).
    """
    items = list()
    items = [item for item in library.all()]
    return items


def formatText(text):
    """
    Escape special characters that break XML.

    Contributed by: svwhisper
    """
    if text is None:
        return ""
    else:
        return escape(str(text))


def formatDate(date):
    """
    Format datetime.datetime objects. Replace bad values.
    """
    if date is None:
        return ""
    else:
        return date.strftime("%Y-%m-%d")


def formatEdition(edition):
    """
    Format edition informaton. Replace bad values.
    """
    if edition is None:
        return ""
    else:
        return formatText(edition)


def writeToDisk(loc, payload, kind, write_type):
    """
    Helper function to handle PermissionErrors on write.
    """
    try:
        with open(loc, "w") as f:
            f.write(payload)
        if write_type == "o":
            if VERBOSE:
                print("OVERWRITE: {}".format(loc))
            STATS[kind]["overwrote"] += 1
        elif write_type == "w":
            print("WRITE: {}".format(loc))
            STATS[kind]["wrote"] += 1
    except PermissionError:
        FAILURES.append(loc)
        print("FAILED: {}".format(loc))
        STATS[kind]["failed"] += 1


def writeNfoToDisk(location, payload, kind):
    """
    Write NFO files to disk.
    """
    loc = None
    if kind == "EPISODE":
        loc = os.path.splitext(location)[0] + ".nfo"
    elif kind == "SHOW":
        loc = os.path.join(location, "tvshow.nfo")
    elif kind == "MOVIE":
        loc = os.path.splitext(location)[0] + ".nfo"

    if os.path.exists(loc):
        if OVERWRITE_NFO:
            writeToDisk(loc, payload, kind, "o")
        else:
            if VERBOSE:
                print("SKIPPING: {}".format(loc))
            STATS[kind]["skipped"] += 1
    else:
        writeToDisk(loc, payload, kind, "w")


def writeMovieNfo(dry_run=True):
    """
    Write Movie NFO files to disk.
    """
    # Get a list of all Movie libraries
    movie_libraries = getMovieLibraries()
    print("\nExploring {} Movie Libraries...".format(len(movie_libraries)))
    print("--------")
    for movie_library in movie_libraries:
        print("Library: {}".format(movie_library.title))
        movies = getListLibraryItems(movie_library)
        print("  Found {} Movies...".format(len(movies)))
        for movie in movies:
            if VERBOSE:
                print("    Movie: {}...".format(movie.title))
            movie_nfo_string = MOVIE_NFO_STRING.format(
                title=formatText(movie.title),
                titleSort=formatText(movie.titleSort),
                year=movie.year,
                originallyAvailableAt=formatDate(movie.originallyAvailableAt),
                summary=movie.summary,
                edition=formatEdition(movie.editionTitle),
            )
            if dry_run:
                print(movie.locations[0])
                print(movie_nfo_string)
            if not dry_run:
                writeNfoToDisk(movie.locations[0], movie_nfo_string, "MOVIE")
    print("--------")


def writeTVnfo(dry_run=True):
    """
    Write TV NFO files to disk.
    """
    # Get a list of all TV libraries
    tv_libraries = getTVLibraries()
    print("\nExploring {} TV Libraries...".format(len(tv_libraries)))
    print("--------")
    for tv_library in tv_libraries:
        # For every TV show, grab the metadata I care about and shove it into a NFO format string
        print("Library: {}".format(tv_library.title))
        shows = getListLibraryItems(tv_library)
        print("  Found {} TV Shows...".format(len(shows)))
        for show in shows:
            if VERBOSE:
                print("    Show: {}...".format(show.title))
            show_nfo_string = SHOW_NFO_STRING.format(
                title=formatText(show.title),
                titleSort=formatText(show.titleSort),
                year=show.year,
                originallyAvailableAt=formatDate(show.originallyAvailableAt),
                summary=show.summary
            )

            if not show.locations:
                # If episodes live in the library root, there's no sensible place to write
                # tvshow.nfo -- Contributed by: svwhisper
                print("No folder for {}. Skipping tvshow.nfo".format(show.title))
            elif dry_run:
                print(show.locations[0])
                print(show_nfo_string)
            else: # Not a dry run
                writeNfoToDisk(show.locations[0], show_nfo_string, "SHOW")

            # For every episode in a show, grab the metadata I care about and shove it into a NFO
            # format string
            # Previous versions of this code didn't handle multi-episode files properly. The logic
            # below that ensures the NFO details for each multi-episode get written to a single file
            # was contributed by svwhisper.
            episodes_by_file = defaultdict(list)
            episodes = show.episodes()
            if VERBOSE:
                print("      Found {} Episodes...".format(len(episodes)))
            for episode in episodes:
                if VERBOSE:
                    print("        Episode: {}...".format(episode.title))
                episode_nfo_string = EPISODE_NFO_STRING.format(
                    title=formatText(episode.title),
                    summary=formatText(episode.summary),
                    originallyAvailableAt=formatDate(episode.originallyAvailableAt),
                    index=episode.index,
                    parentIndex=episode.parentIndex
                )
                episodes_by_file[episode.locations[0]].append(episode_nfo_string)
            for location, episode_nfo_strings in episodes_by_file.items():
                episode_nfo_string = EPISODE_NFO_XML + "".join(episode_nfo_strings)
                if dry_run:
                    print(os.path.splitext(location)[0] + ".nfo")
                    print(episode_nfo_string)
                if not dry_run:
                    writeNfoToDisk(location, episode_nfo_string, "EPISODE")
    print("--------")


def printStats():
    """
    Print write, overwrite, and skip statistics.
    """
    print("Statistics:")
    print("\n--------")
    print("Movies:")
    print("  Wrote: {}\tOverwrote: {}\tSkipped: {}\tFailed: {}".format(STATS["MOVIE"]["wrote"], STATS["MOVIE"]["overwrote"], STATS["MOVIE"]["skipped"], STATS["MOVIE"]["failed"]))
    print("Shows:")
    print("  Wrote: {}\tOverwrote: {}\tSkipped: {}\tFailed: {}".format(STATS["SHOW"]["wrote"], STATS["SHOW"]["overwrote"], STATS["SHOW"]["skipped"], STATS["SHOW"]["failed"]))
    print("Episodes:")
    print("  Wrote: {}\tOverwrote: {}\tSkipped: {}\tFailed: {}".format(STATS["EPISODE"]["wrote"], STATS["EPISODE"]["overwrote"], STATS["EPISODE"]["skipped"], STATS["EPISODE"]["failed"]))
    print("--------\n")


def printFailures():
    """
    Print list of any failures.
    """
    print("Failures:")
    print("\n--------")
    for failure in FAILURES:
        print("  {}".format(failure))
    print("--------\n")


#### MAIN ##########################################################################################
if __name__ == "__main__":
    args = sys.argv[1:]
    print("ARGS: {}".format(args))
    CONFIGS_PATH = args[0]
    DRY_RUN = bool(int(args[1]))
    OVERWRITE_NFO = bool(int(args[2]))
    VERBOSE = bool(int(args[3]))
    PLEX = createServer(CONFIGS_PATH)

    if VERBOSE:
        print("\n--------")
        print("CONFIGS: {}".format(CONFIGS_PATH))
        print("DRY_RUN: {}".format(DRY_RUN))
        print("OVERWRITE: {}".format(OVERWRITE_NFO))
        print("VERBOSE: {}".format(VERBOSE))
        print("PLEX: {}".format(PLEX))
        print("--------\n")

    writeTVnfo(dry_run=DRY_RUN)
    writeMovieNfo(dry_run=DRY_RUN)

    printStats()
    printFailures()
