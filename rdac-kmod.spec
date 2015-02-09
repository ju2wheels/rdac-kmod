%define kmod_name rdac

Name:       %{kmod_name}-kmod
Version:    09.03.0C05.0504
Release:    34%{?dist}
Summary:    LSI rdac engenio kernel modules
License:    Other
Group:      System Environment/Kernel
URL:        http://www.kerneldrivers.org/
Source0:        rdac-LINUX-%{version}-source.tar.gz
Patch1:		fixredhat.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:	%kernel_module_package_buildreqs
BuildArch: i686 x86_64
%kernel_module_package -n %{kmod_name}

%description 
LSI rdac engenio kernel modules

%package -n rdac
Summary: RDAC
Group: System Environment/Base
%if %{?el5:1}%{!?el5:0}
#mkinitrd provides grubby on RHEL5, but grubby rpm provides it on RHEL6
Requires: rdac-kmod mkinitrd
%else
Requires: rdac-kmod grubby
%endif

%description -n rdac
RDAC programs and man pages

%prep
%setup -q -c -n %{kmod_name}-kmod-%{version}
mv linuxrdac-%{version} source
%patch1 -p0 -b .fixredhat
perl -pi -e 's|install -o root -g root|install|' source/Makefile
 
%build
export EXTRA_CFLAGS='-DVERSION=\"%version\"'
for flavor in %flavors_to_build ; do
	echo Building for $flavor and target cpu %{_target_cpu} and kverrel = %kverrel
	cp -r source $flavor
	make -C %{kernel_source $flavor} M=$PWD/$flavor modules
	make -C $flavor genuniqueid mppUtil
done

%install
export INSTALL_MOD_PATH=%{buildroot}
export INSTALL_MOD_DIR=extra/%{kmod_name}
install -d -m755 %{buildroot}/etc/init.d
install -d -m755 %{buildroot}/opt/mpp
install -d -m755 %{buildroot}/var/mpp
install -d -m755 %{buildroot}/%{_sbindir}
install -d -m755 %{buildroot}/%{_datadir}/man

#RHEL6 only files
%if %{?el6:1}%{!?el6:0}
install -d -m755 %{buildroot}/usr/share/dracut/modules.d/90mpp/
%endif

for flavor in %flavors_to_build ; do
	make -C %{kernel_source $flavor} modules_install M=$PWD/$flavor SUBDIRS=$PWD/$flavor
	make -C $flavor DEST_DIR=%{buildroot} copyfiles
	make -C $flavor DEST_DIR=%{buildroot} copyrpmfiles
done
# remove spurious modules files
find %{buildroot}/lib/modules/ -type f -not -name \*.ko | xargs rm -f

/bin/touch %{buildroot}/var/mpp/devicemapping

install -m500 %{_builddir}/%{name}-%{version}/source/Makefile %{buildroot}/opt/mpp/makefile.saved
install -m500 %{_builddir}/%{name}-%{version}/source/hbaCheck %{buildroot}/opt/mpp/hbaCheck
install -m500 %{_builddir}/%{name}-%{version}/source/setupDriver.REDHAT %{buildroot}/opt/mpp/setupDriver.REDHAT
install -m755 %{_builddir}/%{name}-%{version}/source/mpp_rcscript.REDHAT %{buildroot}/etc/init.d/mpp

#RHEL6 only files
%if %{?el6:1}%{!?el6:0}
install -m0644 %{_builddir}/%{name}-%{version}/source/dracutsetup/mpp_pre_udev.sh %{buildroot}/usr/share/dracut/modules.d/90mpp/mpp-pre-udev.sh
install -m0755 %{_builddir}/%{name}-%{version}/source/dracutsetup/install %{buildroot}/usr/share/dracut/modules.d/90mpp/install
install -m0755 %{_builddir}/%{name}-%{version}/source/dracutsetup/installkernel %{buildroot}/usr/share/dracut/modules.d/90mpp/installkernel
%endif

%clean
[ X%{buildroot} != X ] && [ X%{buildroot} != X/ ] && rm -rf %{buildroot}

%post -n rdac
if [ ! -e /usr/sbin/hot_add ]; then
   /bin/ln -s /usr/sbin/mppBusRescan /usr/sbin/hot_add > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to create symlink for hot_add...";
      exit 1;
   fi
fi

if [ ! -e /usr/share/man/man1/hot_add.1.gz ]; then
   /bin/ln -s /usr/share/man/man1/mppBusRescan.1.gz /usr/share/man/man1/hot_add.1.gz;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to create symlink for hot_add mange page...";
      exit 1;
   fi
fi

/sbin/chkconfig --add mpp > /dev/null 2>&1;
/sbin/service mpp restart > /dev/null 2>&1;

