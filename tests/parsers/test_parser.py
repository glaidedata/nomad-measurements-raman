from unittest.mock import MagicMock, patch

from nomad.datamodel.datamodel import EntryArchive, EntryMetadata
from nomad_measurements_raman.parsers.parser import RamanParser
from nomad_measurements_raman.schema_packages.schema_package import ELNRenishawRaman


@patch('nomad_measurements_raman.schema_packages.schema_package.read_renishaw_wdf')
def test_renishaw_parser(mock_read_renishaw_wdf):
    """Verifies the parser correctly routes .wdf files to the Renishaw schema."""

    mock_data = MagicMock()
    mock_data.metadata = {'application_name': 'WiRE Test'}
    mock_data.wavenumber = None
    mock_data.spectra = None
    mock_data.xpos = None
    mock_data.ypos = None

    mock_read_renishaw_wdf.return_value = mock_data

    # Setup the mock NOMAD environment context
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name='dummy_measurement.wdf')

    mock_context = MagicMock()
    mock_file = MagicMock()
    mock_file.name = 'dummy_measurement.wdf'
    mock_context.raw_file.return_value.__enter__.return_value = mock_file
    archive.m_context = mock_context
    logger = MagicMock()

    # Execute the parser
    parser = RamanParser()
    parser.parse('path/to/dummy_measurement.wdf', archive, logger)

    # Assertions
    assert isinstance(archive.data, ELNRenishawRaman)
    assert archive.data.data_file == 'dummy_measurement.wdf'
    assert archive.data.instrument_model == 'Renishaw InVia'
    assert archive.data.software_version == 'WiRE Test'