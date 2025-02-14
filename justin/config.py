"""
Justin daemon config parsing
"""

from configparser import ConfigParser
from pathlib import Path
import logging
import re

from .machine import CONTAINERS, ContainerConfigFile

class Config:
    def __init__(self):
        self.control_socket = None
        self.name = None
        self.control_socket_permissions = None
        self.control_socket_group = None
        self.ssh_port_range = (None, None)

        # machinename -> machineconfig
        # config created by Container.config()
        self.machines = dict()

    def load(self, filename, shell=False):
        cfg = ConfigParser()

        if not Path(filename).exists():
            print("\x1b[31mConfig file '%s' does not exist.\x1b[m" % (
                filename))
            exit(1)

        cfg.read(filename)

        try:
            justincfg = cfg["justin"]

            self.name = justincfg["name"]
            self.control_socket = justincfg["control_socket"]

            self.control_socket_permissions = (
                justincfg.get("control_socket_permissions"))

            self.control_socket_group = (
                justincfg.get("control_socket_group"))

            # ssh ports may be a range or a single port
            ssh_port_range = justincfg["vm_ports"]
            mat = re.match(r"\[(\d+),(\d+)\]", ssh_port_range)
            if mat:
                # port range
                lower, upper = int(mat.group(1)), int(mat.group(2))
                if not lower <= upper:
                    raise ValueError("invalid port range (>): [%d,%d]" % (
                        lower, upper))
                self.ssh_port_range = lower, upper
            else:
                raise ValueError("vm_ports malformed, should be =[from,to]")

            # further config ideas:
            # max parallel machines, memory usage checking

        except KeyError as exc:
            print("\x1b[31mConfig file is missing entry: %s\x1b[m" % (exc))
            exit(1)

        if not shell:
            cfgpath = Path(filename).parent
            self.load_machines(cfg, cfgpath)

        self.verify()

    def load_machines(self, cfg, cfgpath):
        for machineid, machinecfg in cfg.items():
            if machineid in ("justin", "DEFAULT"):
                # is for the main config above.
                continue
            elif machineid in self.machines:
                raise ValueError("Machine %s specified more than once" % (
                    machineid))

            if "type" not in machinecfg:
                raise KeyError("Machine %s has no type=" % (machineid))

            machineclassname = machinecfg["type"]
            try:
                machineclass = CONTAINERS[machineclassname]
            except KeyError:
                raise ValueError(f"Unknown Machine type {machineclassname!r}") from None

            # each machine type requests different config options,
            # these are parsed here.
            machineconfig = machineclass.config(machineid,
                                                machinecfg,
                                                cfgpath)

            if not isinstance(machineconfig, ContainerConfigFile):
                raise Exception("'%s' did not return ContainerConfigFile" % (
                    machineclassname))

            self.machines[machineid] = (machineconfig, machineclass)
            logging.debug("[cfg] loaded machine %s (%s)",
                          machineid,
                          machineclassname)

    def verify(self):
        """ Verifies the validity of the loaded config attributes """
        # TODO
        pass


# global justin configuration instance
CFG = Config()
