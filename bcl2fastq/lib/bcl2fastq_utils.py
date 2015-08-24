import subprocess
import os.path
from itertools import groupby

from illuminate.metadata import InteropMetadata

from bcl2fastq.lib.config import Config
from bcl2fastq.lib.illumina import Samplesheet

class Bcl2FastqConfig:
    """
    Container for configurations for bcl2fastq.
    Should handle setting up sensible defaults for
    values which have to be set.
    """
    def __init__(self,
                 bcl2fastq_version,
                 runfolder_input,
                 output,
                 barcode_mismatches=None,
                 tiles=None,
                 use_base_mask=None,
                 additional_args=None,
                 nbr_of_cores=None):

        self.runfolder_input = runfolder_input
        self.samplesheet_file = runfolder_input + "/SampleSheet.csv"
        self.base_calls_input = runfolder_input + "/Data/Intensities/BaseCalls"

        if bcl2fastq_version:
            self.bcl2fastq_version = bcl2fastq_version
        else:
            self.bcl2fastq_version = Bcl2FastqConfig.\
                get_bcl2fastq_version_from_run_parameters(runfolder_input)

        if output:
            self.output = output
        else:
            output_base = Config.load_config()["default_output_path"]
            runfolder_base_name = os.path.basename(runfolder_input)
            self.output = "{0}/{1}".format(output_base, runfolder_base_name)

        self.barcode_mismatches = barcode_mismatches
        self.tiles = tiles
        # TODO Ensure that this is included in any user facing documentation.
        # Note that for the base mask the "--use-bases-mask" must be included in the
        # commandline passed. E.g. "--use-bases-mask 1:y*,6i,6i, y* --use-bases-mask y*,6i,6i, y* "
        self.use_base_mask = use_base_mask
        self.additional_args = additional_args

        # Nbr of cores to use will default to the number of cpus on the system.
        if nbr_of_cores:
            self.nbr_of_cores = nbr_of_cores
        else:
            import multiprocessing
            self.nbr_of_cores = multiprocessing.cpu_count()

    @staticmethod
    def get_bcl2fastq_version_from_run_parameters(runfolder, config=None):
        """
        Guess which bcl2fastq version to use based on the machine type
        specified in the runfolder meta data, and the corresponding
        mappings in the config file.
        :param runfolder: to get bcl2fastq version to use for
        :param config: to use matching machine type to bcl2fastq versions (will be
        loaded from default config if not set).
        :return the version of bcl2fastq to use.
        """

        meta_data = InteropMetadata(runfolder)
        model = meta_data.model

        current_config = config or Config.load_config()
        version = current_config["machine_type"][model]["bcl2fastq_version"]

        return version

    @staticmethod
    def get_length_of_indexes(runfolder):
        """
        Will parse runfolder meta data to find the length of the index reads.
        :param runfolder: to get the length of the index reads from.
        :return: a dict with the read number as key and the length of each index as value e.g.:
                 {2: 7, 3: 8}
        """
        meta_data = InteropMetadata(runfolder)
        index_read_info = filter(lambda x: x["is_index"], meta_data.read_config)
        indexes_and_lengths = map(lambda x: (x["read_num"], x["cycles"]), index_read_info)
        return dict(indexes_and_lengths)

    @staticmethod
    def get_bases_mask_per_lane_from_samplesheet(samplesheet, index_lengths):
        """
        Create a bases-mask string per lane for based on the length of the index in the
        provided samplesheet. This assumes that all indexes within a lane have
        the same length.

        If the length read on the machine (as specified in `index_lengths`) is longer
        than the index length specified samplesheet, the base mask will be set to
        mask any extra bases.

        :param samplesheet: samplesheet to fetch the index lengths from
        :param index_lengths: dict of index lengths (e.g. "{1: 7, 2: 8}"),
        normally parsed from run meta data.
        :return a dict of the lane and base mask to use, e.g.:
                 { 1:"y*,iiiiiiiin*,iiiiiiiin*,y*" , 2:"y*,iiiiii,n*,y*  [etc] }
        """
        def is_double_index(idxs):
            return idxs[2]

        def pad_with_ignore(length_of_index_in_samplesheet, length_of_index_read):
            difference = length_of_index_read - length_of_index_in_samplesheet
            assert difference >= 0, "Sample sheet indicates that index is longer than what was read by the sequencer!"
            if difference > 0:
                return "n*"
            else:
                return ""

        def construct_double_index_basemask(index1, index2):
            index1_length = len(index1)
            index2_length = len(index2)
            print index1_length
            print index2_length
            return "y*,{0}{1}{2},{3}{4}{5},y*".format(
                "i", index1_length, pad_with_ignore(index1_length, index_lengths[2]),
                "i", index2_length, pad_with_ignore(index2_length, index_lengths[3]))

        def construct_single_index_basemask(idx, flowcell_has_double_idx):
            idx_length = len(idx)
            if flowcell_has_double_idx:
                return "y*,{0}{1}{2},{3},y*".format(
                    "i", idx_length, pad_with_ignore(idx_length, index_lengths[2]), "n*")
            else:
                return "y*,{0}{1}{2},y*".format("i", idx_length, pad_with_ignore(idx_length, index_lengths[2]))

        def by_lane(x):
            return x.lane
        sample_rows_sorted_by_lane = sorted(samplesheet.samples, key=by_lane)
        lanes_and_indexes = groupby(sample_rows_sorted_by_lane, by_lane)

        first_sample_in_each_lane = {k: next(v) for k, v in lanes_and_indexes}

        contains_double_index = len(index_lengths) > 1

        base_masks = {}
        for lane, sample_row in first_sample_in_each_lane.iteritems():
            if sample_row.index2:
                base_masks[lane] = construct_double_index_basemask(sample_row.index1.strip(), sample_row.index2.strip())
            else:
                base_masks[lane] = construct_single_index_basemask(sample_row.index1.strip(), contains_double_index)

        return base_masks