%preun -n rdac
if [ $1 -eq 0 ]; then
   /sbin/service mpp stop > /dev/null 2>&1;
   /sbin/chkconfig mpp off > /dev/null 2>&1;
   /sbin/chkconfig --del mpp > /dev/null 2>&1;
fi

%postun -n rdac
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

if [ $1 -eq 0 ]; then
   for mppInitRdVer in $(/bin/grep "with MPP support" /boot/grub/grub.conf 2>/dev/null | /bin/sed 's|.*(||' | /bin/sed 's|).*||'); do
       /sbin/grubby --grub --remove-kernel="TITLE=Red Hat Enterprise Linux Server (${mppInitRdVer}) with MPP support" > /dev/null 2>&1;

       if [ $? -ne 0 ]; then
       	  /bin/echo "ERROR: Failed to remove grub boot entry for MPP ${initType} image version ${mppInitRdVer}...";
	  exit 1;
       fi
   done

   for initRdKdumpImg in $(/bin/ls /boot/${initType}-*kdump.img.nompp 2>/dev/null); do
       if [ ! -z "${initRdKdumpImg}" ]; then
       	  /bin/mv -f ${initRdKdumpImg} $(/bin/sed 's|.nompp||' <<< "${initRdKdumpImg}") > /dev/null 2>&1;

       	  if [ $? -ne 0 ]; then
       	     /bin/echo "ERROR: Faild to restore ${initType} kdump image ${initRdKdumpImg}...";
	     exit 1;
          fi
       fi
   done 

   /bin/rm -f /boot/mpp-*.img > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to delete MPP ${initType} images...";
      exit 1;
   fi

   /bin/rm -f /usr/sbin/hot_add > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to remove symlink /usr/sbin/hot_add...";
      exit 1;
   fi

   /bin/rm -f /usr/share/man/man1/hot_add.1.gz > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to remove symlink /usr/share/man/man1/hot_add.1.gz...";
      exit 1;
   fi

   if [ -f /etc/modprobe.conf ]; then
      /bin/sed -i -e '/BEGIN MPP Driver Comments/,/END MPP Driver Comments/d' /etc/modprobe.conf;
      /bin/sed -i -e '/BEGIN OF MPP Driver Changes/,/END OF MPP Driver Changes/d' /etc/modprobe.conf;
      /bin/sed -i -e '/^$/d' /etc/modprobe.conf;
   fi

   if [ -f /etc/modprobe.conf.local ]; then
      /bin/sed -i -e '/BEGIN MPP Driver Comments/,/END MPP Driver Comments/d' /etc/modprobe.conf.local;
      /bin/sed -i -e '/BEGIN OF MPP Driver Changes/,/END OF MPP Driver Changes/d' /etc/modprobe.conf.local;
      /bin/sed -i -e '/^$/d' /etc/modprobe.conf;
   fi  

   if [ -f /etc/sysconfig/kernel ]; then
      /bin/sed -i -e '/BEGIN MPP Driver Comments/,/END MPP Driver Comments/d' /etc/sysconfig/kernel;
   fi 

   if [ -f /etc/init.d/iscsi ]; then
      /bin/sed -i -e '/BEGIN_MPP/,/END_MPP/d' /etc/init.d/iscsi;
   fi

   if [ -f /etc/init.d/open-iscsi ]; then
      /bin/sed -i -e '/BEGIN_MPP/,/END_MPP/d' /etc/init.d/open-iscsi;
   fi

   if [ -f /etc/rc.d/init.d/iscsi ]; then
      /bin/sed -i -e '/BEGIN_MPP/,/END_MPP/d' /etc/rc.d/init.d/iscsi;
   fi

   %if %{?el6:1}%{!?el6:0}
       if [ -f /etc/modprobe.d/mppmodules.conf ]; then
          /bin/rm -f /etc/modprobe.d/mppmodules.conf;
       fi
   %endif

   isPAE="";
   preferredKernel="kernel";

   /bin/rpm -q kernel-PAE > /dev/null 2>&1;

   if [ $? -eq 0 ]; then
       preferredKernel="kernel-PAE";
       isPAE="PAE";
   fi

   lastKernelImgVer=$(/bin/rpm -q ${preferredKernel} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${preferredKernel}-||" | /usr/bin/tail -n 1);

   if [ ! -z "${lastKernelImgVer}" ]; then
       /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer})" > /dev/null 2>&1;

       if [ $? -ne 0 ]; then
           /bin/echo "ERROR: Failed to set grub boot entry to kernel init image version ${lastKernelImgVer}...";
           exit 1;
       fi
   else
       /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
       exit 1;
   fi
fi

