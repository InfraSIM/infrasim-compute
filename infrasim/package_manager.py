import os
import re
try:
    import apt_pkg
except ImportError:
    from infrasim import run_command
    run_command("apt-get update")
    run_command("apt-get install --no-install-recommends python-apt -y -q")
    import apt_pkg
import apt.cache
import apt.progress.text
import apt.progress.base
import aptsources.sourceslist

from infrasim import config
from infrasim.yaml_loader import YAMLLoader


class PackageManager(object):

    def __init__(self, update_cache=True, source_list_entry=None, progress=False):
        apt_pkg.init_config()
        # _MUST_ called prior to apt_pkg initialization
        # single entry in sources.list file
        # such as 'deb https://<repo url> trusty main'
        self.__add_entry(source_list_entry)

        self.__progress = progress

        self.__init_apt_pkg_cache()

        if update_cache:
            self.__init_apt_cache()

        # second time to take effect for switching sources
        self.__init_apt_pkg_cache()

        if update_cache:
            self.__init_apt_cache()

    def __init_apt_pkg_cache(self):
        apt_pkg.init()
        op_progress = None
        if self.__progress:
            op_progress = apt.progress.text.OpProgress()
        self.__apt_pkg_cache = apt_pkg.Cache(op_progress)
        self.__apt_pkg_cache.update(apt.progress.base.AcquireProgress(),
                                    apt_pkg.SourceList())
        self.__depcache = apt_pkg.DepCache(self.__apt_pkg_cache)

    def __check_if_entry_exists(self, entry):
        '''
        Event python-apt will check the entry exists, but it can't
        handle the entry with attribute like '[trusted=true]'
        '''
        fp = open("/etc/apt/sources.list", "r")
        lines = fp.readlines()
        fp.close()
        for line in lines:
            if set(line.strip().split()) == set(entry.strip().split()):
                return True
        return False

    def __add_entry(self, entry):
        """
        add single entry in /etc/apt/sources.list
        """
        if entry is None:
            return

        if self.__check_if_entry_exists(entry):
            print "{} exists".format(entry)
            return

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
        op_progress = None
        acquire_progress = None
        if self.__progress:
            op_progress = apt.progress.text.OpProgress()
            acquire_progress = apt.progress.text.AcquireProgress()

        cache = apt.cache.Cache(op_progress)
        cache.update(acquire_progress)  # apt-get update
        cache.open()
        cache.commit()
        cache.close()

    def is_installed(self, package_name):
        """
        check if package_name is installed
        """
        for pkg in self.__apt_pkg_cache.packages:
            if package_name == pkg.name:
                return pkg.current_state == apt_pkg.CURSTATE_INSTALLED
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
        target_pkg = None

        for pkg in self.__apt_pkg_cache.packages:
            if pkg.name == package_name:
                target_pkg = pkg
                break

        op_progress = None
        if self.__progress:
            op_progress = apt.progress.text.OpProgress()
        self.__depcache.init(op_progress)
        if (package_name not in self.__apt_pkg_cache) or (target_pkg is None):
            print "{} not in cache, please check source.".format(package_name)
            return False

        if version_str and version_str != "latest":
            # print self.__apt_pkg_cache[package_name].version_list
            target_version = None
            target_version = self.__get_version(package_name, version_str)
            if target_version:
                self.__depcache.set_candidate_ver(target_pkg,
                                                  target_version)

        self.__depcache.mark_install(target_pkg)
        if force and self.is_installed(package_name):
            self.__depcache.set_reinstall(target_pkg, True)

        try:
            self.__depcache.commit(acquire_progress, install_progress)
        except Exception as e:
            print "{} is not installed (Reason: {})".format(package_name, e)

        return target_pkg.inst_state == apt_pkg.INSTSTATE_OK

    def do_uninstall(self, package_name):
        self.__init_apt_pkg_cache()
        if self.is_installed(package_name):
            for pkg in self.__apt_pkg_cache.packages:
                if pkg.name == package_name:
                    self.__depcache.mark_delete(pkg, True)
                    self.__depcache.commit(apt.progress.base.AcquireProgress(),
                                           apt.progress.base.InstallProgress())

    def list_all_packages(self):
        for pkg in self.__apt_pkg_cache.packages:
            print pkg.name, pkg.current_state, pkg.inst_state, pkg.current_ver


def read_packages_info():
    version_yml = os.path.join(config.get_infrasim_root(), "components-version/packages.yml")
    package_list = None
    with open(version_yml, "r") as fp:
        package_list = YAMLLoader(fp).get_data()
    return package_list


def install_all_packages(force=True, entry=None):
    pm = PackageManager(source_list_entry=entry, progress=True)
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
