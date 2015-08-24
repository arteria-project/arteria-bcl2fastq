"""
This has been adopted from https://github.com/SciLifeLab/TACA.
"""

import os
import yaml


class Config:
    """
    Configures bcl2fastq. Please note that once the config has been loaded once it will
    not reload.
    """

    CONFIG = {}

    @staticmethod
    def load_config(config_file=None):
        """Loads a configuration file.
        By default it assumes ./config/bcl2fastq.conf.yaml
        If the config has already been loaded, just return it (without
        going back to disk to check it).
        """
        if Config.CONFIG:
            return Config.CONFIG
        else:
            try:
                if not config_file:
                    config_file = os.path.join('./config/', 'bcl2fastq.config.yaml')
                Config.CONFIG = Config._load_yaml_config(config_file)
                return Config.CONFIG
            except IOError:
                raise IOError(("There was a problem loading the configuration file. "
                        "Please make sure that {0} exists and that you have "
                        "read permissions".format(config_file)))

    @staticmethod
    def _load_yaml_config(config_file):
        """Load YAML config file
        :param str config_file: The path to the configuration file.
        :returns: A dict of the parsed config file.
        :rtype: dict
        :raises IOError: If the config file cannot be opened.
        """
        if type(config_file) is file:
            Config.CONFIG.update(yaml.load(config_file) or {})
            return Config.CONFIG
        else:
            try:
                with open(config_file, 'r') as f:
                    return yaml.load(f)
            except IOError as e:
                e.message = "Could not open configuration file \"{}\".".format(config_file)
                raise e