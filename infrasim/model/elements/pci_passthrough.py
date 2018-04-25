import os
import struct
import re
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect
from infrasim import InfraSimError
from infrasim import logger

class CPCIEPassthrough(CElement):
    def __init__(self, passthrough_info):
        super(CPCIEPassthrough, self).__init__()
        self.__pci_dev_info = passthrough_info
        self.__host_bdf = None
        self.__target_driver = None
        self.__dev_sysfs = []

    def precheck(self):
        pass

    def __read_config(self, device_bdf, offset, size):
        sizes = {8: "Q", 4: "I", 2: "H", 1: "B"}
        pci_config_path = "/sys/bus/pci/devices/{}/config".format(device_bdf)
        v = None
        try:
            fd = os.open(pci_config_path, os.O_RDONLY)
            os.lseek(fd, offset, os.SEEK_SET)
            v = struct.unpack(sizes[size], os.read(fd, size))[0]
        except Exception as e:
            logger.error("read_config: {}".format(e))
        finally:
            return v


    def init(self):
        self.__host_bdf = self.__pci_dev_info.get("host")
        if self.__host_bdf is None:
            raise ArgsNotCorrect("host should be set.")

        self.__target_driver = self.__pci_dev_info.get("driver", "vfio-pci")
        if self.__target_driver not in ["vfio-pci", "pci-stub"]:
            raise ArgsNotCorrect("{} not supported".format(self.__target_driver))

        if self.__target_driver == "vfio-pci":
            os.system("modprobe vfio-pci")
        else:
            os.system("modprobe pci-stub")

        if not re.search(r'\d{4}:[0-9a-fA-F]{2}:\d{2}\.\d+$', self.__host_bdf):
            raise ArgsNotCorrect("BDF should be Domain:Bus:Device.Function")

        target_dev_sysfs_path = "/sys/bus/pci/devices/{}".format(self.__host_bdf)

        if not os.path.exists(target_dev_sysfs_path):
            raise InfraSimError("No such device {}".format(self.__host_bdf))

        if not os.path.exists(os.path.join(target_dev_sysfs_path, "iommu")):
            raise InfraSimError("No IOMMU found. Check your hardware and/or linux parameters, use intel_iommu=on")

        self.__get_dev_sysfs_path_in_iommu_group(self.__host_bdf)
        self.bind()

    def __get_dev_sysfs_path_in_iommu_group(self, device_bdf):
        target_path = "/sys/bus/pci/devices/{}/iommu_group/devices".format(device_bdf)
        for bdf in os.listdir(target_path):
            v = self.__read_config(bdf, 0x0e, 1)
            if v & 0x7f == 0:
                self.__dev_sysfs.append(bdf)

    def handle_parms(self):
        if self.__target_driver == "vfio-pci":
            device = "vfio-pci"
        else:
            device = "pci-assign"

        device_option = "-device {},host={}".format(device, self.__host_bdf)
        logger.info("{}".format(device_option))
        self.add_option(device_option)

    def bind(self):
        device_prefix = "/sys/bus/pci/devices"
        driver_prefix = "/sys/bus/pci/drivers"
        for device_bdf in self.__dev_sysfs:
            fd = os.open("{}/{}/driver_override".format(device_prefix, device_bdf), os.O_RDWR)
            os.write(fd, self.__target_driver)
            driver_path = "{}/{}/driver".format(device_prefix, device_bdf)
            if os.path.exists(driver_path):
                current_driver = os.path.basename(os.readlink(driver_path))
                logger.info("Binding driver from {} to {} for {}".format(current_driver, self.__target_driver, device_bdf))
                if current_driver == self.__target_driver:
                    logger.warn("{} is already bound to {}".format(device_bdf, self.__target_driver))
                    continue
                else:
                    fd = os.open("{}/unbind".format(driver_path), os.O_WRONLY)
                    os.write(fd, device_bdf)
                    logger.info("Unbound {} from {}".format(device_bdf, current_driver))

                    vendor_id = self.__read_config(device_bdf, 0, 2)
                    device_id = self.__read_config(device_bdf, 2, 2)

                    logger.info("write {:04x} {:04x} to {}/{}/new_id".format(vendor_id,
                                                                       device_id,
                                                                       driver_prefix, self.__target_driver))
                    new_id_fd = os.open("{}/{}/new_id".format(driver_prefix, self.__target_driver),
                                            os.O_WRONLY)
                    os.write(new_id_fd, "{:04x} {:04x}".format(vendor_id, device_id))

            fd2 = os.open("/sys/bus/pci/drivers_probe", os.O_WRONLY)
            os.write(fd2, device_bdf)

if __name__ == '__main__':
    info = {'driver': 'vfio-pci', 'host': '0000:5e:00.0'}
    passthrough = CPCIEPassthrough(info)
    passthrough.init()
