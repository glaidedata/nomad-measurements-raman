from nomad.config.models.plugins import ParserEntryPoint


class RamanParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements_raman.parsers.parser import RamanParser

        return RamanParser(**self.dict())


parser_entry_point = RamanParserEntryPoint(
    name='Raman Parser',
    description='Parser for Raman Spectroscopy files.',
    mainfile_name_re=r'^.*\.(wdf)$',
)
