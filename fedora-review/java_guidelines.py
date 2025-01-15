#    -*- coding: utf-8 -*-

"""Java language plugin for fedora-review

This plugin aims to implement Fedora Packaging Guidelines for Java[1]
as a fedora-review plugin.

[1] https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/
"""

import re
from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    """ Dotted named extends the base group, here 'Java'. """
    group = 'Java.guidelines'
    external_plugin = True

    def is_applicable(self):
        """ Use the is_applicable() defined in main group: """
        return self.checks.groups['Java'].is_applicable()


class JavaCheckBase(CheckBase):
    """Base check for Java checks"""

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)

    def _is_maven_pkg(self):
        """Returns True if this is likely Maven package"""
        for build_r in self.spec.build_requires:
            if 'maven-local' in build_r:
                return True
        return False

    def _is_xmvn_pkg(self):
        """Returns True if this package is being built with XMvn (new style
        Maven packaging)"""
        return self.spec.find_re('([^#]*%mvn_build)|([^#]*%mvn_install)')

    def _get_javadoc_sub(self):
        """Returns name of javadoc rpm or None if no such subpackage
        exists."""
        for pkg in self.spec.packages:
            if pkg.endswith('-javadoc'):
                return pkg
        return None

    def _search_previous_line(self, section, trigger, pivot, judge):
        """This function returns True if we find 'judge' regex
        immediately before pivot (empty lines ignored) in section. This only
        applies if we find trigger regex after pivot as well. If no
        trigger is found we return None. Example use on spec like
        this:

        mvn-rpmbuild -Dmaven.test.skip
        with: -Dmaven.test.skip being trigger
              mvn-rpmbuild being pivot
              any comment would be judge
        """
        empty_regex = re.compile(r'^\s*$')
        found_trigger = False
        found_pivot = False
        for line in reversed(section):
            if trigger.search(line):
                found_trigger = True

            if found_trigger and pivot.search(line):
                found_pivot = True
                continue

            # we already found mvn command. Any non-empty line now has
            # to be a comment or we fail this test
            if found_pivot and not empty_regex.search(line):
                if judge.search(line):
                    return True
                else:
                    self.set_passed(self.FAIL)
                    return False

        return None


class CheckNotJavaApplicable(JavaCheckBase):
    """Class that disables generic tests that make no sense for java
    packages"""

    deprecates = ['CheckBuildCompilerFlags', 'CheckUsefulDebuginfo',
                  'CheckLargeDocs']

    def is_applicable(self):
        return False


class CheckJavadoc(JavaCheckBase):
    """Check if javadoc subpackage exists and contains documentation"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_javadoc_installation'
        self.text = "Javadoc documentation files are generated and " \
                    "included in -javadoc subpackage"
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        pkg = self._get_javadoc_sub()
        if not pkg:
            self.set_passed(self.FAIL,
                            "No javadoc subpackage present. "
                            "Note: Javadocs are optional for Fedora "
                            "versions >= 21")
            return

        # and now look for at least one html file
        if self.rpms.find('*.html', pkg):
            self.set_passed(self.PASS)
            return
        self.set_passed(self.FAIL, "No javadoc html files found in %s" % pkg)


class CheckJavadocdirName(JavaCheckBase):
    """Check if deprecated javadoc symlinks are present"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_javadoc_installation'
        self.text = "Javadocs are placed in %{_javadocdir}/%{name} " \
                    "(no -%{version} symlink)"
        self.automatic = True

    def run_on_applicable(self):
        pkg = self._get_javadoc_sub()
        if not pkg:
            self.set_passed(self.FAIL, "No javadoc subpackage present")
            return
        name_ver_pattern = "/usr/share/javadoc/%s-%s/*" \
            % (self.spec.name, self.spec.version)
        if self.rpms.find_all(name_ver_pattern, pkg):
            self.set_passed(self.FAIL,
                            "Found deprecated versioned javadoc paths " +
                            name_ver_pattern)
            return
        name_pattern = "/usr/share/javadoc/%s/*" % self.spec.name
        if not self.rpms.find_all(name_pattern, pkg):
            self.set_passed(self.FAIL,
                            "No /usr/share/javadoc/%s found" % self.spec.name)
            return
        self.set_passed(self.PASS)


