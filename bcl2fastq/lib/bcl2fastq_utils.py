import subprocess
import os
import errno
from itertools import groupby
import logging
import shutil
import time


import xmltodict


from arteria.exceptions import ArteriaUsageException
from bcl2fastq.lib.illumina import Samplesheet

log = logging.getLogger(__name__)


class Bcl2FastqConfig:
    """
    Container for configurations for bcl2fastq.
    Should handle setting up sensible defaults for
    values which have to be set.
    """
    def __init__(self,
                 general_config,
                 bcl2fastq_version,
                 runfolder_input,
                 output,
                 samplesheet=None,
                 barcode_mismatches=None,
                 tiles=None,
                 use_base_mask=None,
                 create_indexes=False,
                 additional_args=None,
                 nbr_of_cores=None):
        """
        Instantiate Bcl2FastqConfig
        :param general_config: a dict containing general configuration.
                               Typlically loaded from arteria-core ConfigurationService
        :param bcl2fastq_version: version of bcl2fastq to run
        :param runfolder_input: the path to the runfolder to run bcl2fastq on
        :param output: where the output of bcl2fastq should be placed
        :param samplesheet: a samplesheet as a raw string - if none is provided the samplesheet in the
                            runfolder will be used. If it is specified this provided string will be
                            written to a file and passed to bcl2fastq.
        :param barcode_mismatches: how many mismatches to allow in tag.
        :param tiles: tiles to include when running bcl2fastq
        :param use_base_mask: base mask to use
        :param create_indexes: Create fastq files for indexes
        :param additional_args: this can be used to pass any other arguments to bcl2fastq
        :param nbr_of_cores: number of cores to run bcl2fastq with
        """

        self.general_config = general_config

        self.runfolder_input = runfolder_input
        self.base_calls_input = runfolder_input + "/Data/Intensities/BaseCalls"

        if not samplesheet:
            self.samplesheet_file = runfolder_input + "/SampleSheet.csv"
        else:
            log.debug("Got a new samplesheet. Will use that instead of the one found in the runfolder.")
            new_samplesheet_file = runfolder_input + "/SampleSheet.csv"

            if os.path.exists(new_samplesheet_file):
                Bcl2FastqConfig.copy_old_samplesheet(new_samplesheet_file)

            Bcl2FastqConfig.write_samplesheet(samplesheet, new_samplesheet_file)
            self.samplesheet_file = new_samplesheet_file

        if bcl2fastq_version:
            self.bcl2fastq_version = bcl2fastq_version
        else:
            self.bcl2fastq_version = Bcl2FastqConfig. \
                get_bcl2fastq_version_from_run_parameters(runfolder_input, general_config)

        if output:
            self.output = output
        else:
            output_base = general_config["default_output_path"]
            runfolder_base_name = os.path.basename(runfolder_input)
            self.output = "{0}/{1}".format(output_base, runfolder_base_name)

        self.barcode_mismatches = barcode_mismatches
        self.tiles = tiles
        # TODO Ensure that this is included in any user facing documentation.
        # Note that for the base mask the "--use-bases-mask" must be included in the
        # commandline passed. E.g. "--use-bases-mask 1:y*,6i,6i, y* --use-bases-mask y*,6i,6i, y* "
        self.use_base_mask = use_base_mask
        self.additional_args = additional_args
        self.create_indexes = create_indexes

        # Nbr of cores to use will default to the number of cpus on the system.
        if nbr_of_cores:
            self.nbr_of_cores = nbr_of_cores
        else:
            import multiprocessing
            self.nbr_of_cores = multiprocessing.cpu_count()

    @staticmethod
    def copy_old_samplesheet(new_samplesheet_file):
        new_path_for_old_samplesheet = new_samplesheet_file + time.strftime("%Y%m%d-%H%M%S")
        log.debug("Original samplesheet: {} copied to: {}. ".
                  format(new_samplesheet_file, new_path_for_old_samplesheet))
        shutil.copy(new_samplesheet_file,  new_path_for_old_samplesheet)

    @staticmethod
    def write_samplesheet(samplesheet_string, new_samplesheet_file):
        with open(new_samplesheet_file, "w") as f:
            f.write(samplesheet_string)

    @staticmethod
    def runinfo_as_dict(runfolder):
        runinfo_path = os.path.join(runfolder, "RunInfo.xml")
        with open(runinfo_path) as f:
            return xmltodict.parse(f.read())

    @staticmethod
    def get_bcl2fastq_version_from_run_parameters(runfolder, config):
        """
        Guess which bcl2fastq version to use based on the machine type
        specified in the runfolder meta data, and the corresponding
        mappings in the config file.
        :param runfolder: to get bcl2fastq version to use for
        :param config: to use matching machine type to bcl2fastq versions
        :return the version of bcl2fastq to use.
        """

        run_info = Bcl2FastqConfig.runinfo_as_dict(runfolder)
        instrument_name = run_info["RunInfo"]["Run"]["Instrument"]

        machine_type_mappings = {"M": "MiSeq",
                                 "D": "HiSeq 2500",
                                 "SN": "HiSeq 2000",
                                 "ST": "HiSeq X",
                                 "A": "NovaSeq",
                                 "NS": "NextSeq 500",
                                 "K": "HiSeq 4000",
                                 "FS": "ISeq 100",
                                 "LH": "NovaSeq X Plus"}

        for key, value in machine_type_mappings.items():
            if instrument_name.startswith(key):
                return config["machine_type"][value]["bcl2fastq_version"]

    @staticmethod
    def get_length_of_indexes(runfolder):
        """
        Will parse runfolder meta data to find the length of the index reads.
        :param runfolder: to get the length of the index reads from.
        :return: a dict with the read number as key and the length of each index as value e.g.:
                 {2: 7, 3: 8}
        """

        run_info = Bcl2FastqConfig.runinfo_as_dict(runfolder)
        reads = run_info["RunInfo"]["Run"]["Reads"]["Read"]

        index_lengths = {}
        for read in reads:
            if read['@IsIndexedRead'] == 'Y':
                index_lengths[int(read['@Number'])] = int(read['@NumCycles'])
        return index_lengths

    @staticmethod
    def is_single_read(runfolder):
        run_info = Bcl2FastqConfig.runinfo_as_dict(runfolder)
        reads = run_info["RunInfo"]["Run"]["Reads"]["Read"]

        nbr_of_reads = len(list(filter(lambda x: not x["@IsIndexedRead"] == 'Y', reads)))
        return nbr_of_reads < 2

    @staticmethod
    def get_bases_mask_per_lane_from_samplesheet(samplesheet, index_lengths, is_single_read):
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
        :param is_single_read: True if this is a single read run, else false.
        :return a dict of the lane and base mask to use, e.g.:
                 { 1:"y*,i7n*,i7n*,y*" , 2:"y*,i5,n*,y*  [etc] }
        """

        def build_index_string(length_tuple):
            """
            Builds the index mask string
            :param length_tuple: a tuple of the length of the index in the samplesheet and in the read, e.g. (3, 5)
            :return: a index string, e.g. "i5n*" or "n*" or "i3", depending on the situation.
            """
            length_of_index_in_samplesheet = length_tuple[0]
            length_of_index_read = length_tuple[1]
            difference = length_of_index_read - length_of_index_in_samplesheet

            if not difference >= 0:
                raise ArteriaUsageException("Sample sheet indicates that index is "
                                       "longer than what was read by the sequencer!")

            if length_of_index_in_samplesheet == 0:
                # If there is no index in the samplesheet, ignore it in the base-mask
                return "n*"

            if difference > 0:
                # Pad the end if there is a difference here.
                return "i" + str(length_of_index_in_samplesheet) + "n*"
            else:
                return "i" + str(length_of_index_in_samplesheet)

        def construct_base_mask(samplesheet_idx_list):
            """
            Will construct the base mask.
            :param samplesheet_idx_list: A list of the indexes in the samplesheet
            :return a base mask string
            """
            samplesheet_idx_list = map(len, samplesheet_idx_list)
            samplesheet_idx_and_read_length_tuples = zip(samplesheet_idx_list, index_lengths.itervalues())
            idx_masks = map(
                build_index_string,
                samplesheet_idx_and_read_length_tuples)

            if is_single_read:
                return ",".join(["y*"] + idx_masks)
            else:
                return ",".join(["y*"] + idx_masks + ["y*"])

        def by_lane(x):
            return x.lane
        sample_rows_sorted_by_lane = sorted(samplesheet.samples, key=by_lane)
        lanes_and_indexes = groupby(sample_rows_sorted_by_lane, by_lane)

        first_sample_in_each_lane = {k: next(v) for k, v in lanes_and_indexes}

        base_masks = {}
        for lane, sample_row in first_sample_in_each_lane.iteritems():
            if sample_row.index2:
                base_masks[lane] = construct_base_mask([sample_row.index1.strip(), sample_row.index2.strip()])
            else:
                base_masks[lane] = construct_base_mask([sample_row.index1.strip(), ""])

        return base_masks


class BCL2FastqRunnerFactory:
    """
    Generates new bcl2fastq runners according to the config passed.
    Will determine the correct runner to use based on the config,
    and the it's known binaries.
    """

    def __init__(self, config):
        """
        Instantiate a new BCL2FastqRunnerFactory
        :param config: to use
        """
        self.config = config
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

    def version(self):
        """
        Get the version of bcl2fastq run. Preferably defer the
        decision of which version it was to the binary (instead of
        trusting that the configured versions are correct).
        :return: the bcl2fastq version used.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def construct_command(self):
        """
        Implement this in subclass
        :return: a command to be run by `run`, or other external command runner.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def validate_output(self):

        def _parent_dir(d):
            return os.path.abspath(os.path.join(d, os.path.pardir))

        abs_path_of_allowed_dirs = map(os.path.abspath, self.config.general_config['allowed_output_folders'])
        is_located_in_parent_dir = _parent_dir(self.config.output) in abs_path_of_allowed_dirs

        if not is_located_in_parent_dir:
            error_string = "Invalid output directory {} was specified." \
                           " Allowed dirs were: {}".format(self.config.output,
                                                           self.config.general_config['allowed_output_folders'])
            log.error(error_string)
            raise ArteriaUsageException(error_string)

    def delete_output(self):
        """
        Delete the output directory if it exists and  the output path is valid
        :return: None
        """
        self.validate_output()
        log.info("Found a directory at output path {}, will remove it.".format(self.config.output))
        try:
            shutil.rmtree(self.config.output)
        except OSError as e:
            # Ignore if the error is of type "No such file or directory"
            if e.errno == errno.ENOENT:
                log.debug("No such output directory, with path: {} will not remove it.".format(self.config.output))
                pass
            else:
                log.error("Got error with error number {} when trying to remove dir: {}".format(e.errno,
                                                                                                self.config.output))
                raise e

    def symlink_output_to_unaligned(self):
        """
        Create a symlink from `runfolder/Unaligned` to what has been defined as the output directory.
        :raises: OSError if there was any problem creating the symlink, except for that it was already
                         there, in which case, do nothing.
        """
        link_path = self.config.runfolder_input + "/Unaligned"
        link_target_path = self.config.output

        try:
            log.debug("Create symlink from {} to {}.".
                      format(link_path,
                             link_target_path))
            os.symlink(link_target_path, link_path)
        except OSError as e:
            if e.errno == os.errno.EEXIST:
                log.warning("Symlink from {} to {} already exits, will remove it and recreate it...".
                            format(link_path, link_target_path))
                log.warning("Removing link: {}".format(link_path))
                os.remove(link_path)
                os.symlink(link_target_path, link_path)
            else:
                log.error("Problem creating symlink from {} to {}. Message: {}".
                          format(link_path, link_target_path, e.message))
                raise e


class BCL2Fastq2xRunner(BCL2FastqRunner):
    """
    Runs bcl2fastq with versions 2.x
    """

    def __init__(self, config, binary):
        BCL2FastqRunner.__init__(self, config, binary)

    def version(self):
        from subprocess import CalledProcessError
        try:
            cmd = " ".join([self.binary,
                            "--version",
                            "--min-log-level=NONE"])
            log.debug("Command generated was: {}".format(cmd))
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            # the bcl2fastq version should be on the second line of the output.
            version = output.splitlines()[1]
            return version
        except CalledProcessError as e:
            log.error("Failed to get version: {0}".format(e.message))
            log.error("The command was: {0}".format(e.cmd))

    def construct_command(self):

        commandline_collection = [
            self.binary,
            "--input-dir", self.config.base_calls_input,
            "--output-dir", self.config.output,
            "--sample-sheet", self.config.samplesheet_file]

        if self.config.barcode_mismatches:
            commandline_collection.append("--barcode-mismatches " + self.config.barcode_mismatches)

        if self.config.tiles:
            commandline_collection.append("--tiles " + self.config.tiles)

        if self.config.create_indexes:
            commandline_collection.append("--create-fastq-for-index-reads")

        if self.config.use_base_mask:
            # Note that for the base mask the "--use-bases-mask" must be included in the
            # commandline passed.
            commandline_collection.append(self.config.use_base_mask)
        else:
            length_of_indexes = Bcl2FastqConfig.get_length_of_indexes(self.config.runfolder_input)
            is_single_read_run = Bcl2FastqConfig.is_single_read(self.config.runfolder_input)
            samplesheet = Samplesheet(self.config.samplesheet_file)
            lanes_and_base_mask = Bcl2FastqConfig. \
                get_bases_mask_per_lane_from_samplesheet(samplesheet, length_of_indexes, is_single_read_run)
            for lane, base_mask in lanes_and_base_mask.iteritems():
                commandline_collection.append("--use-bases-mask {0}:{1}".format(lane, base_mask))

        if self.config.additional_args:
            commandline_collection.append(self.config.additional_args)

        command = " ".join(commandline_collection)
        log.debug("Generated command: " + command)
        return command

class BCL2Fastq1xRunner(BCL2FastqRunner):
    """Runs bcl2fastq with versions 1.x"""

    def __init__(self, config, binary):
        BCL2FastqRunner.__init__(self, config, binary)

    def version(self):
        """
        Since there is no way of extracting the version used in bcl2fastq 1.x we
        will have to trust the the configured version is correct.
        :return: version of bcl2fastq used as specified by config.
        """
        return self.config.bcl2fastq_version

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
            is_single_read_run = Bcl2FastqConfig.is_single_read(self.config.runfolder_input)
            lanes_and_base_mask = \
                Bcl2FastqConfig.get_bases_mask_per_lane_from_samplesheet(
                    samplesheet,
                    length_of_indexes,
                    is_single_read_run)
            base_masks_as_set = set(lanes_and_base_mask.values())

            if len(base_masks_as_set) is 1:
                raise ArteriaUsageException("For bcl2fastq 1.8.4 there is no support for "
                                       "mixing different bases masks for different lanes")

            # Here we are forced to use the same bases mask was always used for all lanes.
            commandline_collection.append("--use_bases_mask " + lanes_and_base_mask.values()[0])

        if self.config.additional_args:
            commandline_collection.append(self.config.additional_args)

        ##################################
        # Then run make
        ##################################

        commandline_collection.append(" && make -j{0}".format(self.config.nbr_of_cores))

        command = " ".join(commandline_collection)
        log.debug("Generated command: " + command)
        return command
