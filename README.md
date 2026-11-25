# plex2nfo

This command line tool grew out of frustration. I wanted to migrate from Plex to Jellyfin, but I had meticulously edited episode metadata in Plex for shows that like to be special (e.g. Doctor Who (2005), Batman: The Animated Series). I didn't want to manually do all that again, but all of the tools that existed to generate nfo files for Plex either (1) only worked with movies, (2) only pulled from external metadata providers, or (3) were AI vibe-coded garbage. **So, I wrote this from scratch to facilitate my migration.**

**ABSOLUTELY NO AI WAS USED TO WRITE THIS TOOL**

I know this is incomplete and a bit crude. I had hoped to have time to develop this properly, but since [Plex is deprecating TVDB on December 3, 2026](https://forums.plex.tv/t/upcoming-change-thetvdb-metadata-support-ending-on-december-3rd/9462150), I had to write this quickly to ensure no loss of custom metadata.

## Installation

Clone the repository: `git clone git@github.com:meyersbs/plex2nfo.git`

Install the dependencies in your favorite python environment: `pip install -r requirements.txt`

## Configuration

You need to set up a config file that contains your baseurl and X-Plex-Token:

```
$ cat ~/.plex2nfo/config
<BASEURL>
<X-PLEX-TOKEN>
```

You can find your baseurl in the Plex Web Client: Settings --> Remote Access. I used the private IP and port.

You can find your `X-Plex-Token` by [following these instructions](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

For example:

```
$ cat ~/.plex2nfo/config
http://12.34.56.789:32400
B-6DGpm_fK8xYTQNOPgT
```

## Usage

Command line takes two arguments:
- Config File: Path to the configuration file containing your baseurl and X-Plex-Token
- Dry Run: Boolean. 0 = Write NFO files to disk. 1 = Print out what would be written to disk, but don't actually do it.
- Overwrite NFO: Boolean. 1 = Overwrite existing NFO files. 0 = Don't overwrite existing NFO files.
- Verbose Output: Boolean. 0 = Don't show excessive output. 1 = Show excessive output.

Do a dry run without writing any data to disk, normal output:
```
python3 plex2nfo.py ~/.plex2nfo/config 1 0 0
```

Write NFO files to disk without overwriting existing NFO files, normal output:
```
python3 plex2nfo.py ~/.plex2nfo/config 0 0 0
```

Write NFO files to disk with overwriting enabled, verbose output:
```
python3 plex2nfo.py ~/.plex2nfo/config 0 1 1
```

## Notes

- This code is designed to run on the same host as your Plex server. It may work remotely, but I haven't tested it.
- This code does not modify any of your Plex metadata.
- This does not write all of the metadata available for a file, only the ones that I (and I assume others) are likely to modify by hand, e.g. title, summary, air date. If you want to write others, I welcome pull requests.
- This code does not write posters or thumbnails to disk since I do that manually when I add a new show/movie. If you want that functionality, I welcome pull requests.

## Contribute

I welcome pull requests for additional features. Pull requests that contain AI written code will not be merged.

## License

[MIT](LICENSE)

## References

- https://python-plexapi.readthedocs.io/en/latest/introduction.html
- https://jellyfin.org/docs/general/server/metadata/nfo/
- https://kodi.wiki/view/NFO_files/Templates