class BCL2FastqRunnerFactory:
    """
    Generates new bcl2fastq runners according to the config passed.
    Will determine the correct runner to use based on the config,
    and the it's known binaries.
    """

    def __init__(self, config=None):
        config = config or Config.load_config()
        self.bcl2fastq_mappings = config["bcl2fastq"]["versions"]

    def _get_class_creator(self, version):
        """
        Based on the config provided in `bcl2fastq`, and the passed
        version, this will return a function that can be used to provide
        create a appropriate bcl2fastq runner.
        :param: version to look for mapping for
        :return: a function that can be used to create a bcl2fastq runner.
        """

        def _get_bcl2fastq2x_runner(self, config, binary):
            return BCL2Fastq2xRunner(config, binary)

        def _get_bcl2fastq1x_runner(self, config, binary):
            return BCL2Fastq1xRunner(config, binary)

        function_name = self.bcl2fastq_mappings[version]["class_creation_function"]
        function = locals()[function_name]
        return function

    def _get_binary(self, version):
        """
        Get the binary for the bcl2fastq version we are using.
        """
        return self.bcl2fastq_mappings[version]["binary"]

    def create_bcl2fastq_runner(self, config):
        """
        Uses higher order functions to create a correct runner based
        on the config passed to it.
        """
        version = config.bcl2fastq_version
        if version in self.bcl2fastq_mappings:
            clazz = self._get_class_creator(version)
            binary = self._get_binary(version)
            return clazz(self, config, binary)
        else:
            raise LookupError("Couldn't find a valid config mapping for bcl2fastq version {0}.".format(version))