#Note that this run as if it was a post section as well, so consider it a post section as well as a trigger
#its always triggered if there were existing kernels installed when we first install rdac, which is always true because we need at least one kernel installed
%triggerin -n rdac -- kernel
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

lastKernelImgVer="";

/bin/rpm -q kmod-rdac > /dev/null 2>&1;
kmodInstalled=$?;
/bin/rpm -q kmod-rdac-PAE > /dev/null 2>&1;
kmodPAEInstalled=$?;

for kernelType in kernel kernel-PAE; do

    /bin/rpm -q ${kernelType} > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       continue;
    fi

    isPAE="";

    if [ ${kernelType} == "kernel-PAE" ]; then
       isPAE="PAE";
    fi

    for kernelImgVer in $(/bin/rpm -q ${kernelType} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${kernelType}-||"); do
        #If we have a PAE kernel and kmod-rdac-PAE is not installed then dont try to create the MPP kernel image or it will fail
    	if /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodPAEInstalled} -eq 1 ]; then
       	   /bin/echo "WARNING: kmod-rdac-PAE not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	   continue;
    	fi

        #If we have a non PAE kernel and kmod-rdac is not installed then dont try to create the MPP kernel image or it will fail
        if ! /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodInstalled} -eq 1 ]; then
            /bin/echo "WARNING: kmod-rdac not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	    continue;
        fi

        /opt/mpp/setupDriver.REDHAT ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
           /bin/echo "ERROR: Failed to create MPP ${initType} image for kernel ${kernelImgVer}...";
           exit 1;
        fi

        if [ -f /etc/modprobe.conf ]; then
            if ! /bin/grep "BEGIN OF MPP Driver Changes" /etc/modprobe.conf > /dev/null 2>&1 && [ -f /opt/mpp/modprobe.conf.mppappend ]; then
       	        /bin/echo "" >> /etc/modprobe.conf;	
       	        /bin/cat /opt/mpp/modprobe.conf.mppappend >> /etc/modprobe.conf;
            fi
        fi

        if ! /bin/grep "Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" /boot/grub/grub.conf > /dev/null 2>&1; then
            /sbin/grubby --grub --copy-default --add-kernel=/boot/vmlinuz-${kernelImgVer} --initrd=/boot/mpp-${kernelImgVer}.img --title="Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to add grub boot entry for MPP ${initType} image version ${kernelImgVer}...";
	        exit 1;
            fi
        fi

        /sbin/depmod ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
            /bin/echo "ERROR: Failed to update kernel module dependency maps for kernel version ${kernelImgVer}...";
            exit 1;
        fi

	/bin/rm -f /boot/${initType}-${kernelImgVer}.img.dup_orig > /dev/null 2>&1;

        if [ -f /boot/${initType}-${kernelImgVer}kdump.img ] && [ ! -f /boot/${initType}-${kernelImgVer}kdump.img.nompp ]; then
            if [ ! -f /boot/mpp-${kernelImgVer}.img ]; then
       	        /bin/echo "ERROR: No MPP ${initType} image available for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/mv -f /boot/${initType}-${kernelImgVer}kdump.img /boot/${initType}-${kernelImgVer}kdump.img.nompp > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to backup kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/cp -f /boot/mpp-${kernelImgVer}.img /boot/${initType}-${kernelImgVer}kdump.img > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to create MPP kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi
        fi 

        lastKernelImgVer="${kernelImgVer}";
    done
done

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerpostun -n rdac -- kernel
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

removedKernelVer="";

for mppInitRdVer in $(/bin/ls /boot/mpp-*.img 2>/dev/null | /bin/sed 's|/boot/mpp-||' | /bin/sed 's|.img||'); do
    if [ ! -z "${mppInitRdVer}" ]; then
       if [ ! -f /boot/vmlinuz-${mppInitRdVer} ]; then
       	  removedKernelVer="${mppInitRdVer}";

       	  /sbin/grubby --grub --remove-kernel="TITLE=Red Hat Enterprise Linux Server (${mppInitRdVer}) with MPP support" > /dev/null 2>&1;

       	  if [ $? -ne 0 ]; then
       	     /bin/echo "ERROR: Failed to remove grub boot entry for MPP ${initType} image version ${mppInitRdVer}...";
	     exit 1;
          fi

       	  /bin/rm -f /boot/mpp-${mppInitRdVer}.img > /dev/null 2>&1;

       	  if [ $? -ne 0 ]; then
       	     /bin/echo "ERROR: Failed to delete MPP ${initType} image version ${mppInitRdVer}...";
      	     exit 1;
          fi

       	  if [ -f /boot/${initType}-${mppInitRdVer}kdump.img.nompp ]; then
       	     /bin/mv -f /boot/${initType}-${mppInitRdVer}kdump.img.nompp /boot/${initType}-${mppInitRdVer}kdump.img > /dev/null 2>&1;
	  
	     if [ $? -ne 0 ]; then
	     	/bin/echo "ERROR: Faild to restore ${initType} kdump image for kernel ${mppInitRdVer}...";
	     	exit 1;
	     fi
          fi 
       fi
    fi
