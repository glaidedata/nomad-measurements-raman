from nomad.datamodel.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser

# Import our specialized Renishaw schema
from nomad_measurements_raman.schema_packages.schema_package import ELNRenishawRaman


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

        # Extract just the filename from the path
        filename = mainfile.rsplit('/', maxsplit=1)[-1]
        filename_lower = filename.lower()

        # Route to the correct Schema based on the file extension
        if filename_lower.endswith('.wdf'):
            entry = ELNRenishawRaman()
        else:
            logger.error(f'Unsupported Raman file format: {filename}')
            return

        # Assign the file and attach the schema to the archive
        entry.data_file = filename
        archive.data = entry

        # Trigger the reader inside the schema's normalize function
        entry.normalize(archive, logger)