JAVAPACKAGES_BR = ('javapackages-tools', 'jpackage-utils',
                   'javapackages-local', 'gradle-local')
JAVAPACKAGES_R = ('javapackages-tools', 'jpackage-utils')


class CheckJPackageRequires(JavaCheckBase):
    """Check if (Build)Requires on javapackages-tools are correct"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.text = "Packages have proper BuildRequires/Requires on " \
                    "javapackages-tools (jpackage-utils)"
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        brs = self.spec.build_requires
        requires = self.spec.get_requires()
        br_found = any(x in br for x in JAVAPACKAGES_BR for br in brs)

        # this not not 100% correct since we just look for this
        # require anywhere in spec.
        r_found = any(x in br for x in JAVAPACKAGES_R for br in requires)

        if self._is_maven_pkg() or self._is_xmvn_pkg():
            extra = "Maven packages do not need to (Build)Require " \
                    "jpackage-utils. It is pulled in by maven-local"
            self.set_passed(not (br_found or r_found), extra)
        else:
            self.set_passed(br_found and r_found)


class CheckJavadocJPackageRequires(JavaCheckBase):
    """Check if javadoc subpackage has requires on javapackages-tools"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.text = "Javadoc subpackages should not have Requires: " \
                    "javapackages-tools (jpackage-utils)"
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        pkgs = [pkg for pkg in self.spec.packages
                if pkg.endswith('-javadoc')]
        if len(pkgs) == 0:
            self.set_passed(self.NA)
        elif len(pkgs) > 1:
            self.set_passed(self.PENDING,
                            'More than one javadoc package')
        else:
            extra = "javapackages-tools requires are automatically " \
                    "generated by the buildsystem"
            reqs = self.spec.get_requires(pkgs[0])
            ok = not any(x in reqs for x in JAVAPACKAGES_R)
            self.set_passed(self.PASS if ok else self.FAIL,
                            extra if not ok else None)


class CheckNoOldMavenDepmap(JavaCheckBase):
    """Check if old add_to_maven_depmap macro is being used"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_maven_pom_xml_files'
        self.text = 'Old add_to_maven_depmap macro is not being used'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%add_to_maven_depmap\s+.*')

    def run_on_applicable(self):
        """ run check for java packages """
        self.set_passed(not self.spec.find_re(self.regex))


class CheckAddMavenDepmap(JavaCheckBase):
    """Check if POM files have correct Maven mapping"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_maven_pom_xml_files'
        self.text = 'POM files have correct Maven mapping'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        if self._is_xmvn_pkg():
            self.set_passed(self.PASS)
        elif not self.spec.find_re('[^#]*%add_maven_depmap'):
            self.set_passed(self.FAIL, """Old style Maven package found, no
                            add_maven_depmap calls found but POM files
                            present""")
        else:
            self.set_passed(self.PENDING, """Some add_maven_depmap
                            calls found. Please check if they are correct or
                            update to latest guidelines""")


class CheckUseMavenpomdirMacro(JavaCheckBase):
    """Use proper _mavenpomdir macro instead of old path"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_maven_pom_xml_files'
        self.text = 'Packages use .mfiles file list instead of ' \
                    '%{_datadir}/maven2/poms'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile('%{_datadir}/maven2/poms')

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        self.set_passed(not self.spec.find_re(self.regex))


class CheckUpdateDepmap(JavaCheckBase):
    """Check if there is deprecated %update_maven_depmap macro being used"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_maven_pom_xml_files'
        self.text = 'Package DOES NOT use %update_maven_depmap in ' \
                    '%post/%postun'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%update_maven_depmap\s+.*')

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        self.set_passed(not self.spec.find_re(self.regex))