done

if [ -z "${removedKernelVer}" ]; then
   /bin/echo "ERROR: Failed to determine removed kernel version...";
   exit 1;
fi

isPAE="";
preferredKernel="kernel";

/bin/rpm -q kernel-PAE > /dev/null 2>&1;

if [ $? -eq 0 ]; then
   preferredKernel="kernel-PAE";
   isPAE="PAE";
fi

lastKernelImgVer=$(/bin/rpm -q ${preferredKernel} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${preferredKernel}-||" | /bin/grep -v "${removedKernelVer}" | /usr/bin/tail -n 1);

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerin -n rdac -- kernel-PAE
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

lastKernelImgVer="";

/bin/rpm -q kmod-rdac > /dev/null 2>&1;
kmodInstalled=$?;
/bin/rpm -q kmod-rdac-PAE > /dev/null 2>&1;
kmodPAEInstalled=$?;

for kernelType in kernel kernel-PAE; do

    /bin/rpm -q ${kernelType} > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       continue;
    fi

    isPAE="";

    if [ ${kernelType} == "kernel-PAE" ]; then
       isPAE="PAE";
    fi

    for kernelImgVer in $(/bin/rpm -q ${kernelType} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${kernelType}-||"); do
        #If we have a PAE kernel and kmod-rdac-PAE is not installed then dont try to create the MPP kernel image or it will fail
    	if /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodPAEInstalled} -eq 1 ]; then
       	   /bin/echo "WARNING: kmod-rdac-PAE not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	   continue;
    	fi

        #If we have a non PAE kernel and kmod-rdac is not installed then dont try to create the MPP kernel image or it will fail
        if ! /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodInstalled} -eq 1 ]; then
            /bin/echo "WARNING: kmod-rdac not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	    continue;
        fi

        /opt/mpp/setupDriver.REDHAT ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
           /bin/echo "ERROR: Failed to create MPP ${initType} image for kernel ${kernelImgVer}...";
           exit 1;
        fi

        if [ -f /etc/modprobe.conf ]; then
            if ! /bin/grep "BEGIN OF MPP Driver Changes" /etc/modprobe.conf > /dev/null 2>&1 && [ -f /opt/mpp/modprobe.conf.mppappend ]; then
       	        /bin/echo "" >> /etc/modprobe.conf;	
       	        /bin/cat /opt/mpp/modprobe.conf.mppappend >> /etc/modprobe.conf;
            fi
        fi

        if ! /bin/grep "Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" /boot/grub/grub.conf > /dev/null 2>&1; then
            /sbin/grubby --grub --copy-default --add-kernel=/boot/vmlinuz-${kernelImgVer} --initrd=/boot/mpp-${kernelImgVer}.img --title="Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to add grub boot entry for MPP ${initType} image version ${kernelImgVer}...";
	        exit 1;
            fi
        fi

        /sbin/depmod ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
            /bin/echo "ERROR: Failed to update kernel module dependency maps for kernel version ${kernelImgVer}...";
            exit 1;
        fi

	/bin/rm -f /boot/${initType}-${kernelImgVer}.img.dup_orig > /dev/null 2>&1;

        if [ -f /boot/${initType}-${kernelImgVer}kdump.img ] && [ ! -f /boot/${initType}-${kernelImgVer}kdump.img.nompp ]; then
            if [ ! -f /boot/mpp-${kernelImgVer}.img ]; then
       	        /bin/echo "ERROR: No MPP ${initType} image available for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/mv -f /boot/${initType}-${kernelImgVer}kdump.img /boot/${initType}-${kernelImgVer}kdump.img.nompp > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to backup kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/cp -f /boot/mpp-${kernelImgVer}.img /boot/${initType}-${kernelImgVer}kdump.img > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to create MPP kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi
        fi 

        lastKernelImgVer="${kernelImgVer}";
    done
done

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerpostun -n rdac -- kernel-PAE
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

removedKernelVer="";

