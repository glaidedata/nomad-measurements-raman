from unittest.mock import MagicMock, patch

import numpy as np
from nomad.datamodel.datamodel import EntryArchive, EntryMetadata

from nomad_measurements_raman.schema_packages.schema_package import ELNRenishawRaman


@patch('nomad_measurements_raman.schema_packages.schema_package.read_renishaw_wdf')
def test_renishaw_schema_normalization(mock_read_renishaw_wdf):
    """Verifies that the schema extracts metadata and shapes 3D mapping data."""

    mock_data = MagicMock()

    mock_data.metadata = {
        'application_name': 'WiRE',
        'laser_length': 532.0,
        'accumulation_count': 5,
        'measurement_time': 2.5,
        'scan_type': 'Mapping',
    }

    mock_data.wavenumber = np.linspace(100, 3000, 10)
    mock_data.spectra = np.ones((2, 2, 10))  # 2x2 spatial grid, 10 spectral points
    mock_data.xpos = np.array([0.0, 1.0])
    mock_data.ypos = np.array([0.0, 1.0])

    mock_read_renishaw_wdf.return_value = mock_data

    # Setup the mock NOMAD environment context
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name='test_map.wdf')

    mock_context = MagicMock()
    mock_file = MagicMock()
    mock_file.name = 'test_map.wdf'
    mock_context.raw_file.return_value.__enter__.return_value = mock_file
    archive.m_context = mock_context

    # Initialize schema and trigger normalization
    schema = ELNRenishawRaman(data_file='test_map.wdf')
    schema.normalize(archive, MagicMock())

    # Assert Top-Level Metadata
    assert schema.instrument_model == 'Renishaw InVia'

    assert schema.laser_setup.wavelength.magnitude == 532.0  # noqa PLR2004

    assert schema.acquisition_setup.accumulations == 5  # noqa PLR2004
    assert schema.acquisition_setup.exposure_time.magnitude == 2.5  # noqa PLR2004
    assert schema.acquisition_setup.scan_type == 'Mapping'

    # Assert Data Array Processing
    data_section = schema.results[0].data

    assert data_section.x_positions is not None
    assert len(data_section.x_positions.magnitude) == 2  # noqa PLR2004

    assert data_section.map_data is not None
    assert data_section.map_data.shape == (2, 2, 10)

    assert data_section.mean_spectrum is not None
    assert data_section.mean_spectrum.shape == (10,)
    assert data_section.intensity_map is not None
    assert data_section.intensity_map.shape == (2, 2)