class CheckNoRequiresPost(JavaCheckBase):
    """Check if package still has requires(post/postun) on
    jpackage-utils"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.text = "Packages DO NOT have Requires(post) and " \
                    "Requires(postun) on jpackage-utils for " \
                    "%update_maven_depmap macro"
        self.automatic = True
        self.type = 'MUST'
        self.regex = \
            re.compile(r'^\s*Requires\((post|postun)\):\s*jpackage-utils.*')

    def run(self):

        def _find(what, where):
            ''' True if what is part of the list where. '''
            for item in where:
                if not item:
                    continue
                if what in item:
                    return True
            return False

        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        bad_ones = []
        txt = ''
        for pkg_name in self.spec.packages:
            rpm_pkg = self.rpms.get(pkg_name)
            if _find('jpackage-utils', [rpm_pkg.post, rpm_pkg.postun]):
                bad_ones.append(pkg_name)
        if bad_ones:
            txt = 'jpackage-utils post/postun in ' + ', '.join(bad_ones)
        self.set_passed(self.FAIL if txt else self.PASS, txt)


class CheckTestSkip(JavaCheckBase):
    """Check if -Dmaven.test.skip is being used and look for
    comment"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.text = 'If tests are skipped during package build explain' \
                    ' why it was needed in a comment'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        skip_regex = re.compile(r'\s+-Dmaven.test.skip.*')
        # This is ugly, we should test for %mvn_build macro but rpm gives us
        # expanded sections. Expanding %mvn_build in rpm or Mock is an option
        # but it either won't work with --prebuilt (Mock) or can easily fail
        # when package providing %mvn_build macro is not installed locally
        xmvn_skip_regex = re.compile(r'mvn-build\s+.*(-f|--force|'
                                     '--skip-tests).*')
        build_section = self.spec.get_section('%build', raw=True)
        if build_section and (skip_regex.search(build_section) or
                              xmvn_skip_regex.search(build_section)):
            self.set_passed(self.PENDING, """Tests seem to be skipped. Verify
        there is a commment giving a reason for this""")
        else:
            self.set_passed(self.NA)


class CheckMvnRpmbuild(JavaCheckBase):
    """Check if mvn-rpmbuild is not being used"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.text = "mvn-rpmbuild is deprecated and will be removed in " \
                    "future releases"
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        mvn_rpmbuild = re.compile(r'[^#]*mvn-rpmbuild')
        if self.spec.find_re(mvn_rpmbuild):
            self.set_passed(self.FAIL, "Convert the package to use %mvn_build "
                                       "instead of deprecated mvn-rpmbuild")
        else:
            self.set_passed(self.NA)


class CheckBundledJars(JavaCheckBase):
    """Check for bundled JAR/class files in source tarball"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_pre_built_dependencies'
        self.text = """If source tarball includes bundled JAR/class
        files these need to be removed prior to building"""
        self.automatic = False
        self.type = 'MUST'


class JarFilename(JavaCheckBase):
    """Check correct naming of jar files in _javadir"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = "JAR files are named and installed according to guidelines"
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_jar_file_installation'
        self.automatic = False
        self.type = 'MUST'


class CheckPomInstalled(JavaCheckBase):
    """Check if pom.xml files from source tarballs are installed"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = "If package contains pom.xml files install it " \
                    "(including metadata) even when building with ant"
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/' \
                   '#_maven_pom_xml_files'
        self.automatic = False
        self.type = 'MUST'


class CheckUpstremBuildMethod(JavaCheckBase):
    """Verify package uses upstream preferred build method"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Package uses upstream build method (ant/maven/etc.)"""
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.automatic = False
        self.type = 'SHOULD'


class CheckNoArch(JavaCheckBase):
    """Package should be noarch in most cases"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Packages are noarch unless they use JNI"""
        self.url = 'https://docs.fedoraproject.org/en-US/packaging-guidelines/Java/'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        for pkg in self.spec.packages:
            arch = self.spec.expand_tag('arch', pkg)
            if arch:
                arch = arch.lower()
            if arch != 'noarch':
                self.set_passed(self.PENDING, "%s subpackage is not "
                                "noarch. Please verify manually" % pkg)
                break
        else:
            self.set_passed(self.PASS)


class CheckNewStyleMaven(JavaCheckBase):
    """Maven packages should use new style packaging style"""

    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Maven packages should use new style packaging"""
        self.url = 'https://docs.fedoraproject.org/en-US/java-packaging-howto/maven/'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if self._is_maven_pkg() and self._is_xmvn_pkg():
            self.set_passed(self.PASS)
        elif self._is_maven_pkg():
            self.set_passed(self.FAIL, "If possible update your package to "
                            "latest guidelines")
        else:
            self.set_passed(self.NA)


# vim: set expandtab ts=4 sw=4:
