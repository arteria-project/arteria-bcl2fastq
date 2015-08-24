
class TestUtils:

    DUMMY_CONFIG = { "runfolder_path": "/data/biotank3/runfolders",
                     "default_output_path": "test",
                     "bcl2fastq":
                         {"versions":
                              {"2.15.2":
                                   {"class_creation_function": "_get_bcl2fastq2x_runner",
                                    "binary": "/path/to/bcl2fastq"},
                               "1.8.4":
                                   {"class_creation_function": "_get_bcl2fastq1x_runner",
                                    "binary": "/path/to/bcl2fastq"}}},
                     "machine_type":
                         {"MiSeq": {"bcl2fastq_version": "1.8.4"},
                          "HiSeq X": {"bcl2fastq_version": "2.15.2"},
                          "HiSeq 2500": {"bcl2fastq_version": "1.8.4"},
                          "HiSeq 4000": {"bcl2fastq_version": "1.8.4"},
                          "HiSeq 2000": {"bcl2fastq_version": "1.8.4"},
                          "NextSeq 500": {"bcl2fastq_version": "1.8.4"}},
                     "bcl2fastq_logs_path": "/tmp/"}