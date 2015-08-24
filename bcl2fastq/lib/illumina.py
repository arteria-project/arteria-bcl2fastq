
from pandas import read_csv

class SampleRow:
    """
    Provides a representation of the information presented in a Illumina Samplesheet.
    Different samplesheet types (e.g. HiSeq, MiSeq, etc) will provide slightly different
    information for each sample. This class aims at providing a interface to this that will
    hopefully stay relatively stable across time.

    For an example of how the samplesheet looks see: ./tests/sampledata/new_samplesheet_example.csv

    TODO Implement picking up additional information from
    samplesheet. Right only picking up the data field is
    supported.
    """
    def __init__(self, sample_id, sample_name, index1, sample_project, lane=None, sample_plate=None,
                 sample_well=None, index2=None, description=None):
        """
        Constructs the SampleRow, which shadows the information on each sequencing unit (lane, sample, tag, etc)
        in the samplesheet. NB: If a field is set to None, it means that column didn't exist in the samplesheet.
        If it is a empty string it means that it was set to a empty value.
        :param sample_id: unique id of sample
        :param sample_name: the name of the sample
        :param index1: index to demultiplex by
        :param sample_project: project sample belongs to
        :param lane: sequenced on - will default to 1 if not set (e.g. the MiSeq samplesheet does
        not contain lane information
        :param sample_plate: plate the sample was taken from
        :param sample_well: well on plate
        :param index2: second index in the case of dual indexing
        :param description: a free text field containing additional info about the sample
        :return:
        """
        self.lane = int(lane) if lane else 1
        self.sample_id = str(sample_id)
        self.sample_name = str(sample_name)
        self.sample_plate = sample_plate
        self.sample_well = sample_well
        self.index1 = index1
        self.index2 = index2
        self.sample_project = str(sample_project)
        self.description = description

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        if type(other) == type(self):
            return self.__dict__ == other.__dict__
        else:
            False

class Samplesheet:
    """
    Represent information contanied in a Illumina samplesheet
    """

    def __init__(self, samplesheet_file):
        """
        Create a Samplesheet instance.
        :param samplesheet_file: a path to the samplesheet file to read
        """
        self.samplesheet_file = samplesheet_file
        with open(samplesheet_file, mode="r") as s:
            self.samples = self._read_samples(s)

    @staticmethod
    def _read_samples(samplesheet_file_handle):
        """
        Read info about the sequencing units in the samplesheet.
        :param samplesheet_file_handle: file handle for the corresponding samplesheet
        :return: a list of the sequencing units in the samplesheet in the form of `SampleRow` instances.
        """

        def find_data_line():
            enumurated_lines = enumerate(samplesheet_file_handle)
            lines_with_data = filter(lambda x: "[Data]" in x[1], enumurated_lines)
            assert len(lines_with_data) == 1, "The wasn't strictly one line in samplesheet with line '[Data]'"
            return lines_with_data[0][0]

        def row_to_sample_row(index_and_row):
            row = index_and_row[1]
            return SampleRow(lane=row.get("Lane"), sample_id=row.get("Sample_ID"), sample_name=row.get("Sample_Name"),
                             sample_plate=row.get("Sample_Plate"), sample_well=row.get("Sample_Well"),
                             index1=row.get("index"), index2=row.get("index2"),
                             sample_project=row.get("Sample_Project"), description=row.get("Description"))

        lines_to_skip = find_data_line() + 1
        # Ensure that pointer is at beginning of file again.
        samplesheet_file_handle.seek(0)
        samplesheet_df = read_csv(samplesheet_file_handle, skiprows=lines_to_skip)
        samplesheet_df = samplesheet_df.fillna("")
        samples = map(row_to_sample_row, samplesheet_df.iterrows())
        return list(samples)