for mppInitRdVer in $(/bin/ls /boot/mpp-*.img 2>/dev/null | /bin/sed 's|/boot/mpp-||' | /bin/sed 's|.img||'); do
    if [ ! -z "${mppInitRdVer}" ]; then
       if [ ! -f /boot/vmlinuz-${mppInitRdVer} ]; then
       	  removedKernelVer="${mppInitRdVer}";

       	  /sbin/grubby --grub --remove-kernel="TITLE=Red Hat Enterprise Linux Server (${mppInitRdVer}) with MPP support" > /dev/null 2>&1;

       	  if [ $? -ne 0 ]; then
       	     /bin/echo "ERROR: Failed to remove grub boot entry for MPP ${initType} image version ${mppInitRdVer}...";
	     exit 1;
          fi

       	  /bin/rm -f /boot/mpp-${mppInitRdVer}.img > /dev/null 2>&1;

       	  if [ $? -ne 0 ]; then
       	     /bin/echo "ERROR: Failed to delete MPP ${initType} image version ${mppInitRdVer}...";
      	     exit 1;
          fi

       	  if [ -f /boot/${initType}-${mppInitRdVer}kdump.img.nompp ]; then
       	     /bin/mv -f /boot/${initType}-${mppInitRdVer}kdump.img.nompp /boot/${initType}-${mppInitRdVer}kdump.img > /dev/null 2>&1;
	  
	     if [ $? -ne 0 ]; then
	     	/bin/echo "ERROR: Faild to restore ${initType} kdump image for kernel ${mppInitRdVer}...";
	     	exit 1;
	     fi
          fi 
       fi
    fi
done

if [ -z "${removedKernelVer}" ]; then
   /bin/echo "ERROR: Failed to determine removed kernel version...";
   exit 1;
fi

isPAE="";
preferredKernel="kernel";

/bin/rpm -q kernel-PAE > /dev/null 2>&1;

if [ $? -eq 0 ]; then
   preferredKernel="kernel-PAE";
   isPAE="PAE";
fi

lastKernelImgVer=$(/bin/rpm -q ${preferredKernel} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${preferredKernel}-||" | /bin/grep -v "${removedKernelVer}" | /usr/bin/tail -n 1);

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerin -n rdac -- kmod-rdac
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

lastKernelImgVer="";

/bin/rpm -q kmod-rdac > /dev/null 2>&1;
kmodInstalled=$?;
/bin/rpm -q kmod-rdac-PAE > /dev/null 2>&1;
kmodPAEInstalled=$?;

for kernelType in kernel kernel-PAE; do

    /bin/rpm -q ${kernelType} > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       continue;
    fi

    isPAE="";

    if [ ${kernelType} == "kernel-PAE" ]; then
       isPAE="PAE";
    fi

    for kernelImgVer in $(/bin/rpm -q ${kernelType} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${kernelType}-||"); do
        #If we have a PAE kernel and kmod-rdac-PAE is not installed then dont try to create the MPP kernel image or it will fail
    	if /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodPAEInstalled} -eq 1 ]; then
       	   /bin/echo "WARNING: kmod-rdac-PAE not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	   continue;
    	fi

        #If we have a non PAE kernel and kmod-rdac is not installed then dont try to create the MPP kernel image or it will fail
        if ! /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodInstalled} -eq 1 ]; then
            /bin/echo "WARNING: kmod-rdac not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	    continue;
        fi

        /opt/mpp/setupDriver.REDHAT ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
           /bin/echo "ERROR: Failed to create MPP ${initType} image for kernel ${kernelImgVer}...";
           exit 1;
        fi

        if [ -f /etc/modprobe.conf ]; then
            if ! /bin/grep "BEGIN OF MPP Driver Changes" /etc/modprobe.conf > /dev/null 2>&1 && [ -f /opt/mpp/modprobe.conf.mppappend ]; then
       	        /bin/echo "" >> /etc/modprobe.conf;	
       	        /bin/cat /opt/mpp/modprobe.conf.mppappend >> /etc/modprobe.conf;
            fi
        fi

        if ! /bin/grep "Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" /boot/grub/grub.conf > /dev/null 2>&1; then
            /sbin/grubby --grub --copy-default --add-kernel=/boot/vmlinuz-${kernelImgVer} --initrd=/boot/mpp-${kernelImgVer}.img --title="Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to add grub boot entry for MPP ${initType} image version ${kernelImgVer}...";
	        exit 1;
            fi
        fi

        /sbin/depmod ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
            /bin/echo "ERROR: Failed to update kernel module dependency maps for kernel version ${kernelImgVer}...";
            exit 1;
        fi

	/bin/rm -f /boot/${initType}-${kernelImgVer}.img.dup_orig > /dev/null 2>&1;

        if [ -f /boot/${initType}-${kernelImgVer}kdump.img ] && [ ! -f /boot/${initType}-${kernelImgVer}kdump.img.nompp ]; then
            if [ ! -f /boot/mpp-${kernelImgVer}.img ]; then
       	        /bin/echo "ERROR: No MPP ${initType} image available for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/mv -f /boot/${initType}-${kernelImgVer}kdump.img /boot/${initType}-${kernelImgVer}kdump.img.nompp > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to backup kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/cp -f /boot/mpp-${kernelImgVer}.img /boot/${initType}-${kernelImgVer}kdump.img > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to create MPP kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi
        fi 

        lastKernelImgVer="${kernelImgVer}";
    done
