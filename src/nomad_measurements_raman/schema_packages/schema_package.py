from typing import TYPE_CHECKING

import numpy as np

# Import the base class for IEntrance instruments
from ientrance_instruments.schema_packages.schema_package import IEntranceInstrument
from nomad.datamodel.data import JSON, ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import ELNComponentEnum
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection

# Import the reader from your readers package
from readers_ientrance import read_renishaw_wdf

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = SchemaPackage()


# ==========================================
# 1. SHARED RAMAN SETUP SECTIONS
# ==========================================
class RamanLaserSetup(ArchiveSection):
    """Details about the excitation laser."""

    wavelength = Quantity(
        type=np.float64, unit='nm', description='Wavelength of the excitation laser.'
    )
    power = Quantity(
        type=np.float64, unit='mW', description='Laser power at the sample.'
    )
    power_percent = Quantity(
        type=np.float64,
        description='Laser power as a percentage of the maximum source power.',
    )


class RamanInstrumentSetup(ArchiveSection):
    """Details about the spectrometer and microscope."""

    objective_magnification = Quantity(
        type=str, description='Microscope objective magnification (e.g., 100x).'
    )
    grating = Quantity(
        type=np.float64, unit='1/mm', description='Grating groove density (lines/mm).'
    )
    pinhole_size = Quantity(
        type=np.float64, unit='um', description='Confocal pinhole or slit size.'
    )


class RamanAcquisitionSetup(ArchiveSection):
    """Parameters governing how the measurement was executed."""

    exposure_time = Quantity(
        type=np.float64, unit='s', description='Integration/exposure time per spectrum.'
    )
    accumulations = Quantity(
        type=np.int32, description='Number of accumulated spectra per point.'
    )
    scan_type = Quantity(
        type=str, description='Type of scan (e.g., Static, Extended, Mapping).'
    )


# ==========================================
# 2. SHARED RAMAN RESULTS
# ==========================================
class RamanData(ArchiveSection):
    """A section to hold the Raman spectral data and coordinates."""

    m_def = Section(
        a_plot=[
            dict(
                label='Mean Spectrum',
                x='wavenumber',
                y='mean_spectrum',
                lines=[dict(mode='lines')],
            ),
            dict(
                label='Total Intensity Map',
                x='x_positions',
                y='y_positions',
                z='intensity_map',
                type='heatmap',
            ),
        ]
    )

    wavenumber = Quantity(
        type=np.float64,
        shape=['*'],
        unit='1/cm',
        description='The Raman shift/wavenumber array.',
    )

    spectrum_data = Quantity(
        type=np.float64,
        shape=['*'],
        description='1D array for a single-point Raman spectrum.',
    )

    mean_spectrum = Quantity(
        type=np.float64,
        shape=['*'],
        description='The averaged 1D spectrum across the entire mapping grid.',
    )

    intensity_map = Quantity(
        type=np.float64,
        shape=['*', '*'],
        description='2D map of the total spectral intensity at each spatial point.',
    )

    map_data = Quantity(
        type=np.float64,
        shape=['*', '*', '*'],
        description='3D array for mapped Raman spectra (e.g., [Y, X, Wavenumber]).',
        a_browser=dict(render=False),
    )

    x_positions = Quantity(
        type=np.float64,
        shape=['*'],
        unit='um',
        description='X coordinates for mapped measurements.',
    )

    y_positions = Quantity(
        type=np.float64,
        shape=['*'],
        unit='um',
        description='Y coordinates for mapped measurements.',
    )


class RamanResult(MeasurementResult):
    data = SubSection(section_def=RamanData)


# ==========================================
# 3. BASE RAMAN ENTRY
# ==========================================
class BaseRamanSpectroscopy(Measurement):
    """Base class containing shared attributes for all Raman entries."""

    # We define a hidden field using the custom instrument type.
    # Its ONLY purpose is to preload the IEntranceInstrument schema
    _instrument_schema_preload = Quantity(type=IEntranceInstrument)

    data_file = Quantity(
        type=str,
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor'),
        description='The raw Raman data file.',
    )

    instrument_model = Quantity(
        type=str,
        description='The model of the Raman instrument.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    software_version = Quantity(
        type=str,
        description='Software used to record the spectra.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    raw_metadata = Quantity(
        type=JSON,
        description='A complete dictionary dump of unparsed header metadata.',
    )

    laser_setup = SubSection(section_def=RamanLaserSetup)
    instrument_setup = SubSection(section_def=RamanInstrumentSetup)
    acquisition_setup = SubSection(section_def=RamanAcquisitionSetup)
    results = SubSection(section_def=RamanResult, repeats=True)


