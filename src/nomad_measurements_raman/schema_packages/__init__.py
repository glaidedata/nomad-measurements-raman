from nomad.config.models.plugins import SchemaPackageEntryPoint


class RamanSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements_raman.schema_packages.schema_package import m_package

        return m_package


schema_package_entry_point = RamanSchemaPackageEntryPoint(
    name='Raman Schema',
    description='Schema package for Raman Spectroscopy measurements.',
)