class BCL2FastqRunner(object):
    """
    Base class for bcl2fastq runners. Provides common functionality for running commands, etc.
    """
    def __init__(self, config, binary):
        self.config = config
        self.binary = binary
        self.command = None

    def construct_command(self):
        """
        Implement this in subclass
        :return: a command to be run by `run`, or other external command runner.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def run(self):
        """
        Will run the command provided by `_construct_command`
        :return: True is successfully run, else False.
        """
        #TODO Use logger!
        self.command = self.construct_command()
        print("Running bcl2fastq with command: " + self.command)

        try:
            output = subprocess.check_call(self.command, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            #TODO Figure out better error processing (and logging here).
            print("Failure in running bcl2fastq!")
            print(exc)
            return False
        else:
            print("Successfully finished running bcl2fastq!")
            return True


class BCL2Fastq2xRunner(BCL2FastqRunner):
    """
    Runs bcl2fastq with versions 2.x
    """

    def __init__(self, config, binary):
        BCL2FastqRunner.__init__(self, config, binary)

    def construct_command(self):

        commandline_collection = [
            self.binary,
            "--input-dir", self.config.base_calls_input,
            "--output-dir", self.config.output]

        if self.config.barcode_mismatches:
            commandline_collection.append("--barcode-mismatches " + self.config.barcode_mismatches)

        if self.config.tiles:
            commandline_collection.append("--tiles " + self.config.tiles)

        if self.config.use_base_mask:
            # Note that for the base mask the "--use-bases-mask" must be included in the
            # commandline passed.
            commandline_collection.append(self.config.use_base_mask)
        else:
            length_of_indexes = Bcl2FastqConfig.get_length_of_indexes(self.config.runfolder_input)
            samplesheet = Samplesheet(self.config.samplesheet_file)
            lanes_and_base_mask = Bcl2FastqConfig.\
                get_bases_mask_per_lane_from_samplesheet(samplesheet, length_of_indexes)
            for lane, base_mask in lanes_and_base_mask.iteritems():
                commandline_collection.append("--use-bases-mask {0}:{1}".format(lane, base_mask))

        if self.config.additional_args:
            commandline_collection.append(self.config.additional_args)

        command = " ".join(commandline_collection)
        print("Generated command: " + command)
        return command

class BCL2Fastq1xRunner(BCL2FastqRunner):
    """Runs bcl2fastq with versions 1.x"""

    def __init__(self, config, binary):
        BCL2FastqRunner.__init__(self, config, binary)

    def construct_command(self):

        ##################################
        # First run configureBcl2fastq.pl
        ##################################

        # Assumes configureBclToFastq.pl on path
        commandline_collection = [
            "configureBclToFastq.pl",
            "--input-dir", self.config.base_calls_input,
            "--sample-sheet", self.config.samplesheet_file,
            "--output-dir", self.config.output,
            "--fastq-cluster-count 0", # No upper-limit on number of clusters per output file.
            "--force" # overwrite output if it exists.
        ]

        if self.config.barcode_mismatches:
            commandline_collection.append("--mismatches " + self.config.barcode_mismatches)

        if self.config.tiles:
            commandline_collection.append("--tiles " + self.config.tiles)

        if self.config.use_base_mask:
            commandline_collection.append("--use_bases_mask " + self.config.use_base_mask)
        else:
            length_of_indexes = Bcl2FastqConfig.get_length_of_indexes(self.config.runfolder_input)
            samplesheet = Samplesheet(self.config.samplesheet_file)
            lanes_and_base_mask = \
                Bcl2FastqConfig.get_bases_mask_per_lane_from_samplesheet(samplesheet, length_of_indexes)
            base_masks_as_set = set(lanes_and_base_mask.values())

            assert len(base_masks_as_set) is 1, "For bcl2fastq 1.8.4 there is no support for " \
                                                "mixing different bases masks for different lanes"

            # Here we are forced to use the same bases mask was always used for all lanes.
            commandline_collection.append("--use_bases_mask " + lanes_and_base_mask.values()[0])

        if self.config.additional_args:
            commandline_collection.append(self.config.additional_args)

        ##################################
        # Then run make
        ##################################

        commandline_collection.append(" && make -j{0}".format(self.config.nbr_of_cores))

        command = " ".join(commandline_collection)
        print("Generated command: " + command)
        return command
