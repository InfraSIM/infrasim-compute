'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import fnmatch
import re
from infrasim import run_command
from infrasim import config
from infrasim.yaml_loader import YAMLLoader
from infrasim import logger
HAS_PYTHON_APT = True
try:
    import apt
    import apt_pkg
    import aptsources.sourceslist
except ImportError:
    HAS_PYTHON_APT = False


class PackageManager(object):
    def __init__(self, update_cache=True, purge=True,
                 install_recommends=True, force=True,
                 autoremove=True, autoclean=False,
                 only_upgrade=True, allow_unauthenticated=True,
                 source_list_entry=None):
        self.__update_cache = update_cache
        self.__purge = purge
        self.__install_recommends = install_recommends
        self.__force = force
        self.__autoremove = autoremove
        self.__autoclean = autoclean
        self.__only_upgrade = only_upgrade
        self.__allow_unauthenticated = allow_unauthenticated

        if not HAS_PYTHON_APT:
            run_command("apt-get update")
            run_command("apt-get install --no-install-recommends python-apt -y -q")
            global apt, apt_pkg, aptsources
            import apt
            import apt_pkg
            import aptsources.sourceslist

        self.__add_entry(source_list_entry)

        self.__cache = self.__get_cache()
        self.init()

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
            # set to defaut entry
            entry = "deb https://dl.bintray.com/infrasim/deb xenial main"

        if self.__check_if_entry_exists(entry):
            print "{} exists".format(entry)
            return

        source_entry = aptsources.sourceslist.SourceEntry(entry)
        source_list = source_entry.mysplit(entry)
        if (source_list[0] not in ["deb", "deb-src"]) or (len(source_list) < 4):
            logger.error("Invalid entry ({}).".format(entry))
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
        logger.info("adding source list entry: {} {} {} {}".format(typ, uri, distribution, " ".join(components)))
        sources_list.add(typ, uri, distribution, components)
        sources_list.save()

    def init(self):
        if self.__update_cache:
            for retry in range(3):
                try:
                    self.__cache.update(apt.progress.text.AcquireProgress())
                    break
                except apt.cache.FetchFailedException as e:
                    logger.exception(e)
                    continue
            else:
                logger.error("Failed to update apt cache")

            self.__cache.open(progress=None)

    def __get_package_versions(self, pkgname, pkg, pkg_cache):
        try:
            versions = set(v.version for v in pkg.versions)
        except AttributeError as e:
            logger.exception(e)
            raise e

        return versions

    def __package_version_compare(self, version, other_version):
        try:
            return apt_pkg.version_compare(version, other_version)
        except AttributeError as e:
            logger.exception(e)
            raise e

    def __check_package_status(self, pkgname, version, state):
        try:
            package = self.__cache[pkgname]
            ll_package = self.__cache._cache[pkgname]
        except KeyError:
            if state == 'install':
                try:
                    provided_packages = self.__cache.get_providing_packages(pkgname)
                    if provided_packages:
                        is_installed = False
                        upgradable = False
                        version_ok = False

                        if self.__cache.is_virtual_package(pkgname) and len(provided_packages) == 1:
                            package = provided_packages[0]
                            installed, version_ok, upgradable, has_files = self.__check_package_status(package.name,
                                                                                                       version,
                                                                                                       state='install')
                            if installed:
                                is_installed = True
                        return is_installed, version_ok, upgradable, False
                except AttributeError:
                    return False, False, True, False
            else:
                return False, False, False, False

        try:
            has_files = len(package.installed_files) > 0
        except UnicodeDecodeError:
            has_files = True
        except AttributeError:
            has_files = False

        try:
            package_is_installed = ll_package.current_state == apt_pkg.CURSTATE_INSTALLED
        except AttributeError:
            try:
                package_is_installed = package.is_installed
            except AttributeError as e:
                logger.exception(e)
                raise e

        version_is_installed = package_is_installed
        if version:
            versions = self.__get_package_versions(pkgname, package, self.__cache._cache)
            available_upgrades = fnmatch.filter(versions, version)

            if package_is_installed:
                try:
                    installed_version = package.installed.version
                except AttributeError as e:
                    logger.exception(e)
                    raise e

                logger.info("installed version: {}".format(installed_version))
                version_is_installed = fnmatch.fnmatch(installed_version, version)

                package_is_upgradable = False
                for candidate in available_upgrades:
                    if self.__package_version_compare(candidate, installed_version) > 0:
                        package_is_upgradable = True
                        break
            else:
                package_is_upgradable = bool(available_upgrades)
        else:
            try:
                package_is_upgradable = package.is_upgradable
            except AttributeError as e:
                logger.exception(e)
                raise e

        return package_is_installed, version_is_installed, package_is_upgradable, has_files

    def __mark_installed_manually(self, pkg_name):
        cmd = "{} manual {}".format("apt-mark", pkg_name)
        try:
            _, out = run_command(cmd)
        except Exception as e:
            logger.exception(e)
            raise e

        if "Invalid operation" in out:
            cmd = "{} unmarkauto {}".format("apt-mark", pkg_name)
            try:
                run_command(cmd)
            except Exception as e:
                logger.exception(e)
                raise e

    def __get_cache(self):
        cache = None
        try:
            cache = apt.Cache()
        except SystemError:
            try:
                run_command("apt-get update -q")
            except Exception as e:
                logger.exception(e)
                raise e
            cache = apt.Cache()
        return cache

    def do_install(self, pkg_name, version='latest', default_release=None):
        combined_package_version = ""
        installed, installed_version, upgradable, has_files = self.__check_package_status(pkg_name,
                                                                                          version, state='install')

        logger.info(
            "install(): installed {}, installed_version {}, upgradable {}, has_files {}".format(installed,
                                                                                                installed_version,
                                                                                                upgradable,
                                                                                                has_files))
        if (not installed and not self.__only_upgrade) or (installed and not installed_version) or \
                (self.__only_upgrade and upgradable):
            if version != "latest":
                combined_package_version = "'{}={}'".format(pkg_name, version)
            else:
                combined_package_version = "'{}'".format(pkg_name)

        if installed_version and upgradable and version:
            if version != "latest":
                combined_package_version = "'{}={}'".format(pkg_name, version)
            else:
                combined_package_version = "'{}'".format(pkg_name)

        logger.info("combined_package_version: {}".format(combined_package_version))

        if combined_package_version:
            if self.__force:
                force_yes = "--force-yes"
            else:
                force_yes = ''

            if self.__autoremove:
                autoremove = '--auto-remove'
            else:
                autoremove = ''

            if self.__only_upgrade:
                only_upgrade = '--only-upgrade'
            else:
                only_upgrade = ''

            cmd = "{} -y {} {} {} install {}".format("apt-get", only_upgrade, force_yes,
                                                     autoremove, combined_package_version)

            if default_release:
                cmd += " -t '{}'".format(default_release)

            if self.__install_recommends is False:
                cmd += ' -o APT::Install-Recommends=no'
            else:
                cmd += ' -o APT::Install-Recommends=yes'

            if self.__allow_unauthenticated:
                cmd += " --allow-unauthenticated"

            logger.info(cmd)
            try:
                rc, out = run_command(cmd)
                print out
                logger.info(out)
                self.__mark_installed_manually(pkg_name)
            except Exception as e:
                logger.exception(e)
                raise e

    def do_remove(self, pkgname, version="latest"):
        package = None
        installed, installed_version, upgradable, has_files = self.__check_package_status(pkgname,
                                                                                          version, state='remove')
        logger.info(
            "remove(): installed {}, installed_version {}, upgradable {}, has_files {}".format(installed,
                                                                                               installed_version,
                                                                                               upgradable,
                                                                                               has_files))
        if (installed and version == "latest") or installed_version or (has_files and self.__purge):
            package = pkgname

        if not package:
            return

        else:
            if self.__force:
                force_yes = "--force-yes"
            else:
                force_yes = ""

            if self.__purge:
                purge = "--purge"
            else:
                purge = ""

            if self.__autoremove:
                autoremove = "--auto-remove"
            else:
                autoremove = ""

            cmd = "{} -q -y {} {} {} remove {}".format("apt-get", purge, force_yes, autoremove, package)

            logger.info(cmd)
            try:
                rc, out = run_command(cmd)
                print out
                logger.info(out)
            except Exception as e:
                logger.exception(e)
                raise e

    def do_cleanup(self, action=None):
        if action not in frozenset(['autoremove', 'autoclean']):
            raise AssertionError('Expected "autoremove" or "autoclean" clean action.')

        if self.__force:
            force_yes = "--force-yes"
        else:
            force_yes = ""

        cmd = "{} -y {} {}".format("apt-get", force_yes, action)
        try:
            _, out = run_command(cmd)
            print out
            logger.info(out)
        except Exception as e:
            logger.exception(e)
            raise e


def read_packages_info():
    version_yml = os.path.join(config.get_infrasim_root(), "components-version/packages.yml")
    package_list = None
    with open(version_yml, "r") as fp:
        package_list = YAMLLoader(fp).get_data()
    return package_list


def install_all_packages(force=True, entry=None):
    pm = PackageManager(only_upgrade=False, force=force, source_list_entry=entry)
    # install offical packages
    # don't have to install the depencies for each installation
    for pkg_name in ("socat", "ipmitool", "libssl-dev", "libffi-dev", "libyaml-dev", "libaio-dev"):
        pm.do_install(pkg_name)

    # install infrasim packages
    package_info_list = read_packages_info()
    if package_info_list is None:
        print "No packages.yml found."
        return

    for pkg_info in package_info_list:
        pm.do_install(pkg_info.get('name'), version=pkg_info.get('version'))


if __name__ == '__main__':
    install_all_packages()
