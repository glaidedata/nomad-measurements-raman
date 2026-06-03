import datetime
import numpy as np
from typing import TYPE_CHECKING, Any

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
        type=np.float64,
        unit='nm',
        description='Wavelength of the excitation laser.'
    )
    power = Quantity(
        type=np.float64,
        unit='mW',
        description='Laser power at the sample.'
    )
    power_percent = Quantity(
        type=np.float64,
        description='Laser power as a percentage of the maximum source power.'
    )

class RamanInstrumentSetup(ArchiveSection):
    """Details about the spectrometer and microscope."""
    objective_magnification = Quantity(
        type=str,
        description='Microscope objective magnification (e.g., 100x).'
    )
    grating = Quantity(
        type=np.float64,
        unit='1/mm',
        description='Grating groove density (lines/mm).'
    )
    pinhole_size = Quantity(
        type=np.float64,
        unit='um',
        description='Confocal pinhole or slit size.'
    )

class RamanAcquisitionSetup(ArchiveSection):
    """Parameters governing how the measurement was executed."""
    exposure_time = Quantity(
        type=np.float64,
        unit='s',
        description='Integration/exposure time per spectrum.'
    )
    accumulations = Quantity(
        type=np.int32,
        description='Number of accumulated spectra per point.'
    )
    scan_type = Quantity(
        type=str,
        description='Type of scan (e.g., Static, Extended, Mapping).'
    )


# ==========================================
# 2. SHARED RAMAN RESULTS
# ==========================================
class RamanData(ArchiveSection):
    """A section to hold the Raman spectral data and coordinates."""

    wavenumber = Quantity(
        type=np.float64,
        shape=['*'],
        unit='1/cm',
        description='The Raman shift/wavenumber array.'
    )

    spectrum_data = Quantity(
        type=np.float64,
        shape=['*'],
        description='1D array for a single-point Raman spectrum.'
    )

    map_data = Quantity(
        type=np.float64,
        shape=['*', '*', '*'],
        description='3D array for mapped Raman spectra (e.g., [Y, X, Wavenumber]).'
    )

    x_positions = Quantity(
        type=np.float64,
        shape=['*'],
        unit='um',
        description='X coordinates for mapped measurements.'
    )

    y_positions = Quantity(
        type=np.float64,
        shape=['*'],
        unit='um',
        description='Y coordinates for mapped measurements.'
    )

class RamanResult(MeasurementResult):
    data = SubSection(section_def=RamanData)


# ==========================================
# 3. BASE RAMAN ENTRY
# ==========================================
class BaseRamanSpectroscopy(Measurement):
    """Base class containing shared attributes for all Raman entries."""

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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        if not self.data_file:
            super().normalize(archive, logger)
            return

        try:
            # 1. Read the file using the external reader
            with archive.m_context.raw_file(self.data_file, 'rb') as f:
                # We pass the file path to the reader
                file_path = f.name

            wdf_data = read_renishaw_wdf(file_path)

            # 2. Map Top-Level Metadata
            self.instrument_model = 'Renishaw InVia'
            self.software_version = wdf_data.metadata.get('application_name', 'WiRE')
            self.raw_metadata = wdf_data.metadata

            # Initialize Subsections
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

            self.acquisition_setup.scan_type = wdf_data.metadata.get('scan_type', 'Unknown')

            # 4. Map the Matrices / Data Shapes
            raman_data = self.results[0].data

            if wdf_data.wavenumber is not None:
                raman_data.wavenumber = wdf_data.wavenumber

            if wdf_data.spectra is not None:
                if wdf_data.spectra.ndim == 1:
                    raman_data.spectrum_data = wdf_data.spectra
                elif wdf_data.spectra.ndim == 3:
                    raman_data.map_data = wdf_data.spectra

            if wdf_data.xpos is not None:
                raman_data.x_positions = wdf_data.xpos
            if wdf_data.ypos is not None:
                raman_data.y_positions = wdf_data.ypos

        except Exception as e:
            if logger:
                logger.error(f'Error parsing Renishaw WDF file: {e}')
            raise e

        super().normalize(archive, logger)

m_package.__init_metainfo__()