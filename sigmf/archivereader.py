# Copyright: Multiple Authors
#
# This file is part of SigMF. https://github.com/gnuradio/SigMF
#
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Access SigMF archives without extracting them."""

import os
import tarfile
import warnings

from .sigmffile import SigMFFile
from .archive import (SIGMF_COLLECTION_EXT,
                      SIGMF_DATASET_EXT,
                      SIGMF_METADATA_EXT,
                      SIGMF_ARCHIVE_EXT)
from .error import SigMFFileError


class ArchiveRecording:
    """Holds TarInfo objects found in archive for a recording"""
    def __init__(self) -> None:
        self.metadata = None
        self.data = None


class SigMFArchiveReader():
    """Access data within SigMF archive `tar` in-place without extracting. This
    class can be used to iterate through multiple SigMFFiles in the archive.

    Parameters:

      path    -- path to archive file to access. If file does not exist,
                 or if `path` doesn't end in .sigmf, SigMFFileError is raised.

    self.sigmffiles will contain the SigMFFile(s) (metadata/data) found in the
    archive.
    """
    def __init__(self,
                 path=None,
                 skip_checksum=False,
                 map_readonly=True,
                 archive_buffer=None):
        self.path = path
        tar_obj = None
        try:
            if self.path is not None:
                if not self.path.endswith(SIGMF_ARCHIVE_EXT):
                    err = "archive extension != {}".format(SIGMF_ARCHIVE_EXT)
                    raise SigMFFileError(err)

                tar_obj = tarfile.open(self.path)

            elif archive_buffer is not None:
                tar_obj = tarfile.open(fileobj=archive_buffer, mode='r:')

            else:
                raise ValueError('In sigmf.archivereader.__init__(), either '
                                 '`path` or `archive_buffer` must be not None')

            json_contents = None
            data_offset_size = None
            sigmffile_name = None
            self.sigmffiles = []
            recordings = []

            recording = ArchiveRecording()
            for memb in tar_obj.getmembers():
                if memb.isdir():  # memb.type == tarfile.DIRTYPE:
                    # the directory structure will be reflected in the member
                    # name
                    continue

                elif memb.isfile():  # memb.type == tarfile.REGTYPE:
                    if memb.name.endswith(SIGMF_METADATA_EXT):
                        if recording.metadata:
                            # save previous recording
                            recordings.append(recording)
                            recording = ArchiveRecording()
                        recording.metadata = memb
                    elif memb.name.endswith(SIGMF_DATASET_EXT):
                        recording.data = memb
                    elif memb.name.endswith(SIGMF_COLLECTION_EXT):
                        print('A SigMF Collection file ',
                              memb.name,
                              'was found but not handled.')
                    else:
                        print('A regular file',
                              memb.name,
                              'was found but ignored in the archive')
                else:
                    print('A member of type',
                          memb.type,
                          'and name',
                          memb.name,
                          'was found but not handled, just FYI.')

            if recording.metadata:
                recordings.append(recording)  # save final recording

            if recordings:
                for recording in recordings:
                    metadata = recording.metadata
                    sigmffile_name, _ = os.path.splitext(metadata.name)
                    sigmffile_name = os.path.dirname(sigmffile_name)
                    with tar_obj.extractfile(metadata) as memb_fid:
                        json_contents = memb_fid.read()
                    sigmffile = SigMFFile(sigmffile_name,
                                          metadata=json_contents)

                    sigmffile.validate()
                    data = recording.data
                    if data:
                        data_offset_size = data.offset_data, data.size
                        sigmffile.set_data_file(self.path,
                                                data_buffer=archive_buffer,
                                                skip_checksum=skip_checksum,
                                                offset=data_offset_size[0],
                                                size_bytes=data_offset_size[1],
                                                map_readonly=map_readonly)

                    self.sigmffiles.append(sigmffile)

            if not any([r.data for r in recordings]):
                warnings.warn(f"No file with {SIGMF_DATASET_EXT} extension"
                              " found in archive!")
        finally:
            if tar_obj:
                tar_obj.close()

    def __len__(self):
        return len(self.sigmffiles)

    def __iter__(self):
        return self.sigmffiles.__iter__()

    def __getitem__(self, sli):
        return self.sigmffiles.__getitem__(sli)
