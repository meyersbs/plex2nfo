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
XML_DECLARATION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
"""
# A file holding several episodes (e.g. S01E01-E02) gets one <episodedetails> per episode,
# all in the same .nfo, so this template has no XML declaration of its own.
EPISODE_NFO_STRING = """<episodedetails>
    <title>{title}</title>
    <season>{parentIndex}</season>
    <episode>{index}</episode>
    <plot>{summary}</plot>
    <aired>{originallyAvailableAt}</aired>
</episodedetails>
"""


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


def getLibraries():
    """
    Get a list of libraries.
    """
    libraries = list()
    for section in PLEX.library.sections():
        libraries.append(section)

    return libraries


def getTVLibraries():
    """
    Get a list of TV libraries.
    """
    tv_libraries = list()
    tv_libraries = [section for section in PLEX.library.sections() if section.type == "show"]
    print(tv_libraries)
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


def formatDate(date):
    if date is None:
        return ""
    else:
        return date.strftime("%Y-%m-%d")


def formatText(text):
    """
    Escape &, < and > so titles and summaries can't produce invalid XML.
    """
    if text is None:
        return ""
    else:
        return escape(str(text))


def writeMovieNfoToDisk(location, payload):
    """
    Write 'movie.nfo' files to disk.
    """
    loc = os.path.splitext(location)[0] + ".nfo"
    print(loc)
    if OVERWRITE_NFO:
        with open(loc, "w") as f:
            f.write(payload)
    else:
        if not os.path.exists(loc):
            with open(loc, "w") as f:
                f.write(payload)


def writeShowNfoToDisk(location, payload):
    """
    Write 'tvshow.nfo' files to disk.
    """
    loc = os.path.join(location, "tvshow.nfo")
    print(loc)
    if OVERWRITE_NFO:
        with open(loc, "w") as f:
            f.write(payload)
    else:
        if not os.path.exists(loc):
            with open(loc, "w") as f:
                f.write(payload)


def writeEpisodeNfoToDisk(location, payload):
    """
    Write episode NFO files to disk.
    """
    loc = os.path.splitext(location)[0] + ".nfo"
    print(loc)
    if OVERWRITE_NFO:
        with open(loc, "w") as f:
            f.write(payload)
    else:
        if not os.path.exists(loc):
            with open(loc, "w") as f:
                f.write(payload)


def writeMovieNfo(dry_run=True):
    """
    Write Movie NFO files to disk.
    """
    # Get a list of all Movie libraries
    movie_libraries = getMovieLibraries()
    for movie_library in movie_libraries:
        for movie in getListLibraryItems(movie_library):
            movie_nfo_string = MOVIE_NFO_STRING.format(
                title=formatText(movie.title),
                titleSort=formatText(movie.titleSort),
                year=formatText(movie.year),
                originallyAvailableAt=formatDate(movie.originallyAvailableAt),
                summary=formatText(movie.summary),
                edition=formatText(movie.editionTitle),
            )
            if dry_run:
                print(movie.locations[0])
                print(movie_nfo_string)
            if not dry_run:
                writeMovieNfoToDisk(movie.locations[0], movie_nfo_string)


def writeTVnfo(dry_run=True):
    """
    Write TV NFO files to disk.
    """
    # Get a list of all TV libraries
    tv_libraries = getTVLibraries()
    for tv_library in tv_libraries:
        # For every TV show, grab the metadata I care about and shove it into a NFO format string
        for show in getListLibraryItems(tv_library):
            # Shows have no edition in plexapi (only movies do); show.editionTitle raised
            # AttributeError and stopped the run at the first show.
            show_nfo_string = SHOW_NFO_STRING.format(
                title=formatText(show.title),
                titleSort=formatText(show.titleSort),
                year=formatText(show.year),
                originallyAvailableAt=formatDate(show.originallyAvailableAt),
                summary=formatText(show.summary),
            )
            # Plex reports no show folder when episode files sit directly in the library root;
            # there is nowhere sensible for tvshow.nfo then, but the episodes still get theirs.
            if not show.locations:
                print(f"No folder for show '{show.title}', skipping tvshow.nfo")
            elif dry_run:
                print(show.locations[0])
                print(show_nfo_string)
            else:
                writeShowNfoToDisk(show.locations[0], show_nfo_string)

            # For every episode in a show, grab the metadata I care about and shove it into a NFO
            # format string
            # Group by file first: a multi-episode file has several episodes, and writing them
            # one at a time made each overwrite the previous one's .nfo.
            episodes_by_file = defaultdict(list)
            for episode in show.episodes():
                episode_nfo_string = EPISODE_NFO_STRING.format(
                    title=formatText(episode.title),
                    summary=formatText(episode.summary),
                    # The episode's own air date (was the show's premiere date for every episode)
                    originallyAvailableAt=formatDate(episode.originallyAvailableAt),
                    index=formatText(episode.index),
                    parentIndex=formatText(episode.parentIndex)
                )
                episodes_by_file[episode.locations[0]].append(episode_nfo_string)
            for location, episode_nfo_strings in episodes_by_file.items():
                episode_nfo_string = XML_DECLARATION + "".join(episode_nfo_strings)
                if dry_run:
                    print(os.path.splitext(location)[0] + ".nfo")
                    print(episode_nfo_string)
                if not dry_run:
                    writeEpisodeNfoToDisk(location, episode_nfo_string)


#### MAIN ##########################################################################################
if __name__ == "__main__":
    args = sys.argv[1:]
    print(args)
    CONFIGS_PATH = args[0]
    print(CONFIGS_PATH)
    DRY_RUN = bool(int(args[1]))
    print(DRY_RUN)
    OVERWRITE_NFO = bool(int(args[2]))
    print(OVERWRITE_NFO)
    PLEX = createServer(CONFIGS_PATH)
    print(PLEX)
    writeTVnfo(dry_run=DRY_RUN)
    writeMovieNfo(dry_run=DRY_RUN)

