from nomad.datamodel.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser
from nomad.datamodel.context import ServerContext
from nomad_measurements.utils import create_archive

# Import our specialized Renishaw schema
from nomad_measurements_raman.schema_packages.schema_package import (
    ELNRenishawRaman,
    RawFileRamanData,
)

class RamanParser(MatchingParser):
    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ) -> bool:
        """Gatekeeper for Raman files."""

        filename_lower = filename.lower()

        # 1. Renishaw Check (.wdf)
        if filename_lower.endswith('.wdf'):
            # WDF files are binary, so we just ensure the buffer isn't completely empty.
            if buffer:
                return True

        return False

    def parse(
        self,
        mainfile: str,
        archive: EntryArchive,
        logger=None,
        child_archives=None,
    ) -> None:
        logger = logger or archive.m_context.logger

        # Extract the filename, handling server context paths correctly
        data_file = mainfile.split('/')[-1]
        if isinstance(archive.m_context, ServerContext):
            data_file = mainfile.split('/raw/', 1)[1]

        filename_lower = data_file.lower()

        # Route to the correct Schema based on the file extension
        if filename_lower.endswith('.wdf'):
            entry = ELNRenishawRaman()
        else:
            logger.error(f'Unsupported Raman file format: {data_file}')
            return

        # Assign the file name to the entry
        entry.data_file = data_file

        # Trigger the reader inside the schema's normalize function FIRST
        #entry.normalize(archive, logger)

        # Create the separate editable .archive.json file to preserve ELN edits
        archive_name = f'{"".join(data_file.split(".")[:-1])}.archive.json'
        eln_ref = create_archive(entry, archive, archive_name)

        # Link the raw .wdf file to the generated ELN to prevent the crash and duplication
        archive.data = RawFileRamanData(measurement=eln_ref)
