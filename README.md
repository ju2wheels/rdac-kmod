# NetApp RDAC driver RPM

This rpm is a highly modified version of the release available from http://pkgs.org/centos-5-rhel-5/puias-computational-x86_64/kmod-rdac-09.03.0C05.0331-0.4.PU_IAS.5.x86_64.rpm.html which was packaged for RHEL6. Modifications were made to port it RHEL5 as well as allow it to automatically detect when a new kernel is installed and automatically update the kernel init image and set the default boot kernel to the one that includes the RDAC driver.

The original rpm provides kmod RDAC kernel modules compiled in a kernel agnostic manner against the stable ABI meaning as long as the ABI doesnt change from one kernel release to the next, then there is no need to recompile/rebuild the driver rpm thus allowing it work across multple kernel versions.

**WARNING** DO NOT install this rpm on a box where you have previous manually compiled/installed the RDAC drivers. The rpm must be installed on a box that hasnt yet had RDAC drivers installed on it (see below on how to properly remove any previous installs).

Building the RPM requires downloading the source for the RDAC drivers from NetApp (automated as part of build script).

Building the rpm:
  1. Install the build dependencies of gcc, make, buildsys-macros, rpm-build and kernel-devel (and kernel-PAE-devel on 32bit systems only):
    ```
    yum install gcc make buildsys-macros rpm-build kernel-devel kernel-PAE-devel
    ```

  2. If building on RH 6, install the kernel ABI whitelists:
    ```
	yum install kabi-whitelists kernel-abi-whitelists
	```

  2. Start the rpm build as a regular user (requires internet access to download the RDAC drivers):
    ```
    ./rdac-kmod-rpmbuild.sh
    ```

  3. Check for your rpms in `~/rpmbuild/RPMS/`.
  
# Supported Platforms
The RDAC kmod driver supports RH/Suse, however this customized RPM only supports RH (or similar distros such as Centos/SL). In order to add support for Suse you should review the install scripts and add any missing actions as described in question 4 below.

# Questions/Troubleshooting
1. When do the drivers/rpm need to be recompiled/upgraded?
  >The rpms will need to be rebuilt any time there is a change in the kernel ABI (kABI) or when you want to upgrade to a new driver version. More information on the kernel ABI can be found in the [Redhat Driver Update Packages Guide](http://people.redhat.com/jcm/el6/dup/docs/dup_book.pdf).

2. How do I check if a new kernel's ABI is supported by the current RDAC kernel module rpms?
  >This is done by validating the hashes of the ABI groups provided in the rpm to that of the kernel (note that this should be handled by rpm automatically but its a good pre kernel upgrade manual test to ensure they are compatible:

    * Check the ABI hashes of the last compiled RDAC kmod RPM:
      ```
      $ rpm --requires -qp kmod-rdac-09.03.0C05.0504-25.el5.x86_64.rpm | grep kernel
      kernel(rhel5_drivers_base_ga) = 61dc730b8ca5e74017f2df5b55ecda8b7df7f9c2
      kernel(rhel5_vmlinux_ga) = 78f928da689a93ecf2e044fc0ced6b3eaedf5c19
      kernel(rhel5_drivers_scsi_ga) = 1cc16b1f8996d37eaa858690bfbab7f4030c55b6
      kernel(rhel5_kernel_ga) = 84d69198cf51b494e38d9d0a54e52607c8a507e2
      kernel(rhel5_mm_ga) = d5edc1b3d2a4f2bf8ce28d7f4dbeab27cfeb19bd
      kernel(rhel5_lib_ga) = ff25b583d6d314edd98f7c9533c5867194b3d30d
      kernel(rhel5_fs_proc_ga) = 30f9166e128d20c7305d5a9bc9ab69451c40a555
      kernel(rhel5_block_ga) = 5b4effd1cc3809b4bd243e499ab6be486fd95fd9
      kernel(rhel5_fs_ga) = 1c422a6b84a2000991b1b99c61506cfd711a20d1
      kernel(rhel5_fs_u4) = 518e7b7963ed0843e4b55b64ba2b25db95cf821a
      kernel(rhel5_arch_x86_64_kernel_ga) = 880dbfce5086d666f5bab6ad642c0323fcdabd90
      kernel(rhel5_drivers_xen_core_ga) = c05a8027c47f037b99169c7441da64fa0a723869
      kernel(rhel5_kernel_module_ga) = a74a9d2bf87d13d6b9412698dc2728248ca92523
      ```

    * Check the ABI hashes of the new kernel you want to install:
      ```
      $ rpm --provides -q kernel-2.6.18-308.13.1.el5 | grep "kernel("
      kernel(rhel5_gfs2_ga) = 73e828ddf6a8787f935f6088a18a862409174aaf
      kernel(rhel5_fs_lockd_ga) = 67913a0875a3219e6b8c2d914775c91fab5b7c4f
      kernel(rhel5_drivers_hwmon_ga) = 21462092aeb2b284e955337136d204c26f79ed92
      kernel(rhel5_net_core_ga) = c186a7dc043c903564c2dd9ed49d8847b7043c86
      ``` 

    * Run the following one liner to find any missing ABI hashes:
      ```
      $ for modDep in $(rpm --requires -qp kmod-rdac-09.03.0C05.0504-25.el5.x86_64.rpm | grep kernel); do if ! /bin/grep "${modDep}" <<< "$(rpm --provides -q kernel-2.6.18-308.13.1.el5)" > /dev/null; then echo "ERROR: NOT FOUND ${modDep}"; fi done
      ```

3. What steps do I need to perform before installing the rpms on a system which already has the RDAC drivers installed manually from source?
  >Perform the following steps to uninstall manually installed RDAC kmod instances:
    1. Unmount all partitions that are using the RDAC driver (and comment them out in /etc/fstab if needed) and unmap all LUNs.
    2. Remove all MPP kernel boot entries from /boot/grub/grub.conf
    3. Remove all MPP init images: `/bin/rm -f /boot/mpp-*.img`
    4. Remove all lines from `/etc/modprobe.conf` and `/etc/modprobe.conf.local` that match the lines in `/opt/mpp/modprobe.conf.mppappend`
    5. Run the uninstall script: `make -f /opt/mpp/makefile.saved uninstall`
    6. Reboot the box

4. Will the current rdac-kmod.spec file work for new versions of the RDAC driver?
  >Theres no way to know before hand whether the existing spec file will work for future versions of the RDAC driver without modification as this is 100% dependent on what changes are made to the make file for the new release. You will have to review changes that are made to the copyfiles, copyrpmfiles, moduledep, setupfiles, setupdriver, uninstall, and uninstall_doer sections of the make/install files and ensure the same steps are done in the proper sections of the spec file if necessary.

5. I have installed the RDAC rpms and will be doing a kernel upgrade, what steps do I need to perform?
  >If you have done the pre-upgrade check in step 2 and no errors are reported, then just upgrade the kernel as normal and there are no extra steps, the rpm will handle the rest.
