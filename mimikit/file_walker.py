import os
from typing import Iterable


class FileWalker:

    AUDIO_EXTENSIONS = {"wav", "aif", "aiff", "mp3", "m4a", "mp4"}
    MIDI_EXTENSIONS = {"mid"}

    def __init__(self, files_ext, items=None):
        """
        recursively find audio files from `roots` and/or collect audio files passed in `files`

        Parameters
        ----------
        files_ext : str or list of str
            type(s) of files to be filtered. Must be either 'audio' or 'midi'.
        items : str or list of str
            a single path (string, os.Path) or an Iterable of paths. Each item can be the root of
            a directory which will be searched recursively or a single file.

        Examples
        --------
        >>> files = list(FileWalker(files_ext='midi', items=["my-root-dir", 'piece.mid']))

        """
        extensions = dict(audio=self.AUDIO_EXTENSIONS, midi=self.MIDI_EXTENSIONS)
        if isinstance(files_ext, str):
            files_ext = [files_ext]
        if not all(ext in ("audio", "midi") for ext in files_ext):
            raise ValueError("Expected all files_ext to be one of 'audio' or 'midi'.")
        self._valid_ext = {ext for file_type in files_ext for ext in extensions[file_type]}

        generators = []

        if items is not None and isinstance(items, Iterable):
            if isinstance(items, str):
                if not os.path.exists(items):
                    raise FileNotFoundError("%s does not exist." % items)
                if os.path.isdir(items):
                    generators += [self.walk_root(items)]
                else:
                    if self.is_matching_file(items):
                        generators += [[items]]
            else:
                for item in items:
                    if not os.path.exists(item):
                        raise FileNotFoundError("%s does not exist." % item)
                    if os.path.isdir(item):
                        generators += [self.walk_root(item)]
                    else:
                        if self.is_matching_file(item):
                            generators += [[item]]

        self.generators = generators

    def __iter__(self):
        for generator in self.generators:
            for file in generator:
                yield file

    def walk_root(self, root):
        for directory, _, files in os.walk(root):
            for file in filter(self.is_matching_file, files):
                yield os.path.join(directory, file)

    def is_matching_file(self, filename):
        # filter out hidden files
        if os.path.split(filename.strip("/"))[-1].startswith("."):
            return False
        return os.path.splitext(filename)[-1].strip(".") in self._valid_ext
