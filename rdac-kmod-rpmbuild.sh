#!/bin/bash

CURUSER=$(/usr/bin/whoami);
RHELVER=$(/usr/bin/lsb_release -sr);
RHELVER=${RHELVER%.*};

if [ "${CURUSER}" == "root" ]; then
    /bin/echo "ERROR: RPM's must not be built as the root user for security purposes. Please run the build as a regular user.";
    exit 1;
fi

if [ ${RHELVER} -eq 5 ]; then
    /bin/rpm -q buildsys-macros > /dev/null;
    
    if [ $? -ne 0 ]; then
	/bin/echo "ERROR: RPM dependency buildsys-macros is not installed. Please install before continuing...";
	exit 1;
    fi
fi

/bin/rpm -q rpm-build > /dev/null;

if [ $? -ne 0 ]; then
    /bin/echo "ERROR: RPM dependency rpm-build is not installed. Please install before continuing...";
    exit 1;
fi

#kabi whitelists performs kenrel abi compatibility checks when building the rpm but its only available in RHEL6
#Note: Bug in RHEL 6.3 causes kabi whitelists to not be located even if installed, see RH Bugzilla 842038
if [ ${RHELVER} -eq 6 ]; then
    /bin/rpm -q kabi-whitelists > /dev/null;
    oldkabi=$?;

    /bin/rpm -q kernel-abi-whitelists > /dev/null;
    newkabi=$?;

    if [ ${oldkabi} -ne 0 ] && [ ${newkabi} -ne 0 ]; then
	/bin/echo "ERROR: RPM dependency kernel-abi-whitelists (formerly kabi-whitelists) is not installed. Please install before continuing...";
	exit 1;
    fi
fi


if [ -f ~/.rpmmacros ]; then
    /bin/rm -f ~/.rpmmacros;
fi

#Only required for RHEL5, this setting is standard in RHEL6
#If missing it will default to /usr/src/redhat which is deprecated and no longer recommended
if [ ${RHELVER} -eq 5 ]; then
    /bin/echo "%_topdir ${HOME}/rpmbuild" > ~/.rpmmacros;
fi

/usr/bin/wget -q "http://mysupport.netapp.com/NOW/public/apbu/oemcp/09.03.0C05.0504/rdac-LINUX-09.03.0C05.0504-source.tar.gz";

if [ $? -ne 0 ]; then
    /bin/echo "ERROR: Failed to download NetApp RDAC drivers..." 1>&2;
    exit 1;
fi

/bin/mkdir -p ~/rpmbuild/{BUILD,RPMS,S{OURCES,PECS,RPMS}};
/bin/cp -f *.spec ~/rpmbuild/SPECS/;
/bin/cp -f *.patch ~/rpmbuild/SOURCES/;
/bin/cp -a *.gz ~/rpmbuild/SOURCES/;

/usr/bin/rpmbuild -ba ~/rpmbuild/SPECS/rdac-kmod.spec;
