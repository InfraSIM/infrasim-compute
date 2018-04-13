import os
import re
import apt_pkg
import apt.cache
import apt.progress.text
import apt.progress.base
import aptsources.sourceslist

from infrasim import config
from infrasim.yaml_loader import YAMLLoader


class PackageManager(object):
    _debug = False

    def __init__(self, source_list_entry):
        apt_pkg.init_config()
        # _MUST_ called prior to apt_pkg initialization
        # single entry in sources.list file
        # such as 'deb https://<repo url> trusty main'
        self.__add_entry(source_list_entry)

        # apt_pkg.init()
        apt_pkg.init_system()
        op_progress = None
        acquire_progress = None
        if PackageManager._debug:
            op_progress = apt.progress.text.OpProgress()
            acquire_progress = apt.progress.text.AcquireProgress()
        self.__apt_pkg_cache = apt_pkg.Cache(op_progress)
        self.__apt_pkg_cache.update(acquire_progress, apt_pkg.SourceList())
        self.__depcache = apt_pkg.DepCache(self.__apt_pkg_cache)
        self.__init_apt_cache()

    def __add_entry(self, entry):
        """
        add single entry in /etc/apt/sources.list
        """
        if entry is None:
            return False

        source_entry = aptsources.sourceslist.SourceEntry(entry)
        source_list = source_entry.mysplit(entry)
        if (source_list[0] not in ["deb", "deb-src"]) or (len(source_list) < 4):
            print "Invalid entry ({}).".format(entry)
            return

        typ = source_list[0]
        uri = None
        distribution = None
        attribute = None
        components = []
        for source in source_list:
            if source in ["deb", "deb-src"]:
                continue
            elif re.search(r'^https?:\/\/\w+', source):
                uri = source
            elif re.search(r'^\[.*\]', source):
                attribute = source
            elif source in ["trusty", "xenial"]:
                distribution = source
            else:
                components.append(source)

        if uri is None or distribution is None:
            return

        if attribute:
            uri = " ".join([attribute, uri])
        sources_list = aptsources.sourceslist.SourcesList()
        sources_list.backup(".orig")
        print "adding source list entry: {} {} {} {}".format(typ, uri, distribution, " ".join(components))
        sources_list.add(typ, uri, distribution, components)
        sources_list.save()

    def __init_apt_cache(self):
        pm = apt_pkg.PackageManager(self.__depcache)
        op_progress = None
        acquire_progress = None
        if PackageManager._debug:
            op_progress = apt.progress.text.OpProgress()
            acquire_progress = apt.progress.text.AcquireProgress()

        cache = apt.cache.Cache(op_progress)
        cache.update(acquire_progress)  # apt-get update
        fetcher = apt_pkg.Acquire(apt.progress.base.AcquireProgress())
        cache.fetch_archives(fetcher=fetcher)
        cache.install_archives(pm, apt.progress.base.InstallProgress())
        # cache.fetch_archives(progress=apt.progress.text.AcquireProgress())

    def is_installed(self, package_name):
        """
        check if package_name is installed
        """
        for pkg in self.__apt_pkg_cache.packages:
            if package_name == pkg.name:
                return (pkg.inst_state == apt_pkg.INSTSTATE_OK and
                        pkg.current_state == apt_pkg.CURSTATE_INSTALLED)
        return False

    def __get_version(self, package_name, version_str):
        target_version = None
        for v in self.__apt_pkg_cache[package_name].version_list:
            if v.ver_str == version_str:
                target_version = v
                break
        return target_version

    def do_install(self, package_name, version_str=None, force=True):
        """
        install one specific apt package
        """
        acquire_progress = apt.progress.base.AcquireProgress()
        install_progress = apt.progress.base.InstallProgress()

        op_progress = None
        if PackageManager._debug:
            op_progress = apt.progress.text.OpProgress()
        self.__depcache.init(op_progress)
        if package_name not in self.__apt_pkg_cache:
            print "{} not in cache, please check source.".format(package_name)
            return False

        if version_str:
            # print self.__apt_pkg_cache[package_name].version_list
            target_version = None
            target_version = self.__get_version(package_name, version_str)
            if target_version:
                self.__depcache.set_candidate_ver(self.__apt_pkg_cache[package_name],
                                                  target_version)

        self.__depcache.mark_install(self.__apt_pkg_cache[package_name])
        if force and self.is_installed(package_name):
            self.__depcache.set_reinstall(self.__apt_pkg_cache[package_name], True)

        try:
            self.__depcache.commit(acquire_progress, install_progress)
        except Exception:
            print "{} is not installed".format(package_name)

        return self.__apt_pkg_cache[package_name].inst_state == apt_pkg.INSTSTATE_OK

    def do_uninstall(self, package_name):
        if self.is_installed(package_name):
            self.__depcache.mark_delete(self.__apt_pkg_cache[package_name])
            self.__depcache.commit(apt.progress.base.AcquireProgress(),
                                   apt.progress.base.InstallProgress())

    def list_all_packages(self):
        for pkg in self.__apt_pkg_cache.packages:
            print pkg.name, pkg.current_state, pkg.inst_state, pkg.current_ver


def read_packages_info():
    version_yml = os.path.join(config.get_infrasim_root(), "packages.yml")
    package_list = None
    with open(version_yml, "r") as fp:
        package_list = YAMLLoader(fp).get_data()
    return package_list


def install_all_packages(force=True, entry=None):
    pm = PackageManager(entry)
    # install offical packages
    # don't have to install the depencies for each installation
    for pkg_name in ("socat", "ipmitool", "libssh-dev", "libffi-dev", "libyaml-dev"):
        pm.do_install(pkg_name, version_str=None, force=False)

    # install infrasim packages
    package_info_list = read_packages_info()
    if package_info_list is None:
        print "No packages.yml found."
        return

    for pkg_info in package_info_list:
        res = pm.do_install(pkg_info.get('name'), version_str=pkg_info.get('version'), force=force)
        print "Installing {}... {}".format(pkg_info.get('name'), "Done" if res else "Fail")

if __name__ == '__main__':
    install_all_packages()