# ==========================================
# 4. RENISHAW SPECIFIC SCHEMA
# ==========================================
class ELNRenishawRaman(BaseRamanSpectroscopy, EntryData):
    m_def = Section(
        label='Renishaw Raman Spectroscopy',
        a_eln=dict(lane_width='600px'),
        a_template=dict(measurement_identifiers=dict()),
    )

    def _init_subsections(self):
        """Helper method to initialize empty schema sections."""
        if not self.laser_setup:
            self.laser_setup = RamanLaserSetup()
        if not self.acquisition_setup:
            self.acquisition_setup = RamanAcquisitionSetup()
        if not self.instrument_setup:
            self.instrument_setup = RamanInstrumentSetup()
        if not self.results:
            self.results = [RamanResult()]
        if not self.results[0].data:
            self.results[0].data = RamanData()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        if not self.data_file:
            super().normalize(archive, logger)
            return

        try:
            # 1. Get the absolute OS path directly without closing the file handle
            file_path = archive.m_context.upload_files.raw_file_object(
                self.data_file
            ).os_path

            wdf_data = read_renishaw_wdf(file_path)

            # 2. Map Top-Level Metadata
            self.instrument_model = 'Renishaw InVia'
            self.software_version = wdf_data.metadata.get('application_name', 'WiRE')
            self.raw_metadata = wdf_data.metadata

            # Initialize Subsections
            self._init_subsections()

            # 3. Map Setup Parameters
            laser_length = wdf_data.metadata.get('laser_length')
            if laser_length:
                self.laser_setup.wavelength = float(laser_length)

            acc_count = wdf_data.metadata.get('accumulation_count')
            if acc_count:
                self.acquisition_setup.accumulations = int(acc_count)

            meas_time = wdf_data.metadata.get('measurement_time')
            if meas_time is not None:
                self.acquisition_setup.exposure_time = float(meas_time)
            raw_scan_type = wdf_data.metadata.get('scan_type', 'Unknown')
            self.acquisition_setup.scan_type = getattr(
                raw_scan_type, 'name', str(raw_scan_type)
            )

            # 4. Map the Matrices / Data Shapes
            raman_data = self.results[0].data

            if wdf_data.wavenumber is not None:
                raman_data.wavenumber = wdf_data.wavenumber

            if wdf_data.spectra is not None:
                mapping_dimensions = 3
                if wdf_data.spectra.ndim == 1:
                    # Single point scan
                    raman_data.spectrum_data = wdf_data.spectra
                    raman_data.mean_spectrum = wdf_data.spectra
                elif wdf_data.spectra.ndim == mapping_dimensions:
                    # Mapping scan
                    raman_data.map_data = wdf_data.spectra
                    # Calculate the average spectrum across the whole 11x11 grid
                    raman_data.mean_spectrum = np.mean(wdf_data.spectra, axis=(0, 1))
                    # Calculate a 2D heatmap summing up the intensity at each point
                    raman_data.intensity_map = np.sum(wdf_data.spectra, axis=2)

            if wdf_data.xpos is not None:
                raman_data.x_positions = wdf_data.xpos
            if wdf_data.ypos is not None:
                raman_data.y_positions = wdf_data.ypos

        except Exception as e:
            if logger:
                logger.error(f'Error parsing Renishaw WDF file: {e}')
            raise e

        super().normalize(archive, logger)


class RawFileRamanData(EntryData):
    """Placeholder for the raw WDF file to point to the generated ELN."""

    m_def = Section(label='Raw Raman Data File')

    measurement = Quantity(
        type=ELNRenishawRaman,
        a_eln=dict(component=ELNComponentEnum.ReferenceEditQuantity),
        description='The editable ELN archive generated from this raw file.',
    )


m_package.__init_metainfo__()