done

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerpostun -n rdac -- kmod-rdac
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

for mppInitRdVer in $(/bin/grep "with MPP support" /boot/grub/grub.conf 2>/dev/null | /bin/sed 's|.*(||' | /bin/sed 's|).*||' | /bin/grep -v PAE); do
    /sbin/grubby --grub --remove-kernel="TITLE=Red Hat Enterprise Linux Server (${mppInitRdVer}) with MPP support" > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       /bin/echo "ERROR: Failed to remove grub boot entry for MPP ${initType} image version ${mppInitRdVer}...";
       exit 1;
    fi
done

for initRdKdumpImg in $(/bin/ls /boot/${initType}-*kdump.img.nompp 2>/dev/null | /bin/grep -v PAE); do
    if [ ! -z "${initRdKdumpImg}" ]; then
        /bin/mv -f ${initRdKdumpImg} $(/bin/sed 's|.nompp||' <<< "${initRdKdumpImg}") > /dev/null 2>&1;

       	if [ $? -ne 0 ]; then
       	    /bin/echo "ERROR: Faild to restore ${initType} kdump image ${initRdKdumpImg}...";
	    exit 1;
        fi
    fi
done 

/bin/rm -f $(/bin/ls /boot/mpp-*.img | /bin/grep -v PAE) > /dev/null 2>&1;

if [ $? -ne 0 ]; then
    /bin/echo "ERROR: Failed to delete MPP ${initType} images...";
    exit 1;
fi

