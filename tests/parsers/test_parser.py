from unittest.mock import MagicMock, patch

from nomad.datamodel.datamodel import EntryArchive, EntryMetadata

from nomad_measurements_raman.parsers.parser import RamanParser
from nomad_measurements_raman.schema_packages.schema_package import (
    ELNRenishawRaman,
    RawFileRamanData,
)


@patch('nomad_measurements_raman.parsers.parser.create_archive')
def test_renishaw_parser(mock_create_archive):
    """Verifies the parser correctly routes .wdf files using the Two-Archive pattern."""

    # Mock the reference string returned by create_archive
    mock_create_archive.return_value = 'mocked_archive_reference'

    # Setup the mock NOMAD environment context
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name='dummy_measurement.wdf')

    mock_context = MagicMock()
    archive.m_context = mock_context
    logger = MagicMock()

    # Execute the parser
    parser = RamanParser()
    parser.parse('path/to/dummy_measurement.wdf', archive, logger)

    # Assertions for the main raw file
    assert isinstance(archive.data, RawFileRamanData)
    assert archive.data.measurement.m_proxy_value == 'mocked_archive_reference'

    # Assertions to ensure the ELN archive was created with the correct data
    mock_create_archive.assert_called_once()
    entry, _, archive_name = mock_create_archive.call_args[0]

    assert isinstance(entry, ELNRenishawRaman)
    assert entry.data_file == 'dummy_measurement.wdf'
    assert archive_name == 'dummy_measurement.archive.json'