lastKernelImgVer=$(/bin/rpm -q kernel-PAE --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}PAE${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|kernel-PAE-||" | /usr/bin/tail -n 1);

if [ ! -z "${lastKernelImgVer}" ]; then
    /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
        /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
        exit 1;
    fi
else
    /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
    exit 1;
fi

%triggerin -n rdac -- kmod-rdac-PAE
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

lastKernelImgVer="";

/bin/rpm -q kmod-rdac > /dev/null 2>&1;
kmodInstalled=$?;
/bin/rpm -q kmod-rdac-PAE > /dev/null 2>&1;
kmodPAEInstalled=$?;

for kernelType in kernel kernel-PAE; do

    /bin/rpm -q ${kernelType} > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       continue;
    fi

    isPAE="";

    if [ ${kernelType} == "kernel-PAE" ]; then
       isPAE="PAE";
    fi

    for kernelImgVer in $(/bin/rpm -q ${kernelType} --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${isPAE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|${kernelType}-||"); do
        #If we have a PAE kernel and kmod-rdac-PAE is not installed then dont try to create the MPP kernel image or it will fail
    	if /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodPAEInstalled} -eq 1 ]; then
       	   /bin/echo "WARNING: kmod-rdac-PAE not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	   continue;
    	fi

        #If we have a non PAE kernel and kmod-rdac is not installed then dont try to create the MPP kernel image or it will fail
        if ! /bin/grep -i PAE <<< "${kernelImgVer}" > /dev/null && [ ${kmodInstalled} -eq 1 ]; then
            /bin/echo "WARNING: kmod-rdac not installed, skipping MPP init kernel image creation for kernel ${kernelImgVer}...";
       	    continue;
        fi

        /opt/mpp/setupDriver.REDHAT ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
           /bin/echo "ERROR: Failed to create MPP ${initType} image for kernel ${kernelImgVer}...";
           exit 1;
        fi

        if [ -f /etc/modprobe.conf ]; then
            if ! /bin/grep "BEGIN OF MPP Driver Changes" /etc/modprobe.conf > /dev/null 2>&1 && [ -f /opt/mpp/modprobe.conf.mppappend ]; then
       	        /bin/echo "" >> /etc/modprobe.conf;	
       	        /bin/cat /opt/mpp/modprobe.conf.mppappend >> /etc/modprobe.conf;
            fi
        fi

        if ! /bin/grep "Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" /boot/grub/grub.conf > /dev/null 2>&1; then
            /sbin/grubby --grub --copy-default --add-kernel=/boot/vmlinuz-${kernelImgVer} --initrd=/boot/mpp-${kernelImgVer}.img --title="Red Hat Enterprise Linux Server (${kernelImgVer}) with MPP support" > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to add grub boot entry for MPP ${initType} image version ${kernelImgVer}...";
	        exit 1;
            fi
        fi

        /sbin/depmod ${kernelImgVer} > /dev/null 2>&1;

        if [ $? -ne 0 ]; then
            /bin/echo "ERROR: Failed to update kernel module dependency maps for kernel version ${kernelImgVer}...";
            exit 1;
        fi

	/bin/rm -f /boot/${initType}-${kernelImgVer}.img.dup_orig > /dev/null 2>&1;

        if [ -f /boot/${initType}-${kernelImgVer}kdump.img ] && [ ! -f /boot/${initType}-${kernelImgVer}kdump.img.nompp ]; then
            if [ ! -f /boot/mpp-${kernelImgVer}.img ]; then
       	        /bin/echo "ERROR: No MPP ${initType} image available for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/mv -f /boot/${initType}-${kernelImgVer}kdump.img /boot/${initType}-${kernelImgVer}kdump.img.nompp > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to backup kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi

            /bin/cp -f /boot/mpp-${kernelImgVer}.img /boot/${initType}-${kernelImgVer}kdump.img > /dev/null 2>&1;

            if [ $? -ne 0 ]; then
       	        /bin/echo "ERROR: Failed to create MPP kdump ${initType} image for kernel ${kernelImgVer}...";
	        exit 1;
            fi
        fi 

        lastKernelImgVer="${kernelImgVer}";
    done
done

if [ ! -z "${lastKernelImgVer}" ]; then
   /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

   if [ $? -ne 0 ]; then
      /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
      exit 1;
   fi
else
   /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
   exit 1;
fi

%triggerpostun -n rdac -- kmod-rdac-PAE
%if %{?el6:1}%{!?el6:0}
archType=".%%{ARCH}";
initType="initramfs";
%else
archType="";
initType="initrd";
%endif

for mppInitRdVer in $(/bin/grep "with MPP support" /boot/grub/grub.conf 2>/dev/null | /bin/sed 's|.*(||' | /bin/sed 's|).*||' | /bin/grep PAE); do
    /sbin/grubby --grub --remove-kernel="TITLE=Red Hat Enterprise Linux Server (${mppInitRdVer}) with MPP support" > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
       /bin/echo "ERROR: Failed to remove grub boot entry for MPP ${initType} image version ${mppInitRdVer}...";
       exit 1;
    fi
done

for initRdKdumpImg in $(/bin/ls /boot/${initType}-*kdump.img.nompp 2>/dev/null | /bin/grep PAE); do
    if [ ! -z "${initRdKdumpImg}" ]; then
        /bin/mv -f ${initRdKdumpImg} $(/bin/sed 's|.nompp||' <<< "${initRdKdumpImg}") > /dev/null 2>&1;

       	if [ $? -ne 0 ]; then
       	    /bin/echo "ERROR: Faild to restore ${initType} kdump image ${initRdKdumpImg}...";
	    exit 1;
        fi
    fi
done 

/bin/rm -f $(/bin/ls /boot/mpp-*.img | /bin/grep PAE) > /dev/null 2>&1;

if [ $? -ne 0 ]; then
    /bin/echo "ERROR: Failed to delete MPP ${initType} images...";
    exit 1;
fi

lastKernelImgVer=$(/bin/rpm -q kernel --queryformat "%%{BUILDTIME} %%{VERSION}-%%{RELEASE}${archType}\n" 2>/dev/null | /bin/sort | /usr/bin/awk '{print $2;}' | /bin/sed "s|kernel-||" | /usr/bin/tail -n 1);

if [ ! -z "${lastKernelImgVer}" ]; then
    /sbin/grubby --grub --set-default="TITLE=Red Hat Enterprise Linux Server (${lastKernelImgVer}) with MPP support" > /dev/null 2>&1;

    if [ $? -ne 0 ]; then
        /bin/echo "ERROR: Failed to set grub boot entry to MPP ${initType} image version ${lastKernelImgVer}...";
        exit 1;
    fi
else
    /bin/echo "ERROR: Failed to find the latest kernel version to update grub boot entry...";
    exit 1;
fi

%files -n rdac
%defattr(-,root,root)
%attr(0444,root,root) %config /etc/mpp.conf
%attr(0755,root,root) %dir    /opt/mpp
%attr(0755,root,root) %dir    /var/mpp
%attr(0755,root,root) %dir    /opt/mpp/.mppLnx_rpm_helpers
#RHEL6 only files
%if %{?el6:1}%{!?el6:0}
%attr(0755,root,root) %dir    /usr/share/dracut/modules.d/90mpp
%attr(0644,root,root)         /usr/share/dracut/modules.d/90mpp/mpp-pre-udev.sh
%attr(0755,root,root)         /usr/share/dracut/modules.d/90mpp/install
%attr(0755,root,root)         /usr/share/dracut/modules.d/90mpp/installkernel
%endif
%attr(0755,root,root)         /etc/init.d/mpp
%attr(0500,root,root)         /opt/mpp/.mppLnx_rpm_helpers/hbaCheck
%attr(0500,root,root)         /opt/mpp/.mppLnx_rpm_helpers/setupDriver.REDHAT
%attr(0755,root,root)         /opt/mpp/.mppLnx_rpm_helpers/mpp
%attr(0644,root,root)         /var/mpp/devicemapping
%attr(0500,root,root)         /opt/mpp/genuniqueid
%attr(0500,root,root)         /opt/mpp/lsvdev
%attr(0500,root,root)         /opt/mpp/mppMkInitrdHelper
%attr(0500,root,root)         /opt/mpp/mppSupport
%attr(0500,root,root)         /opt/mpp/mppiscsi_umountall
%attr(0500,root,root)         /opt/mpp/makefile.saved
%attr(0500,root,root)         /opt/mpp/hbaCheck
%attr(0500,root,root)         /opt/mpp/setupDriver.REDHAT
%attr(0500,root,root)         %{_sbindir}/mpp*
%attr(0644,root,root)         %{_datadir}/man/man1/mpp*
%attr(0644,root,root)         %{_datadir}/man/man9/RDAC*

%changelog
* Wed Dec 11 2013 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-34
- Fix updating module dependency map on RH6 systems which now add the arch to the kernel module path

* Fri Oct 26 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-33
- Add triggers for kmod-rdac and kmod-rdac-PAE so they can be installed independently and the MPP images are configured as needed when it detects they are installed or removed
- Add cleanup of duplicate init image left after running depmod

* Thu Oct 25 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-31
- Fix bug in dependency name used between rpms which prevents install on 32bit systems that dont have a non PAE kernel installed
- Add a check to ensure kmod-rdac or kmod-rdac-PAE respectively installed for non PAE or PAE kernels before trying to create an MPP init kernel image for an installed kernel
- Add PAE kernel to the list of kernels checked and patch for true PAE support that was missing
- Fix bug in installing rpms where preferrence for the default boot kernel wasnt given to PAE kernels over non PAE kernels
- Fix bug in uninstall not preferring the newest PAE kernel over the newest non PAE kernel
- Add triggers for kernel-PAE so PAE kernels are auto configured

* Wed Oct 10 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-27
- Add explicit build arch to allow proper compilation on 32bit systems

* Tue Sep 11 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-26
- Readd RHEL6 support by re-adding missing dracut files
- Fix bug in uninstall cleanup, cleanup service scripts and modprobe confs created or modified by the mpp setup scripts
- Fix bug in error output on RHEL6 uninstall when /etc/modprobe.conf and kdump kernels dont exist
- Fix bug in init image name/types since RHEL6 uses a initramfs vs RHEL5 using initrd.
- Fix bug in not sorting the kernel versions correctly causing incorrect default kernel to be set in grub.
- Remove debug echo statements used to fix kernel sorting issue

* Thu Aug 30 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-18
- Add kmod MPP image support

* Fri Aug 24 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-17
- Change modprobe.conf setup to be dynamic instead of static, as the contents of the recommended modprobe config seem to be server specifc based on the hardware thats installed

* Thu Aug 23 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-15
- Add missing symlinks for files
- Add service script and other missing files
- Add service auto add/remove
- Note current changes support RHEL5 only, further modifications required to suppot RHEL6 in the future
- Add kernel modules dependcy map updating
- Fix bug in post uninstall, moved service removal from post uninstall to pre uninstall
- Fix bug with grub entries being added more than once due to typo in string check
- Fix bug in typo preventing proper removal/adding of symlink for hot_add
- Fix bug in sorting kernel versions on install/remove
- Fix bug in setting default kernel on kernel uninstall
- Fix bug in service script run levels
- Fix bug in add/removing kernel module configs from modprobe.conf

* Wed Aug 22 2012 Julio Lajara <ju2wheels@gmail.coom> - 09.03.0C05.0504-3
- Add kmod-rdac and grubby as requires for rdac
- Add automatic build/removal of MPP initrd images
- Add automatic add/removal of MPP grub boot menu options
- Fix permission issue when using non normal umask by specifying explicit file permissions
- Add missing /var/mpp/devicemapping file

* Mon Dec 12 2011 Josko Plazonic <plazonic@math.princeton.edu>
- rebuild due to changed abi

* Fri Jul 09 2010 Josko Plazonic <plazonic@math.princeton.edu>
- initial build

