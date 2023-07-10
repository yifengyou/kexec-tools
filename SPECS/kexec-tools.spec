Name: kexec-tools
Version: 2.0.25
Release: 5%{?dist}.1
License: GPLv2
Group: Applications/System
Summary: The kexec/kdump userspace component

Source0: http://kernel.org/pub/linux/utils/kernel/kexec/%{name}-%{version}.tar.xz
Source1: kdumpctl
Source2: kdump.sysconfig
Source3: kdump.sysconfig.x86_64
Source4: kdump.sysconfig.i386
Source5: kdump.sysconfig.ppc64
Source7: mkdumprd
Source8: gen-kdump-conf.sh
Source9: https://github.com/makedumpfile/makedumpfile/archive/1.7.1.tar.gz
Source10: kexec-kdump-howto.txt
Source12: mkdumprd.8
Source13: 98-kexec.rules
Source14: 98-kexec.rules.ppc64
Source15: kdump.conf.5
Source16: kdump.service
Source18: kdump.sysconfig.s390x
Source19: eppic_050615.tar.gz
Source20: kdump-lib.sh
Source21: kdump-in-cluster-environment.txt
Source22: kdump-dep-generator.sh
Source23: kdump-lib-initramfs.sh
Source24: kdump.sysconfig.ppc64le
Source25: kdumpctl.8
Source26: live-image-kdump-howto.txt
Source27: early-kdump-howto.txt
Source28: supported-kdump-targets.txt
Source29: kdump-udev-throttler
Source30: kdump.sysconfig.aarch64
Source31: fadump-howto.txt
Source32: 60-kdump.install
Source33: kdump-logger.sh
Source34: kdump-migrate-action.sh
Source35: kdump-restart.sh
Source36: mkfadumprd

#######################################
# These are sources for mkdumpramfs
# Which is currently in development
#######################################
Source100: dracut-kdump.sh
Source101: dracut-module-setup.sh
Source102: dracut-monitor_dd_progress
Source103: dracut-kdump-error-handler.sh
Source104: dracut-kdump-emergency.service
Source105: dracut-kdump-error-handler.service
Source106: dracut-kdump-capture.service
Source107: dracut-kdump-emergency.target
Source108: dracut-early-kdump.sh
Source109: dracut-early-kdump-module-setup.sh

Source200: dracut-fadump-init-fadump.sh
Source201: dracut-fadump-module-setup.sh

%ifarch ppc64 ppc64le
Requires(post): servicelog
Recommends: keyutils
%endif

Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
Requires(pre): coreutils sed zlib 
Requires: dracut >= 049-129
Requires: dracut-network >= 049
Requires: dracut-squash >= 049
Requires: ethtool
BuildRequires: zlib-devel zlib zlib-static elfutils-devel glib2-devel bzip2-devel ncurses-devel bison flex lzo-devel snappy-devel libzstd-devel
BuildRequires: pkgconfig intltool gettext 
BuildRequires: systemd-units
BuildRequires: automake autoconf libtool
%ifarch %{ix86} x86_64 ppc64 ppc s390x ppc64le
Obsoletes: diskdumputils netdump kexec-tools-eppic
%endif

ExcludeArch: i686

#START INSERT

#
# Patches 0 through 100 are meant for x86 kexec-tools enablement
#

#
# Patches 101 through 200 are meant for x86_64 kexec-tools enablement
#

#
# Patches 301 through 400 are meant for ppc64 kexec-tools enablement
#

#
# Patches 401 through 500 are meant for s390 kexec-tools enablement
#

#
# Patches 501 through 600 are meant for ARM kexec-tools enablement
#

#
# Patches 601 onward are generic patches
#
Patch601: rhelonly-kexec-tools-2.0.16-koji-build-fail-workaround.patch
Patch602: rhelonly-kexec-tools-2.0.18-eppic-fix-issues-with-hardening-flags.patch

# Patches 701 onward for makedumpfile
Patch701: rhelonly-kexec-tools-2.0.20-makedumpfile-arm64-Add-support-for-ARMv8.2-LVA-52-bi.patch
Patch702: kexec-tools-2.0.24-makedumpfile-Avoid_false_positive_mem_section_validation_with_vmlinux.patch
Patch703: kexec-tools-2.0.25-makedumpfile-sadump-fix-failure-of-reading-memory-when-5-le.patch

%description
kexec-tools provides /usr/sbin/kexec binary that facilitates a new
kernel to boot using the kernel's kexec feature either on a
normal or a panic reboot. This package contains the /usr/sbin/kexec
binary and ancillary utilities that together form the userspace
component of the kernel's kexec feature.

%prep
%setup -q 

mkdir -p -m755 kcp
tar -z -x -v -f %{SOURCE9}
tar -z -x -v -f %{SOURCE19}

%patch601 -p1
%patch602 -p1

%patch701 -p1
%patch702 -p1
%patch703 -p1

%ifarch ppc
%define archdef ARCH=ppc
%endif

%build
autoreconf
%configure \
%ifarch ppc64
    --host=powerpc64-redhat-linux-gnu \
    --build=powerpc64-redhat-linux-gnu \
%endif
%ifarch ppc64le
    --host=powerpc64le-redhat-linux-gnu \
    --build=powerpc64le-redhat-linux-gnu \
%endif
    --sbindir=/usr/sbin
rm -f kexec-tools.spec.in
# setup the docs
cp %{SOURCE10} .
cp %{SOURCE21} .
cp %{SOURCE26} .
cp %{SOURCE27} .
cp %{SOURCE28} .
cp %{SOURCE31} .

# Generate sysconfig file
%{SOURCE8} %{_target_cpu} > kdump.conf

make
%ifarch %{ix86} x86_64 ppc64 s390x ppc64le aarch64
make -C eppic/libeppic
make -C makedumpfile-1.7.1 LINKTYPE=dynamic USELZO=on USESNAPPY=on USEZSTD=on
make -C makedumpfile-1.7.1 LDFLAGS="$LDFLAGS -I../eppic/libeppic -L../eppic/libeppic" eppic_makedumpfile.so
%endif

%install
mkdir -p -m755 $RPM_BUILD_ROOT/usr/sbin
mkdir -p -m755 $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
mkdir -p -m755 $RPM_BUILD_ROOT%{_sysconfdir}/kdump
mkdir -p -m755 $RPM_BUILD_ROOT%{_sysconfdir}/kdump/pre.d
mkdir -p -m755 $RPM_BUILD_ROOT%{_sysconfdir}/kdump/post.d
mkdir -p -m755 $RPM_BUILD_ROOT%{_localstatedir}/crash
mkdir -p -m755 $RPM_BUILD_ROOT%{_mandir}/man8/
mkdir -p -m755 $RPM_BUILD_ROOT%{_mandir}/man5/
mkdir -p -m755 $RPM_BUILD_ROOT%{_docdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_datadir}/kdump
mkdir -p -m755 $RPM_BUILD_ROOT%{_udevrulesdir}
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_bindir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_libdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_prefix}/lib/kdump
mkdir -p -m755 $RPM_BUILD_ROOT%{_sharedstatedir}/kdump
install -m 755 %{SOURCE1} $RPM_BUILD_ROOT%{_bindir}/kdumpctl

install -m 755 build/sbin/kexec $RPM_BUILD_ROOT/usr/sbin/kexec
install -m 755 build/sbin/vmcore-dmesg $RPM_BUILD_ROOT/usr/sbin/vmcore-dmesg
install -m 644 build/man/man8/kexec.8  $RPM_BUILD_ROOT%{_mandir}/man8/
install -m 644 build/man/man8/vmcore-dmesg.8  $RPM_BUILD_ROOT%{_mandir}/man8/

SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig.%{_target_cpu}
[ -f $SYSCONFIG ] || SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig.%{_arch}
[ -f $SYSCONFIG ] || SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig
install -m 644 $SYSCONFIG $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/kdump

install -m 755 %{SOURCE7} $RPM_BUILD_ROOT/usr/sbin/mkdumprd
install -m 755 %{SOURCE36} $RPM_BUILD_ROOT/usr/sbin/mkfadumprd
install -m 644 kdump.conf $RPM_BUILD_ROOT%{_sysconfdir}/kdump.conf
install -m 644 kexec/kexec.8 $RPM_BUILD_ROOT%{_mandir}/man8/kexec.8
install -m 644 %{SOURCE12} $RPM_BUILD_ROOT%{_mandir}/man8/mkdumprd.8
install -m 644 %{SOURCE25} $RPM_BUILD_ROOT%{_mandir}/man8/kdumpctl.8
install -m 755 %{SOURCE20} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-lib.sh
install -m 755 %{SOURCE23} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-lib-initramfs.sh
install -m 755 %{SOURCE33} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-logger.sh
%ifnarch s390x ppc64 ppc64le
# For s390x the ELF header is created in the kdump kernel and therefore kexec
# udev rules are not required
install -m 644 %{SOURCE13} $RPM_BUILD_ROOT%{_udevrulesdir}/98-kexec.rules
%endif
%ifarch ppc64 ppc64le
install -m 644 %{SOURCE14} $RPM_BUILD_ROOT%{_udevrulesdir}/98-kexec.rules
install -m 755 %{SOURCE34} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-migrate-action.sh
install -m 755 %{SOURCE35} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-restart.sh
%endif
%ifnarch s390x
install -m 755 %{SOURCE29} $RPM_BUILD_ROOT%{_udevrulesdir}/../kdump-udev-throttler
%endif
install -m 644 %{SOURCE15} $RPM_BUILD_ROOT%{_mandir}/man5/kdump.conf.5
install -m 644 %{SOURCE16} $RPM_BUILD_ROOT%{_unitdir}/kdump.service
install -m 755 -D %{SOURCE22} $RPM_BUILD_ROOT%{_prefix}/lib/systemd/system-generators/kdump-dep-generator.sh
install -m 755 -D %{SOURCE32} $RPM_BUILD_ROOT%{_prefix}/lib/kernel/install.d/60-kdump.install


%ifarch %{ix86} x86_64 ppc64 s390x ppc64le aarch64
install -m 755 makedumpfile-1.7.1/makedumpfile $RPM_BUILD_ROOT/usr/sbin/makedumpfile
install -m 644 makedumpfile-1.7.1/makedumpfile.8 $RPM_BUILD_ROOT/%{_mandir}/man8/makedumpfile.8
install -m 644 makedumpfile-1.7.1/makedumpfile.conf.5 $RPM_BUILD_ROOT/%{_mandir}/man5/makedumpfile.conf.5
install -m 644 makedumpfile-1.7.1/makedumpfile.conf $RPM_BUILD_ROOT/%{_sysconfdir}/makedumpfile.conf.sample
install -m 755 makedumpfile-1.7.1/eppic_makedumpfile.so $RPM_BUILD_ROOT/%{_libdir}/eppic_makedumpfile.so
mkdir -p $RPM_BUILD_ROOT/usr/share/makedumpfile/eppic_scripts/
install -m 644 makedumpfile-1.7.1/eppic_scripts/* $RPM_BUILD_ROOT/usr/share/makedumpfile/eppic_scripts/
%endif

%define remove_dracut_prefix() %(echo -n %1|sed 's/.*dracut-//g')
%define remove_dracut_early_kdump_prefix() %(echo -n %1|sed 's/.*dracut-early-kdump-//g')
%define remove_dracut_fadump_prefix() %(echo -n %1|sed 's/.*dracut-fadump-//g')

# deal with dracut modules
mkdir -p -m755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase
cp %{SOURCE100} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE100}}
cp %{SOURCE101} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE101}}
cp %{SOURCE102} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE102}}
cp %{SOURCE103} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE103}}
cp %{SOURCE104} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE104}}
cp %{SOURCE105} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE105}}
cp %{SOURCE106} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE106}}
cp %{SOURCE107} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE107}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE100}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE101}}
mkdir -p -m755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99earlykdump
cp %{SOURCE108} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99earlykdump/%{remove_dracut_prefix %{SOURCE108}}
cp %{SOURCE109} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99earlykdump/%{remove_dracut_early_kdump_prefix %{SOURCE109}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99earlykdump/%{remove_dracut_prefix %{SOURCE108}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99earlykdump/%{remove_dracut_early_kdump_prefix %{SOURCE109}}
%ifarch ppc64 ppc64le
mkdir -p -m755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99zz-fadumpinit
cp %{SOURCE200} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99zz-fadumpinit/%{remove_dracut_fadump_prefix %{SOURCE200}}
cp %{SOURCE201} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99zz-fadumpinit/%{remove_dracut_fadump_prefix %{SOURCE201}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99zz-fadumpinit/%{remove_dracut_fadump_prefix %{SOURCE200}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99zz-fadumpinit/%{remove_dracut_fadump_prefix %{SOURCE201}}
%endif


%define dracutlibdir %{_prefix}/lib/dracut
#and move the custom dracut modules to the dracut directory
mkdir -p $RPM_BUILD_ROOT/%{dracutlibdir}/modules.d/
mv $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/* $RPM_BUILD_ROOT/%{dracutlibdir}/modules.d/

%post
# Initial installation
%systemd_post kdump.service

touch /etc/kdump.conf

%ifarch ppc64 ppc64le
servicelog_notify --remove --command=/usr/lib/kdump/kdump-migrate-action.sh 2>/dev/null
servicelog_notify --add --command=/usr/lib/kdump/kdump-migrate-action.sh --match='refcode="#MIGRATE" and serviceable=0' --type=EVENT --method=pairs_stdin
%endif


# This portion of the script is temporary.  Its only here
# to fix up broken boxes that require special settings 
# in /etc/sysconfig/kdump.  It will be removed when 
# These systems are fixed.

if [ -d /proc/bus/mckinley ]
then
	# This is for HP zx1 machines
	# They require machvec=dig on the kernel command line
	sed -e's/\(^KDUMP_COMMANDLINE_APPEND.*\)\("$\)/\1 machvec=dig"/' \
	/etc/sysconfig/kdump > /etc/sysconfig/kdump.new
	mv /etc/sysconfig/kdump.new /etc/sysconfig/kdump
elif [ -d /proc/sgi_sn ]
then
	# This is for SGI SN boxes
	# They require the --noio option to kexec 
	# since they don't support legacy io
	sed -e's/\(^KEXEC_ARGS.*\)\("$\)/\1 --noio"/' \
	/etc/sysconfig/kdump > /etc/sysconfig/kdump.new
	mv /etc/sysconfig/kdump.new /etc/sysconfig/kdump
fi


%postun
%systemd_postun_with_restart kdump.service

%preun
%ifarch ppc64 ppc64le
servicelog_notify --remove --command=/usr/lib/kdump/kdump-migrate-action.sh
%endif
# Package removal, not upgrade
%systemd_preun kdump.service

%triggerun -- kexec-tools < 2.0.2-3
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply kdump
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save kdump >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/usr/sbin/chkconfig --del kdump >/dev/null 2>&1 || :
/bin/systemctl try-restart kdump.service >/dev/null 2>&1 || :


%triggerin -- kernel-kdump
touch %{_sysconfdir}/kdump.conf


%triggerpostun -- kernel kernel-xen kernel-debug kernel-PAE kernel-kdump
# List out the initrds here, strip out version nubmers
# and search for corresponding kernel installs, if a kernel
# is not found, remove the corresponding kdump initrd


IMGDIR=/boot
for i in `ls $IMGDIR/initramfs*kdump.img 2>/dev/null`
do
	KDVER=`echo $i | sed -e's/^.*initramfs-//' -e's/kdump.*$//'`
	if [ ! -e $IMGDIR/vmlinuz-$KDVER ]
	then
		# We have found an initrd with no corresponding kernel
		# so we should be able to remove it
		rm -f $i
	fi
done

%files
/usr/sbin/kexec
/usr/sbin/makedumpfile
/usr/sbin/mkdumprd
/usr/sbin/mkfadumprd
/usr/sbin/vmcore-dmesg
%{_bindir}/*
%{_datadir}/kdump
%{_prefix}/lib/kdump
%ifarch %{ix86} x86_64 ppc64 s390x ppc64le aarch64
%{_sysconfdir}/makedumpfile.conf.sample
%endif
%config(noreplace,missingok) %{_sysconfdir}/sysconfig/kdump
%config(noreplace,missingok) %verify(not mtime) %{_sysconfdir}/kdump.conf
%ifnarch s390x
%config %{_udevrulesdir}
%{_udevrulesdir}/../kdump-udev-throttler
%endif
%{dracutlibdir}/modules.d/*
%dir %{_localstatedir}/crash
%dir %{_sysconfdir}/kdump
%dir %{_sysconfdir}/kdump/pre.d
%dir %{_sysconfdir}/kdump/post.d
%dir %{_sharedstatedir}/kdump
%{_mandir}/man8/kdumpctl.8.gz
%{_mandir}/man8/kexec.8.gz
%{_mandir}/man8/makedumpfile.8.gz
%{_mandir}/man8/mkdumprd.8.gz
%{_mandir}/man8/vmcore-dmesg.8.gz
%{_mandir}/man5/*
%{_unitdir}/kdump.service
%{_prefix}/lib/systemd/system-generators/kdump-dep-generator.sh
%{_prefix}/lib/kernel/install.d/60-kdump.install
%doc News
%license COPYING
%doc TODO
%doc kexec-kdump-howto.txt
%doc early-kdump-howto.txt
%doc fadump-howto.txt
%doc supported-kdump-targets.txt
%doc kdump-in-cluster-environment.txt
%doc live-image-kdump-howto.txt
%ifarch %{ix86} x86_64 ppc64 s390x ppc64le aarch64
%{_libdir}/eppic_makedumpfile.so
/usr/share/makedumpfile/
%endif

%changelog
* Thu May  4 2023 Pingfan Liu <piliu@redhat.com> - 2.0.25-5.1
- sadump: fix failure of reading memory when 5-level paging is enabled

* Wed Jan 18 2023 Pingfan Liu <piliu@redhat.com> - 2.0.25-5
 dracut-module-setup: Fix invalid rd.znet command line entry
 dracut-module-setup: Fix persistent nic name on s390

* Mon Jan  9 2023 Pingfan Liu <piliu@redhat.com> - 2.0.25-4
- Don't check fs modified when dump target is lvm2 thinp
- Add dependency of dracut lvmthinpool-monitor module
- lvm.conf should be check modified if lvm2 thinp enabled
- Add lvm2 thin provision dump target checker
- Fix the sync issue for dump_fs

* Fri Dec  2 2022 Pingfan Liu <piliu@redhat.com> - 2.0.25-3
- kdump.conf: use a simple generator script to maintain
- Reduce kdump memory consumption by not letting NetworkManager manage unneeded network interfaces

* Mon Oct 17 2022 Pingfan Liu <piliu@redhat.com> - 2.0.25-2
- mkdumprd: Improve error messages on non-existing NFS target directories
- fadump: avoid non-debug kernel use for fadump case

* Sun Sep 18 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-7
- kdumpctl: make the kdump.log root-readable-only

* Mon Jul 18 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-6
- kdump-lib: Add the CoreOS kernel dir to the boot_dirlist
- kdump-lib: attempt to fix BOOT_IMAGE detection
- kdump-lib: change how ostree based systems are detected
- kdump-lib: clear up references to Atomic/CoreOS

* Mon Jul 4 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-5
- kdump-lib: use non-debug kernels first

* Tue Jun 21 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-4
- kdump-lib.sh: Check the output of blkid with sed instead of eval

* Fri Jun 10 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-3
- kdump.sysconfig*: add ignition.firstboot to KDUMP_COMMANDLINE_REMOVE

* Fri May 27 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-2
- kdumpctl: fix missed dollar sign

* Thu May  5 2022 Pingfan Liu <piliu@redhat.com> - 2.0.24-1
- kdumpctl: sync the $TARGET_INITRD after rebuild
- Avoid false-positive mem_section validation with vmlinux
- Rebase kexec-tools to 2.0.24
- Rebase makedumpfile to 1.7.1

* Fri Apr 15 2022 Pingfan Liu <piliu@redhat.com> - 2.0.20-69
- s390: add support for --reuse-cmdline
- use slurp_proc_file() in get_command_line()
- add slurp_proc_file()
- s390: use KEXEC_ALL_OPTIONS
- s390: add variable command line size
- util_lib/elf_info: harden parsing of printk buffer
- print error when reading with unsupported compression
- use cycle detection when parsing the prink log_buf
- use pointer arithmetics for dump_dmesg
- add generic cycle detection

* Thu Jan 27 2022 Pingfan Liu <piliu@redhat.com> - 2.0.20-68
- Revert "Remove trace_buf_size and trace_event from the kernel bootparameters of the kdump kernel"

* Fri Dec 24 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-67
- Remove trace_buf_size and trace_event from the kernel bootparameters of the kdump kernel

* Fri Dec 10 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-66
- kdump/ppc64: suppress the error message "Could not find a registered notification tool" from servicelog_notify
- Enable zstd compression for makedumpfile in kexec-tools.spec

* Thu Dec  2 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-65
- mkdumprd: drop mountaddr/mountproto nfs mount options 

* Fri Nov 26 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-64
- add keytuils as a weak dependency for POWER

* Fri Nov 19 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-63
- Document/kexec-kdump-howto.txt: fix escape

* Wed Nov 17 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-62
- Document/kexec-kdump-howto.txt: improve notes for kdump_pre  and kdump_post scripts

* Tue Nov  9 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-61
- rebase makedumpfile to 1.7.0

* Fri Oct 22 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-60
- fadump-init: clean up mount points properly
- fadump: kdumpctl should check the modules used by the fadump initramfs
- fadump: isolate fadump initramfs image within the default one
- mkdumprd: Use xz for squash image compression

* Mon Oct 18 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-59
- makedumpfile: printk: use committed/finalized state values
- makedumpfile: printk: add support for lockless ringbuffer
- kexec-tools: printk: Use %zu to format size_t
- kexec-tools: printk: Use ULL suffix for 64-bit constants
- kexec-tools: printk: add support for lockless ringbuffer

* Sun Oct 17 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-58
- kdumpctl: fix fragile loops over find output

* Fri Aug 27 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-57
- kdumpctl: enable secure boot on ppc64le LPARs

* Fri Aug  6 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-56
- kdumpctl: fix a typo

* Mon Aug  2 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-55
- kdump/ppc64: migration action registration clean up

* Fri Jul 23 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-54
- kdump/ppc64: rebuild initramfs image after migration
- Check the existence of /sys/bus/ccwgroup/devices/*/online beforehand
- kdump.sysconfig.s390: Remove "prot_virt" from kdump kernel cmdline

* Fri Jul  2 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-53
- check for invalid physical address of /proc/kcore when making ELF dumpfile
- check for invalid physical address of /proc/kcore when finding max_paddr
- fix format issue in find_online_znet_device
- check the existence of /sys/bus/ccwgroup/devices before trying to find online network device
- kdump-lib.sh: fix a warning in prepare_kdump_bootinfo()

* Thu Jun 17 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-52
- Write to `/var/lib/kdump` if $KDUMP_BOOTDIR not writable
- Iterate /sys/bus/ccwgroup/devices to tell if we should set up rd.znet
- mkdumprd: display the absolute path of dump location in the check_user_configured_target()

* Wed Jun  2 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-51
- Stop reloading kdump service on CPU hotplug event for FADump
- fadump: improve fadump-howto.txt about remote dump target setup

* Tue May 25 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-50
- rd.route should use the name from kdump_setup_ifname
- get kdump ifname once in kdump_install_netdev

* Tue May 25 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-49
- kdump-lib.sh: fix the case if no enough total RAM for kdump  in get_recommend_size()

* Thu May 20 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-48
- kdumpctl: Add kdumpctl estimate
- mkdumprd: make use of the new get_luks_crypt_dev helper
- kdump-lib.sh: introduce a helper to get all crypt dev used by kdump
- kdump-lib.sh: introduce a helper to get underlying crypt device
- RHEL-only: keep total memory size coherent to RHEL-only kernel patch
- Show write byte size in report messages
- Add shorthand --show-stats option to show report stats
- Add --dry-run option to prevent writing the dumpfile
- kdump-lib.sh: introduce functions to return recommened mem size

* Mon May 10 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-47
- Implement IP netmask calculation to replace "ipcalc -m"
- kdumpctl: fix check_config error when kdump.conf is empty
- Fix incorrect vmcore permissions when dumped through ssh
- Fix incorrect permissions on kdump dmesg file

* Mon Jan 25 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-45
- origin/rhel-8.4.0) Revert "Revert "Append both nofail and x-systemd.before to kdump mount target""
- kdump.conf: add ipv6 example for nfs and ssh dump
- fix kdump failure of saving vmcore with the scp + ipv6 method

* Fri Jan 22 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-44
- module-setup.sh: don't polute the namespace unnecessarily
- module-setup.sh: don't source $dracutfunctions
- logger: source the logger file individually
- dracut-module-setup.sh: enable ForwardToConsole=yes in fadump mode

* Fri Jan 15 2021 Pingfan Liu <piliu@redhat.com> - 2.0.20-43
- Always include watchdog-modules
- mkdumprd: Ensure kdumpbase is added
- Move watchdog detect and install code to module-setup.sh
- Add a helper to omit non-mandatory dracut module
- Move some dracut module dependencies checks to module-setup.sh
- Set watchdog's pretimeout to zero in kdump kernel
- kdump-lib.sh: Use a more generic helper to detect omitted dracut module
- Fix the watchdog drivers detection code
- Add a helper for detecting watchdog drivers
- Remove a redundant nfs check
- kdumpctl: split the driver detection from fs dection function
- kdump.service: use ConditionKernelCommandLine=crashkernel
- Revert "Append both nofail and x-systemd.before to kdump mount target"
- Revert "Don's try to restart dracut-initqueue if it's already failed"
- Fix dump_fs mount point detection and fallback mount
- kdump.conf: Update doc about core_collector for ssh target
- Save the final failure information to log file if saving vmcore failed
- Doc: Improve the kdump sysconfig document
- kdumpctl: fix a variable expansion in check_fence_kdump_config()
- Fedora 33 rhpkg build bug

* Tue Dec 22 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-42
- makedumpfile: add support for ARMv8.2 LVA 52 bits

* Fri Dec 18 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-41
- Doc: improve mkdumprd man page

* Tue Dec 15 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-40
- Rework on dracut-module-setup.sh: Use systemctl call to replace ln_r

* Tue Dec 15 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-39
- dracut-module-setup.sh: Use systemctl call to replace ln_r

* Fri Dec 11 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-38
- Don's try to restart dracut-initqueue if it's already failed
- fadump-howto: update about 'nocma' and 'off' options for 'fadump=' parameter
- dracut-module-setup.sh: use auto6 for ipv6
- module-setup.sh: enable vlan on team interface
- Fix rootfs detection in dump_fs
- Remove RHEL-only patch: kexec-tools-2.0.18-makedumpfile-arm64-Add-support-for-ARMv8.2-LVA-52-bi.patch
- Rebase to makedumpfile-1.6.8 (step1)

* Fri Nov 13 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-37
- Doc: improve the usage documentation of the logger
- Update the kdump sysconfig
- Capitalize the configuration name of log level
- Add the rd.kdumploglvl option to control log level in the second kernel
- Appropriately converts logger numeric level to syslog log level
- Remove unused log levels for kdump logger
- Add sanity checks for the log levels
- Add code comments to help better understanding
- Doc: add a documentation for the usage of logger
- Improve debugging in the kdump kernel
- kdumpctl: add the '-d' option to enable the kexec loading debugging messages
- kdump.sysconfig: add the kdump logger configurations
- enable the logger for kdump
- introduce the kdump logger from the dracut

* Fri Nov  6 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-36
- arm64: Enable 'kexec_file_load' by default
- Fix, Add a kernel install hook to clean up kdump initramfs

* Fri Oct 30 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-35
- module-setup.sh: Instead of drop journalctl log, just don't read kmsg
- s390x: enable the kexec file load by default
- increase makdumpfile default message level to 7
- Rework check_config and warn on any duplicated option
- kdumpctl: Error out if path is set more than once.
- Don't drop journalctl content if failure action is "shell"
- dracut-module-install: Move systemd conf install code to a function
- kdump-lib.sh: Remove is_atomic
- Refactor kernel image and initrd detection code
- early-kdump: Use consistent symbol link for kernel and initramfs
- kdump-lib: strip grub device from kdump_bootdir
- kdumpctl: fix driver change detection on latest Fedora
- Revert "kdump-lib: disable efifb if hyperv_fb is in use"
- kdump-lib.sh: detect secure boot on s390
- Add a kernel install hook to clean up kdump initramfs

* Wed Aug 19 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-34
- kdump-lib: disable efifb if hyperv_fb is in use

* Tue Aug 18 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-33
- sadump, kaslr: fix failure of calculating kaslr_offset due to an sadump format restriction

* Mon Aug  3 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-32
- kdumpctl: exit if either pre.d or post.d is missing

* Wed Jul 22 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-31
- ppc64/kdump: use kexec_file_load when secureboot is enabled
- kdump_pre: make notes more precise
- dracut-kdump.sh: exit shell when machine reboot
- kdump.conf: fix a grammar issue
- kdumpctl: detect modification of scripts by its directory's timestamp
- module-setup.sh: suppress false alarm
- kexec-tools.spec: make the existence of pre.d and post.d mandatory

* Tue Jul 14 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-30
- x86_64: enable the kexec file load by default
- Revert "kdump-lib: switch to the kexec_file_load() syscall on x86_64 by default"

* Wed Jun 24 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-29
- mkdumprd: Improve the error message for umounted dump target

* Wed Jun 24 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-28
- mkdumprd: Fix nfs detection in to_mount
- Always wrap up call to dracut get_persistent_dev function
- man: improve description about /etc/kdump/{pre.d,post.d}interface

* Tue Jun 16 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-27
- kdump-lib: switch to the kexec_file_load() syscall on x86_64 by default

* Mon Jun 15 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-26
- Fix kdump failure when mount target specified by dracut_args
- mkdumprd: Fix dracut error on multiple extra_modules

* Mon Jun 15 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-25
- kdump.conf: Specify /etc/kdump/{pre.d,post.d}interface
- dracut-kdump.sh: Execute the binary and script filesin /etc/kdump/{pre.d,post.d}
- kdumpctl: Check the update of the binary and script files in /etc/kdump/{pre.d,post.d}
- dracut-module-setup.sh: Install files under /etc/kdump/{pre.d,post.d} into kdump initramfs

* Thu Jun 4 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-24
- fadump: update fadump-howto.txt with some more troubleshooting help

* Wed Jun 3 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-23
- fadump-howto.txt: source it in spec file

* Mon Jun 1 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-22
- mkdumprd: Use DUMP_TARGET which printing error message during ssh

* Mon Jun 1 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-21
- Don't inherit swiotlb parameter form 1st kernel by default
- Add a new option 'rd.znet_ifname' in order to use it in udev rules
- kdump.sysconfig: Remove the option 'log_buf_len' from kdump command line
- kdump-error-handler.service: Remove ExecStopPost
- module-setup.sh: Add "rd.neednet" parameter if network is needed

* Thu May 28 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-20
- Update docs for the new noauto dump target support
- kexec-kdump-howto.txt: Add some format to the document
- mkdumprd: generate usable kdump initramfs even target is not mounted
- Use get_mount_info to replace findmnt calls
- kdump-lib.sh: add fstab failback helper for getting mount info
- Allow calling mkdumprd from kdumpctl even if targat not mounted
- Add a is_mounted helper
- Introduce get_kdump_mntpoint_from_target and fix duplicated /
- Doc: Improves the early-kdump-howto.txt document in several points
- Doc: Add --force option to step 2 in early-kdump-howto.txt
- Doc: Fix typo in early-kdump-howto.txt
- Remove adjust_bind_mount_path call
- No longer treat atomic/silverblue specially
- mkdumprd: Simplify handling of user specified target
- mkdumprd: Use get_save_path instead of parsing config
- Remove is_dump_target_configured
- Always use get_save_path to get the 'path' option
- kdump-lib: Don't abuse echo, and clean up
- mkdumprd: Fix dracut args parsing
- mkdumprd: simplify dracut args parsing

* Thu May 21 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-19
- dracut-module-setup.sh: improve get_alias()
- fadump: update fadump-howto.txt with some troubleshooting help
- Append both nofail and x-systemd.before to kdump mount target
- Partially Revert "Don't mount the dump target unless needed"
- Don't unmount the dump target just after saving vmcore

* Mon May 11 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-18
- makedumpfile: Avoid false-positive failure in mem_seciton validation

* Tue Apr 21 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-17
- mkdumprd: Use makedumpfile --check-params option

* Thu Apr  9 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-16
- makedumpfile update to latest

* Wed Apr  1 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-15
- makedumpfile rebase to 1.6.7 

* Tue Feb 18 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-14
- kexec-tools/module-setup: Ensure eth devices get IP address for VLAN

* Wed Feb 12 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-13
- Add document to declare FCoE support

* Wed Feb 12 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-12
- powerpc: enable the scripts to capture dump on POWERNV platform

* Tue Feb  4 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-11
- s390: Use get_kaslr_offset_general() for s390x

* Fri Jan 10 2020 Pingfan Liu <piliu@redhat.com> - 2.0.20-10
- arm64: kdump: deal with a lot of resource entries in /proc/iomem
- arm64: kexec: allocate memory space avoiding reserved regions
- kexec: add variant helper functions for handling memory regions

* Thu Dec 12 2019 Pingfan Liu <piliu@redhat.com> - 2.0.20-9
- makedumpfile: assign bitmap1/2 fd for subprocess in non-cyclic mode

* Mon Dec  2 2019 Pingfan Liu <piliu@redhat.com> - 2.0.20-8
- makedumpfile: remove -lebl

* Thu Nov 28 2019 Pingfan Liu <piliu@redhat.com> - 2.0.20-7
- makedumpfile: Fix off-by-one issue in exclude_nodata_pages()

* Wed Nov 27 2019 Pingfan Liu <piliu@redhat.com> - 2.0.20-6
-rhel-8.2.0, origin/rhel-8.2.0) Increase SECTION_MAP_LAST_BIT to 4
- spec: move binaries from /sbin to /usr/sbin
- As /etc/kdump.conf timestamp is updated do not compare it when doing rpm --verify
- kdumpctl: make reload fail proof

* Tue Nov 12 2019 Pingfan Liu <piliu@redhat.com> - 2.0.20-5
- Don't execute final_action if failure_action terminates the system
- module-setup: re-fix 99kdumpbase network dependency
- kdumpctl: bail out immediately if host key verification failed
- kdumpctl: echo msg when waiting for connection
- kdumpctl: distinguish the failed reason of ssh
- kdumpctl: wait a while for network ready if dump target is ssh
- dracut-module-setup: filter out localhost for generic_fence_kdump
- dracut-module-setup: get localhost alias by manual

* Mon Oct 28 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-12.4
- dracut-module-setup.sh: Don't use squash module for fadump
- Don't mount the dump target unless needed
- dracut-module-setup: fix bond ifcfg processing
- Doc: amend the man page of kdump.conf

* Mon Oct 28 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-12.3
- Limit the size of vmcore-dmesg.txt to 2G
- makedumpfile: x86_64: Fix incorrect exclusion by -e option with KASLR
- mkdumprd: ensure ssh path exists before check size

* Fri Oct 18 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-12.2
- rebase to kexec-tools-2.0.20 and makedumpfile-1.6.6

* Fri Aug  9 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-12
- Don't forward and drop journalctl logs for fadump

* Mon Aug  5 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-11
- Drop switch root capability for non fadump initramfs

* Mon Aug  5 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-10
- Forward logs in kdump kernel to console directly

* Fri Jul 19 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-9
- kexec/arm64: Add support for handling zlib compressed (Image.gz) image
- kexec/kexec-zlib.h: Add 'is_zlib_file()' helper function
- kexec-uImage-arm64.c: Fix return value of uImage_arm64_probe()
- kexec/kexec.c: Add the missing close() for fd used for kexec_file_load()

* Sun Jul 14 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-8
- kdump.sysconfig/x86_64: Disable HEST by default

* Mon Jun 17 2019 Kairui Song <kasong@redhat.com> - 2.0.19-7
- dracut-kdump-capture.service: Use OnFailureJobMode instead of deprecated OnFailureIsolate

* Wed Jun 12 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-6
- kexec-kdump-howto.txt: Add notes about device dump
- Disable device dump by default

* Mon Jun 10 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-5
- kdumpctl: check for ssh path availability when rebuild
- kdumpctl: Check kdump.conf for error when rebuild is called
- makedumpfile: x86_64: Add support for AMD Secure Memory Encryption
- aarch64/kdump.sysconfig: Make config options similar to x86_64

* Mon May 27 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-4
- kexec-kdump-howto.txt: Add document about encrypted targets
- kexec-kdump-howto.txt: Add document about initramfs rebiuld
- kexec-kdump-howto: Add note on setting correct value of kptr_restrict
- doc: fix dead links in the file kexec-kdump-howto.txt
- earlykdump: provide a prompt message after the rebuilding of kdump initramfs.
- Get rid of duplicated strip_comments when reading config
- mkdumprd: Improve the config reading logic
- kdumpctl: don't always rebuild when extra_modules is set
- kdumpctl: follow symlink when checking for modified files
- fadump: leverage kernel support to re-regisgter FADump

* Wed May 15 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-3
- earlykdump: Add a note of final_action option to avoid crash loop
- Add final_action option to kdump.conf
- Add failure_action as alias of default and make default obsolete
- earlykdump: warn when installed kernel version differs from dracut target
- earlykdump: add more sanity check when generating initramfs
- fadump: use the original initrd to rebuild fadump initrdfrom

* Fri May 10 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-2
- kdumpctl: Detect block device driver change for initramfs rebuild
- Revert "kdumpctl: Rebuild initramfs if loaded kernel modules changed"
- mkdumprd: allow spaces after 'path' config phrase with network dump setting
- kexec.rules: create dedicated udev rules for ppc64
- Revert "rhel-only/kexec.rules: create dedicated udev rules for ppc64"
- rh-only makedumpfile/arm64: Add support for ARMv8.2-LVA (52-bit user-space VA support)

* Mon Apr 22 2019 Pingfan Liu <piliu@redhat.com> - 2.0.19-1
- kexec-tools: rebasing to 2.0.19
- makedumpfile: upgrade to 1.6.5
- kexec-tools: x86: Introduce a new option --reuse-video-type
- makedumpfile: exclude pages that are logically offline
- earlykdump: Fix failure when earlykdump is included by dracut
- Update man page for new kdumpctl command: reload / rebuild
- kdumpctl: add rebuild support
- rhel-only/kexec.rules: create dedicated udev rules for ppc64

* Mon Apr 15 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-30
- Enable building with hardening flags

* Fri Mar 15 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-29
- add gating

* Fri Feb 22 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-28

- makedumpfile/arm64: Add support for ARMv8.2-LVA (52-bit user-space VA support)
* Fri Feb  1 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-27
- Revert "kdumpctl, earlykdump: Don't use kexec_file_load when secure boot is enabled"
- mkdumprd: refine regex on dropping mount options

* Mon Jan 14 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-26
- earlykdump: fix kexec fails to load the early kdump kernel
- makedumpfile/x86_64: fix an unnecessary message with --mem-usage option

* Tue Jan  8 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-25
- dracut-module-setup: Don't build squashed image if required modules are missing

* Mon Jan  7 2019 Pingfan Liu <piliu@redhat.com> - 2.0.17-24
- makedumpfile/arm64: Fix 'info->page_offset' calculation for both KASLR and non-KASLR cases
- makedumpfile: Prepare paddr_to_vaddr() for arch-specific p2v conversion

* Sat Dec 29 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-23
- kdumpctl, earlykdump: Don't use kexec_file_load when secure boot is enabled

* Mon Dec 17 2018 Lianbo Jiang <lijiang@redhat.com> - 2.0.17-22
- mkdumprd: drop some nfs mount options when reading from kernel

* Fri Dec 14 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-21
- makedumpfile: Support newer kernels
- kdump-lib-initramfs.sh: using -force option when poweroff
- kexec-tools/vmcore-dmesg: fix infinite loop if log buffer wraps around
- makedumpfile: sadump: fix failure of reading 640 KB backup region if at over 4GB location
- Make udev reload rules quiet during bootup

* Thu Nov 22 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-20
- makedumpfile: Fix failure of detection of SPARSEMEM EXTREME in case of -x VMLINUX
- makedumpfile: ppc64: increase MAX_PHYSMEM_BITS to 128TB
- kdumpctl: Rebuild initramfs if loaded kernel modules changed

* Thu Nov 15 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-19
- Add aarch64 specific kdump.sysconfig and use 'nr_cpus' instead of 'maxcpus'
- Add missing usage info
- Throttle kdump reload request triggered by udev event
- Rewrite kdump's udev rules
- kdumpctl: Add reload support

* Tue Nov 6 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-18
- arm64: If 'getrandom' syscall fails, don't error out - just warn and proceed

* Mon Oct 29 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-17
- Update help text to indicate --mem-usage is supported on archs other than x86_64
- Fix 'makedumpfile --split' error ("Can't read the buffer of struct page") on x86_64

* Tue Oct 16 2018 Pingfan Liu <piliu@redhat.com> - 2.0.17-16
- dracut-module-setup: Enable dracut squash module
- dracut-module-setup: Fix DRM module inclusion test for hyper-v

* Sun Sep 30 2018 Pingfan Liu <piliu@redhat.com> 
- kdumpctl: add showmem cmd
- makedumpfile: fix makedumpfile Not tainted in 2nd kernel

* Thu Sep 20 2018 Kairui Song <kasong@redhat.com> - 2.0.17-14
- Add support to supply 'kaslr-seed' to secondary kernel
- kexec-tools.spec: Drop kexec-tools-2.0.3-disable-kexec-test.patch

* Mon Jul 30 2018 Florian Weimer <fweimer@redhat.com> - 2.0.17-9
- Rebuild with fixed binutils

* Sat Apr 28 2018 Dave Young <dyoung@redhat.com> - 2.0.17-1
- pull in makedumpfile 1.6.3 

* Sat Apr 28 2018 Dave Young <dyoung@redhat.com> - 2.0.17-1
- pull in 2.0.17

* Sun Apr 08 2018 Dave Young <dyoung@redhat.com> - 2.0.16-6
- kdump.sysconfig.ppc64(le): remove "root=" param from ppc64(le) 2nd kernel
- kdumpctl: Check the modification time of core_collector
- dracut-module-setup.sh: pass correct ip= param for ipv6

* Fri Feb 09 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 2.0.16-5
- Escape macros in %%changelog

* Wed Feb 7 2018 Dave Young <dyoung@redhat.com> - 2.0.16-4
- update anaconda addon migrate with Anaconda changes.

* Fri Dec 8 2017 Dave Young <dyoung@redhat.com> - 2.0.16-3
- workaround koji build failure (rhbz1520805)

* Mon Dec 4 2017 Dave Young <dyoung@redhat.com> - 2.0.16-2
- dracut-module-setup.sh: check whether to include multipath-hostonly or not
- Revert "kdumpctl: sanity check of nr_cpus for x86_64 in case running out of vectors"
- kdumpctl: skip selinux-relabel for dracut_args --mount dump target

* Tue Nov 21 2017 Dave Young <dyoung@redhat.com> - 2.0.16-1
- update to kexec-tools 2.0.16

* Thu Nov 9 2017 Dave Young <dyoung@redhat.com> - 2.0.15-15
- Use absolute path /usr/bin/dracut in mkdumprd

* Wed Oct 11 2017 Dave Young <dyoung@redhat.com> - 2.0.15-14
- kdumpctl: Error out in case there are white spaces before an option name

* Wed Sep 6 2017 Dave Young <dyoung@redhat.com> - 2.0.15-13
- dracut-module-setup.sh: eliminate redundant kdump_get_mac_addr call
- mkdumprd: use --quiet dracut argument to speedup initramfs build
- mkdumprd: fix patterns to modify mount options
- fadump: rebuild default initrd with dump capture capability
- module-setup: remove software iscsi cmdline generated by dracut
- kdumpctl: remove some cmdline inheritage from 1st kernel
- mkdumprd: apply dracut "--hostonly-cmdline" and "--no-hostonly-default-device"
- Change dump_to_rootfs to use "--mount" instead of "root=X"
- kdumpctl: move is_fadump_capable() to kdump-lib.sh
- Revert "kdumpctl: use generated rd.lvm.lv=X"
- Revert "mkdumprd: omit crypt when there is no crypt kdump target"
- Revert "mkdumprd: omit dracut modules in case of no dm target"
- Revert "mkdumprd: omit dracut modules in case of network dumping"
- update bogus date in rpm spec

* Thu Aug 17 2017 Dave Young <dyoung@redhat.com> - 2.0.15-12
- makedumpfile: fix 4.13 kernel larget vmcore bug
- Revert "Improve 'cpu add' udev rules"

* Tue Aug 15 2017 Dave Young <dyoung@redhat.com> - 2.0.15-11
- Own the /usr/share/makedumpfile dir
- Mark COPYING as %%license

* Tue Aug 8 2017 Dave Young <dyoung@redhat.com> - 2.0.15-10
- Improve 'cpu add' udev rules
- module-setup: suppress the early iscsi error messages
- mkdumprd: use 300s as the default systemd unit timeout for kdump mount 

* Mon Aug 7 2017 Dave Young <dyoung@redhat.com> - 2.0.15-9
- fix makedumpfile bug 1474706 

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.0.15-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Sun Jul 30 2017 Florian Weimer <fweimer@redhat.com> - 2.0.15-7
- Rebuild with binutils fix for ppc64le (#1475636)

* Fri Jul 28 2017 Dave Young <dyoung@redhat.com> - 2.0.15-6
- update upstream makedumpfile 1.6.2

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.0.15-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Wed Jul 19 2017 Dave Young <dyoung@redhat.com> - 2.0.15-4
- mkdumprd: remove useless "x-initrd.mount"
- kdumpctl: use "apicid" other than "initial apicid"

* Fri Jul 14 2017 Dave Young <dyoung@redhat.com> - 2.0.15-3
- module-setup: fix 99kdumpbase network dependency
- mkdumprd: omit dracut modules in case of network dumping
- mkdumprd: omit dracut modules in case of no dm target
- mkdumprd: omit crypt when there is no crypt kdump target
- kdumpctl: use generated rd.lvm.lv=X
- mkdumprd: change for_each_block_target() to use get_kdump_targets()
- kdump-lib.sh: introduce get_kdump_targets()
- kdump-lib.sh: fix improper get_block_dump_target()
- kdumpctl: fix infinite loop caused by running under bash

* Wed Jun 28 2017 Dave Young <dyoung@redhat.com> - 2.0.15-2
- enable makedumpfile for arm64

* Fri Jun 23 2017 Dave Young <dyoung@redhat.com> - 2.0.15-1
- rebase kexec-tools-2.0.15

* Thu Jun 15 2017 Dave Young <dyoung@redhat.com> - 2.0.14-13
- kexec-tools.spec: Fix whitespace errors
- dracut-module-setup: Fix test for inclusion of DRM modules
- kdump.conf.5: clarify the fence_kdump_nodes option

* Thu May 18 2017 Dave Young <dyoung@redhat.com> - 2.0.14-12
- kdumpctl: for fence_kdump, the ipaddr of this node should be excluded

* Fri May 12 2017 Dave Young <dyoung@redhat.com> - 2.0.14-11
- kdumpctl: change the shebang header to use /bin/bash
- kdumpctl: call strip_comments only when necessary to speedup
- Revert "kdumpctl: improve "while read" time for /etc/kdump.conf" (rhbz1449801)

* Fri May 5 2017 Dave Young <dyoung@redhat.com> - 2.0.14-10
- kdumpctl: improve "while read" time for /etc/kdump.conf
- kdumpctl: update check_dump_fs_modified() to use "lsinitrd -f"
- kdumpctl: improve check_wdt_modified()
- kdumpctl: remove is_mode_switched()
- kdumpctl: bail out earlier in case of no reserved memory

* Thu Apr 27 2017 Dave Young <dyoung@redhat.com> - 2.0.14-9
- kdump: Introduce 'force_no_rebuild' option
- kdump-lib-initramfs.sh: ignore the failure of echo
- kdump.sysconfig/x86_64: Add nokaslr to kdump kernel cmdline

* Tue Apr 11 2017 Dave Young <dyoung@redhat.com> - 2.0.14-8
- kdumpctl: fix status check when CONFIG_CRASH_DUMP is not enabled in kernel
- kdumpctl: fix a bug in remove_cmdline_param()
- kdumpctl: remove "root=X" for kdump boot
- Revert "kdumpctl: filter 'root' kernel parameter when running in live images"

* Fri Mar 31 2017 Dave Young <dyoung@redhat.com> - 2.0.14-7
- kdump-emergency: fix "Transaction is destructive" emergency failure
- mkdumprd: reduce lvm2 memory under kdump

* Fri Mar 17 2017 Dave Young <dyoung@redhat.com> - 2.0.14-6
- Fix kernel kaslr caused regressions (kexec -p and makedumpfile --mem-usage)

* Thu Mar 9 2017 Dave Young <dyoung@redhat.com> - 2.0.14-5
- kdump-lib.sh: fix incorrect usage with pipe as input for grep -q in is_pcs_fence_kdump()
- Document: fix incorrect link in fadump-how.txt

* Mon Jan 23 2017 Dave Young <dyoung@redhat.com> - 2.0.14-4
- drop kdump script rhcrashkernel-param in kexec-tools repo
- kdumpctl: sanity check of nr_cpus for x86_64 in case running out of vectors
- kdumpctl: change prepare_cmdline() to operate KDUMP_COMMANDLINE directly
- use --hostonly-i18n for dracut

* Wed Jan 4 2017 Dave Young <dyoung@redhat.com> - 2.0.14-3
- Rebase makedumpfile 1.6.1
- Delete unused patches

* Tue Dec 20 2016 Dave Young <dyoung@redhat.com> - 2.0.14-2
- rebase upstream kexec-tools 2.0.14
- update kdump anaconda addon
- cleanup sources file

* Mon Nov 28 2016 Dave Young <dyoung@redhat.com> - 2.0.14-1
- kexec-tools 2.0.14-1

* Mon Nov 28 2016 Dave Young <dyoung@redhat.com> - 2.0.13-9
- rename function kdump_to_udev_name
- Raw dump: use by-id as persistent policy in 2nd kernel
- drop dracut duplicate functions
- dracut-kdump: use POSIX shell syntax
- Correct two typos in kdumpctl and kdump.conf

* Fri Nov 11 2016 Dave Young <dyoung@redhat.com> - 2.0.13-8
- kexec/arch/i386: Add support for KASLR memory randomization
- Update kdump anaconda addon
- fadump: restore default initrd when fadump mode is disabled
- kdump/fadump: fix network interface name when switching from fadump to kdump
- kdumpctl: filter 'root' kernel parameter when running in live images
- Documentation: step by step guide on confiuring kdump in live images

* Thu Oct 27 2016 Dave Young <dyoung@redhat.com> - 2.0.13-7
- fix wrong page_offset added in 2.0.13-6

* Wed Oct 26 2016 Dave Young <dyoung@redhat.com> - 2.0.13-6
- add kexec support for arm64
- support x86 kaslr which is enabled by default in F25 kernel

* Fri Sep 16 2016 Dave Young <dyoung@redhat.com> - 2.0.13-5
- Fix bug 1373958 for system boot without initrd
- Do not depend on /etc/fstab in kdumpctl in case it does not exist

* Fri Aug 26 2016 Dave Young <dyoung@redhat.com> - 2.0.13-4
- Add special dump target "--mount" in dracut_args

* Tue Aug 9 2016 Dave Young <dyoung@redhat.com> - 2.0.13-3
- Fix armv7 build failure

* Tue Aug 9 2016 Dave Young <dyoung@redhat.com> - 2.0.13-2
- Drop old patches for 2.0.12

* Tue Aug 9 2016 Dave Young <dyoung@redhat.com> - 2.0.13-1
- Rebase kexec-tools 2.0.13

* Thu Jul 21 2016 Dave Young <dyoung@redhat.com> - 2.0.12-10
- kdump.conf manpage and kdump.conf comments fixes.
- kdump watchdog support.

* Wed Jul 13 2016 Dave Young <dyoung@redhat.com> - 2.0.12-9
- Update kdump anaconda addon
- makedumpfile: Support _count -> _refcount rename in struct page
- module-setup: Don't handle iBFT in kdump

* Wed Jul 6 2016 Dave Young <dyoung@redhat.com> - 2.0.12-8
- Rebase makedumpfile 1.6.0

* Mon Jun 27 2016 Dave Young <dyoung@redhat.com> - 2.0.12-7
- Fix date format in spec file.

* Mon Jun 27 2016 Dave Young <dyoung@redhat.com> - 2.0.12-6
- get_persistent_dev(): fix name contention with dracut's similar function

* Mon Jun 6 2016 Dave Young <dyoung@redhat.com> - 2.0.12-5
- kdump-lib: Add get_ifcfg_filename() to get the proper ifcfg file
- module-setup: Use get_ifcfg_filename() to get the proper ifcfg file

* Mon May 30 2016 Dave Young <dyoung@redhat.com> - 2.0.12-4
- update kdump anaconda addon to add mem range in tui 
- .gitignore: Update to make it more generic
- kdumpctl: check_rebuild improvement 
- kdumpctl: Do not rebuild initramfs when $KDUMP_BOOTDIR is read only

* Tue Mar 29 2016 Dave Young <dyoung@redhat.com> - 2.0.12-3
- update kdump anaconda addon to adapt to blivet-2.0 API

* Thu Mar 24 2016 Dave Young <dyoung@redhat.com> - 2.0.12-2
- Release 2.0.12-2
- ppc64le: fix kexec hang due to ppc64 elf abi breakage

* Tue Mar 22 2016 Dave Young <dyoung@redhat.com> - 2.0.12-1
- Rebase kexec-tools to 2.0.12 

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.0.11-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Fri Dec 11 2015 Dave Young <dyoung@redhat.com> - 2.0.11-3
- use "systemctl reboot -f" for reboot action
- Remove kernel param "quiet" from kdump kernel cmdline
- kdump.sysconfig: add KDUMP_COMMANDLINE_REMOVE
- Add missing prefixes in default sysconfig file
- fix bogus date in changelog

* Thu Nov 19 2015 Dave Young <dyoung@redhat.com> - 2.0.11-2
- Rebase to upstream makedumpfile 1.5.9 

* Mon Nov 9 2015 Dave Young <dyoung@redhat.com> - 2.0.11-1
- Rebase to upstream kexec-tools 2.0.11

* Mon Oct 19 2015 Dave Young <dyoung@redhat.com> - 2.0.10-9
- kexec-kdump-howto:Add introduction of parallel dumping
- Remove duplicate prefix path ${initdir}

* Tue Sep 8 2015 Dave Young <dyoung@redhat.com> - 2.0.10-8
- update kdump addon to fix a kickstart installationi issue 

* Wed Aug 19 2015 Dave Young <dyoung@redhat.com> - 2.0.10-7
- add man page for kdumpctl

* Thu Aug 13 2015 Baoquan He <bhe@redhat.com> - 2.0.10-6
- mkdumprd: Remove ifcfg from dracut's modules
- module-setup: Choose the first matched gateway in kdump_static_ip
- module-setup: Add permanent option to detect static ip address or not

* Tue Aug 4 2015 Dave Young <dyoung@redhat.com> - 2.0.10-5
- Update kdump addon to fix an installation hang issue.

* Tue Jul 28 2015 Dave Young <dyoung@redhat.com> - 2.0.10-4
- ipv6 support (except for link scope addresses)
- Apply the manual DNS to the 2nd kernel
- load iTCO_wdt early in cmdline hook

* Thu Jul 23 2015 Dave Young <dyoung@redhat.com> - 2.0.10-3
- Update kdump addon icon
- Revert static route corner case patches per bhe. He discussed with Marc
  it is just a corner case.

* Mon Jul 13 2015 Dave Young <dyoung@redhat.com> - 2.0.10-2
- update kdump addon icon

* Thu Jul 9 2015 Dave Young <dyoung@redhat.com> - 2.0.10-1
- Rebase kexec-tools 2.0.10
- Rebase eppic git tree 050615
- Enhance kdump.conf "default" parameters check

* Thu Jul 2 2015 Dave Young <dyoung@redhat.com> - 2.0.9-2
- Resolve bug 1236456, kexec load fail because koji add extra gcc flags.
- Remove -FPIC for makedumpfile since it is not necessary without harden build

* Tue Jun 23 2015 Dave Young <dyoung@redhat.com> - 2.0.9-1
- Rebase kexec-tools 2.0.9
- Rebase makedumpfile 1.5.8
- revert 6347630 since ipv6 patches has not been reviewed.

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.8-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Jun 11 2015 Dave Young <dyoung@redhat.com> -2.0.8-13
- Update kdump anaconda addon icon again.

* Wed Jun 10 2015 Dave Young <dyoung@redhat.com> -2.0.8-12
- Update kdump anaconda addon, change an icon.

* Wed Jun 03 2015 Baoquan He <bhe@redhat.com> -2.0.8-11
- make kdump work when kernel crash after shutdown
- Disable transparent hugepages in second kernel
- Filtered out "noauto" options in 2nd kernel fstab

* Tue Apr 21 2015 Baoquan He <bhe@redhat.com> -2.0.8-10
- add fPIC to makefumpfile CFLAGS to support hardening
- dracut-module-setup: Enhance kdump to support the bind mounted feature in Atomic
- Fix the warning if the target path is bind mount in Atomic
- Get the mount point correctly, if the device has several mount point
- kdump-lib: Add new function to judge the system is Atomic or not
- kdump-lib: Add the new function to enhance bind mounted judgement
- Remove duplicate slash in save path

* Thu Apr 09 2015 Baoquan He <bhe@redhat.com> -2.0.8-9
- Revert "execute kdump_post after do_default_action"
- dracut-module-setup.sh: change the insecure use of /tmp/*$$* filenames
- make kdump saving directory name consistent with RHEL6

* Sun Feb 15 2015 Dave Young <dyoung@redhat.com> - 2.0.8-8
- execute kdump_post after do_default_action
- update kdump anaconda addon (translations/help text issus)

* Fri Jan 30 2015 Baoquan He <bhe@redhat.com> - 2.0.8-7
- kdumpctl: adjust the boot dir if kernel is put in sub dir of /boot

* Tue Jan 13 2015 WANG Chao <chaowang@redhat.com> - 2.0.8-6
- mount fail if its mount point doesn't exist in /sysroot
- rebuild initrd dependency during kdump restart
- fix a dump path issue

* Tue Jan 06 2015 WANG Chao <chaowang@redhat.com> - 2.0.8-5
- remove panic_on_warn kernel param in 2nd kernel
- remove sysctl.conf to restore sysctl default values in 2nd kernel
- fix a core_collector issue in ssh and raw dump case
- update to kdump-anaconda-addon-005-2-g86366ae.tar.gz
- some cleanups

* Tue Nov 04 2014 WANG Chao <chaowang@redhat.com> - 2.0.8-4
- Fix ppc64le installation issue
- Fix get_option_value function

* Tue Oct 28 2014 WANG Chao <chaowang@redhat.com> - 2.0.8-3
- fix static route corner case
- fadump fix

* Tue Oct 21 2014 WANG Chao <chaowang@redhat.com> - 2.0.8-2
- Fix build issue on ARM

* Mon Oct 20 2014 WANG Chao <chaowang@redhat.com> - 2.0.8-1
- Rebase kexec-tools-2.0.8
- Remove subpackage kexec-tools-eppic
- Rebase kdump-anaconda-addon-005

* Fri Sep 26 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-11
- Fix build failure on ppc64le
- Fix an issue on iscsi boot environment

* Tue Sep 23 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-10
- Enable ppc64le arch.
- Rebase makedumpfile-1.5.7
- add sample eppic scripts to kexec-tools-eppic package
- Restart kdump service on cpu ADD/REMOVE events

* Wed Sep 10 2014 Baoquan He <bhe@redhat.com> - 2.0.7-9
- kdumpctl: Use kexec file based syscall for secureboot enabled machines
- kdumpctl: Use kexec file based mode to unload kdump kernel
- kdumpctl: Do not redirect error messages to /dev/null
- kexec: Provide an option to use new kexec system call

* Fri Aug 29 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-8
- use absolute path for executable in systemd service
- update to kdump-anaconda-addon-003
- remove dead kdump firstboot module and po files

* Thu Aug 21 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-7
- install 98-kexec.rules to /usr/lib/
- update kdump-anaconda-addon-0.2

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.7-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Wed Aug 06 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-5
- rework of kdump error handling
- add fadump support
- add static route support
- systemd will take care of shutdown and umount filesystems

* Thu Jul 24 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-4
- update to kdump-anaconda-addon-001-4-g03898ef.tar.gz
- prefix "kdump-" to eth name

* Mon Jul 21 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-3
- update to kdump-anaconda-addon-20140721.tar.gz

* Wed Jul 16 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-2
- Fix makedumpfile OOM issue

* Tue Jun 10 2014 WANG Chao <chaowang@redhat.com> - 2.0.7-1
- Rebase kexec-tools-2.0.7

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.6-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu May 22 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-8
- re-construct anaconda-addon file hierarchy

* Wed May 21 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-7
- fix a typo in kexec-tools.spec

* Tue May 20 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-6
- New package kdump-anaconda-addon
- fixes for udev event based service restart

* Wed Apr 30 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-5
- Remove nofail mount option
- Rebase makedumpfile-1.5.6

* Thu Apr 17 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-4
- generate kdump service dependencies on the fly
- kdump.conf: a standalone path directive becomes a relative path to it's backed disk.

* Wed Apr 02 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-3
- Add README to git repo
- Add fence_kdump support for generic clusters

* Thu Mar 27 2014 Peter Robinson <pbrobinson@fedoraproject.org> 2.0.6-2
- Exclude AArch64

* Wed Mar 26 2014 WANG Chao <chaowang@redhat.com> - 2.0.6-1
- Rebase kexec-tools-2.0.6
- fix an issue when dump path is mounted on nfs
- vmcore-dmesg: stack smashing fix
- get_ssh_size fix for localized df output

* Mon Mar 10 2014 WANG Chao <chaowang@redhat.com> - 2.0.5-2
- Warn about save vmcore patch mounted by another disk
- Omit dracut resume module

* Tue Mar 04 2014 WANG Chao <chaowang@redhat.com> - 2.0.5-1
- Rebase kexec-tools-2.0.5
- backport several patches from upstream for i386 build

* Mon Mar 03 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-25
- Pass disable_cpu_apicid to kexec of capture kernel
- Relax restriction of dumping on encrypted target
- regression fix on wdt kernel drivers instal

* Mon Feb 17 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-24
- add kdump-in-cluster-environment.txt to rpm pkg
- Secure Boot status check warning
- Some watchdog driver support

* Wed Jan 29 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-23
- ssh dump: create random-seed manually
- makedumpfile: memset() in cyclic bitmap initialization introduce segment fault.
- Add acpi_no_memhotplug to kdump kernel
- Add fence kdump support

* Tue Jan 28 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-22
- Rebase makedumpfile-1.5.5

* Wed Jan 22 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-21
- makedumpfile: Improve progress information for huge memory system
- s390: use nr_cpus=1 instead of maxcpus=1

* Fri Jan 17 2014 WANG Chao <chaowang@redhat.com> - 2.0.4-20
- vmcore-dmesg: fix timestamp error in vmcore-dmesg.txt
- makedumpfile: re-enable mmap() and introduce --non-mmap
- kdump.conf uncomment default core_collector line
- fix an issue when 'ssh' directive appearing in kdump.conf, the rest part of
  lines in this file are ignored

* Tue Dec 24 2013 WANG Chao <chaowang@redhat.com> - 2.0.4-18
- update translation files
- makedumpfile: default to lzo compression
- makedumpfile: add makedumpfile.conf.sample and its manpage

* Sat Dec 21 2013 Ville Skyttä <ville.skytta@iki.fi> - 2.0.4-15
- Fix Tamil (India) locale subdir name.
- Fix bogus date in %%changelog.

* Tue Dec 03 2013 WANG Chao <chaowang@redhat.com> - 2.0.4-14
- Add rd.memdebug in kdump module
- kdumpctl: Avoid leaking fd to subshell
- makedumpfile: Understand >= v3.11-rc4 dmesg
- makedumpfile, ppc: Support to filter dump for kernels that use CONFIG_SPARSEMEM_VMEMMAP.

* Fri Nov 15 2013 WANG Chao <chaowang@redhat.com> - 2.0.4-13
- makedumpfile: disable mmap()

* Tue Oct 29 2013 WANG Chao <chaowang@redhat.com> - 2.0.4-12
- fix sadump format phys_base calculating error
- kdump, x86: Process multiple Crash kernel in /proc/iomem
- makedumpfile: wrong cyclic buffer size recalculation causes bitmap data corruption
- Fix max_mapnr issue on system has over 44-bit addressing.

* Sat Oct 12 2013 Baoquan He <bhe@redhat.com> -2.0.4-11
- kdump-lib.sh: strip_comments is not implemented correcty

* Fri Sep 27 2013 Baoquan He <bhe@redhat.com> - 2.0.4-10
- Back port 2 revert commits
- kdump.sysconfig: default to "nofail" mount

* Fri Sep 27 2013 Baoquan He <bhe@redhat.com> - 2.0.4-9
- Strip inline comments from the kdump config file before use
- kdump-lib.sh: add common function strip_comments
- Introduce kdump-lib.sh for kdump shared functions
- kdump.service: Start kdump after network is online and remote fs is mounted
- dracut-module-setup: _dev to be a local variable
- kdumpctl: Run multiple kdumpctl instances one by one in serial order

* Wed Aug 21 2013 Baoquan He <bhe@redhat.com> - 2.0.4-8
- remove 98selinux dependency

* Fri Aug 2  2013 Baoquan He <bhe@redhat.com> - 2.0.4-7
- dracut-kdump.sh: add do_dump() and error out if dump vmcore fails
- dracut-module-setup.sh: setup correct system time and time zone in 2nd kernel.
- kernel cmdline: Remove hugepage allocations
- Use /lib/dracut/no-emergency-shell to control action on fail
- Revert: kdump.sysconfig: Add option action_on_fail and set its default as continue
- dracut-kdump.sh: Redirect kdump script stdout/stderr to /dev/console
- makedumpfile: Add vmap_area_list definition for ppc/ppc64.

* Fri Jul 12 2013 Baoquan He <bhe@redhat.com> - 2.0.4-6
- add snappy build
- add lzo build
- pull makedumpfile-1.5.4
- mkdumprd: check return value of subshell
- mkdumprd: get_persistent_dev() return original dev if no persistent dev exists.
- dracut-kdump.sh: Merge dump_to_rootfs() to dump_fs()
- dracut-kdump.sh: explicitly sync after each dump
- Correct wrong weekday of changelog
- kexec-tools.spec: Remove incorrect description in changelog

* Tue Jun 25 2013 Baoquan He <bhe@redhat.com> - 2.0.4-5
- monitor-dd-progress fix
- rawdump: only show dd progress bar when core_collector is not makedumpfile
- kexec-tools.spec: replaces scriptlets with new systemd macros
- dracut-kdump.sh: umount fs right before kdump exit
- dracut-kdump.sh: recursively umount fs and its submounts
- dracut-kdump.sh: cleanup - using local variable names instead of $1/$2 in functions
- dracut-kdump.sh: name the invalid vmcore to vmcore-incomplete
- dracut-kdump.sh: Output top level information about the kdump progress.
- kexec-kdump-howto: Add a section for debugging tips

* Tue Jun 18 2013 Baoquan He <bhe@redhat.com> - 2.0.4-4
- dracut-module-setup.sh: improve the approach to get a bridged interface list
- dracut-module-setup.sh: cleanup - use kdump_get_mac_addr() function
- dracut-module-setup.sh: use kernel exported mac address in kdump_get_mac_addr()
- dracut-module-setup.sh: use perm addr of slaves to setup bonding network
- kdump: Do not output debug messages by default
- dracut-module-setup.sh: kdump module depends on drm module
- mkdumprd: return error if no write permission on save path of server for ssh

* Thu Jun 13 2013 Baoquan He <bhe@redhat.com> - 2.0.4-3
- mkdumprd: remove -M option for dracut
- kdumpctl: add selinux relabel when service startup
- depends on dracut selinux module
- dracut-kdump.sh: umount rootfs after dump_to_rootfs
- kdump.sysconfig: append "panic=10" to kdump cmdline
- kexec-kdump-howto: grubby is suggested modifing kernel cmdline
- kexec-tools.spec: removes kexec udev rules for s390
- kdump.sysconfig: Add option action_on_fail and set its default as continue
- Add tab key as delimiter for core_collector in kdump.conf
- redirect stdout to stderr

* Tue May 14 2013 Baoquan He <bhe@redhat.com> - 2.0.4-2
- kdump: Save vmcore-dmesg.txt before saving vmcore
- Remove "ip=" overwrite to 40ip.conf
- Add support for bridge over bond/team/vlan.
- Fix bonding options syntax and get all specified options from ifcfg file.
- add dracut_args option to kdump.conf
- kexec-tools.spec: Add ethtool to dependency.
- error out if dump target is encrypted

* Wed Apr  3 2013 Baoquan He <bhe@redhat.com> - 2.0.4-1
- Delete several patches which have been merged into kexec-tools-2.0.4
- Revert: Release 2.0.3-72
- Release 2.0.3-72
- Pull kexec-tools-2.0.4
- Check if block device as dump target is resettable
- mkdumprd: add function perror_exit
- Deprecate blacklist option

* Wed Mar 27 2013 Baoquan He <bhe@redhat.com> - 2.0.3-71
- Remove eppic support on ppc and s390 arch

* Mon Mar 18 2013 Baoquan He <bhe@redhat.com> - 2.0.3-70
- Change rules related to eppic in kexec-tools.spec

* Thu Mar 14 2013 Baoquan He <bhe@redhat.com> - 2.0.3-69
- Support for eppic language as a subpackage
 
* Thu Mar 14 2013 Baoquan He <bhe@redhat.com> - 2.0.3-68
- tune sysconfig to save memory usage
- Remove useless codes related to LOGGER in kdumpctl
- kdumpctl:print out the service status
- Return to start() function when check_ssh_target failed
- use findmnt instead of blkid in mkdumprd
- check dump target mounting earlier
- kdumpctl: rename function name check_config
- add function to check kdump config file
- dracut-module-setup.sh: remove UUID/LABEL quotes before using it
- Change dump_to_rootfs to be a default option and reboot to be default action
- Remove "-F" in CORE_COLLECTOR when dump_to_rootfs

* Tue Feb 19 2013 Baoquan He <bhe@redhat.com> - 2.0.3-67
- Remove comma which is redundant
- Modify codes related to dump dir to make it clearer
- Rectify the get_host_ip implementation
- Revert: Merge an upstream patch for fix a ppc64 makedumpfile bug with with CONFIG_SPARSEMEM_EXTREME
- pull makedumpfile 1.5.3

* Tue Feb 5 2013 Dave Young <ruyang@redhat.com> - 2.0.3-66
- Spec: remove kdump image when a corresponding kernel is removed
- Merge an upstream patch for fix a ppc64 makedumpfile bug

* Mon Jan 28 2013 Dave Young <ruyang@redhat.com> - 2.0.3-65
- Add support for team devices
- Update translation file po/it.po
- remove wait for net ok function
- add bootdev cmdline param
- kdumpnic cmdline file name cleanup

* Fri Jan 4 2013 Dave Young <ruyang@redhat.com> - 2.0.3-64
- fix issue of exec on stack for ppc32

* Fri Dec 21 2012 Dave Young <ruyang@redhat.com> - 2.0.3-63
- revert explictly handling of PIPESTATUS
- enable pipefail bash option
- wrong ssh key fix
- build fix: Update 3 po files: po/gu.po po/or.po po/zh_CN.po

* Fri Dec 21 2012 Dave Young <ruyang@redhat.com> - 2.0.3-62
- Pull translated po files from zanata
- Optimize redundent code fetching server of network dump
- change the dump dir format to be more readable

* Wed Dec 12 2012 Dave Young <ruyang@redhat.com> - 2.0.3-61
- firstboot:fix reserve mem ui spinbox step size
- handle readonly mounted filesystem

* Mon Dec 10 2012 Dave Young <ruyang@redhat.com> - 2.0.3-60
- makedumpfile 1.5.1
- Update po tar.gz
- Add a notes for zanata process
- Add two xmls file for po zanata translation
- Cleanup and recreate po files

* Fri Nov 16 2012 Dave Young <ruyang@redhat.com> - 2.0.3-59
- Enable kdump service after installation
- get MEM_RESERVED from sysfs attribute
- get_ssh_size: use -n to redirect stdin from /dev/null
- add random feeding code for ssh dump
- kdump option space checking improvement
- kdumpctl: multi dump target checking fix

* Thu Oct 25 2012 Dave Young <ruyang@redhat.com> - 2.0.3-58
- pull in two upstream patches

* Thu Oct 11 2012 Dave Young <ruyang@redhat.com> - 2.0.3-57
- improve persistent name handling

* Sat Sep 29 2012 Dave Young <ruyang@redhat.com> - 2.0.3-56
- Pull vmcore-dmesg patches from vivek
- ppc/ppc64: compile purgatory with gcc option msoft-float
- Update to support f18 grub2 efi config file
- pass persistent name to dracut --device
- pass persistent name to dracut --mount
- use persistent name in kdump.conf of initramfs
- mkdumprd: add function get_persistent_dev
- remove useless uuid and label handling

* Thu Sep 06 2012 Dave Young <ruyang@redhat.com> - 2.0.3-55
- doc fix for mount dump target before mkdumprd
- pull makedumpfile 1.5.0

* Wed Aug 29 2012 Dave Young <ruyang@redhat.com> - 2.0.3-54
- pass raw device as dracut argument
- iscsi setup fix
- firstboot: add automatic and manual memory reservation for rhel
- firstboot: remove unnecessary underline shortkey
- firstboot: fix gtk warning about non-zero page size
- firstboot: update all kernels config in grubbyCmd
- firstboot: add actual reserved memory widget
- firstboot code cleanup
- rhcrashkernel-param: echo crashkernel=auto for rhel7
- Remove the kernel-kdump handling
- s390x firstboot fix
- remove elilo support
- grub2 fix in firstboot
- Take closing the reboot dialog as no
- Handle new crashkernel= syntax in firstboot
- Fix a localized string in firstboot
- Configure kdump in firstboot
- fix firstboot to ensure kdump svc is disabled properly
- firstboot text domain fix
- Update to use systemctl instead of sysv chkconfig
- port force_rebuild kdump.conf option
- Change return value to indicate the result of dump_raw() correctly.
- call dracut function for default shell

* Mon Jul 23 2012 Dave Young <ruyang@redhat.com> - 2.0.3-53
- refactor net option
- use fstab-sys to mount nfs
- rename function dump_localfs
- dump_localfs error path fix
- update kexec-kdump-howto.txt about systemctl commands
- ssh propagate alert message fix
- remove useless dracut cmdline '-c /dev/null'
- remove useless dracut cmdline for kernel-modules and kdumpbase
- install core_collector in module-setup.sh
- install extra_bins in module-setup.sh
- remove busybox dependency
- improve warning message of space checking
- do not mount root twice
- do not add fstab-sys module in dracut cmdline
- omit dash module
- network dns config fix
- shell exit value fix 

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.3-52
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Jul 5 2012 Dave Young <ruyang@redhat.com> - 2.0.3-51
- add s390x netdev setup
- Add s390x support
- Cleanup temp file leaved at /tmp/
- add check_size function for fs dump
- add ssh check_size
- blacklist patch apply fix
- Respect bonding mode
- Support dump over vlan tagged bonding

* Fri Jun 22 2012 Dave Young <ruyang@redhat.com> - 2.0.3-50
- add blacklist option, Resolves: bz805774
- Add kdump_post and kdump_pre support, Resolves: bz805773
- Port check_config from rhel6, Resolves: bz805778
- raw core_collector fix
- ssh core_collector fix
- drcut-kdump.sh: cleanup kdump.conf check

* Tue Jun 12 2012 Dave Young <ruyang@redhat.com> - 2.0.3-49
- cleanup DUMP_INSTRUCTION handling
- final reboot behavior fix
- dump_rootfs for default target fix
- add vlan support
- fix and refactor bond handling code
- fix and refactor bridge handling code
- core_collector doc basic fix
- omit plymouth module, Resolves: bz821997
- mkdumprd manpage cleanup manpage
- mkdumprd: remove --debug
- mkdumprd: remove noconf
- makedumprd: remove -d
- kdump.conf add sshkey
- kdump.conf remove disk_timeout
- kdump.conf make path uncommented
- kdump.conf.5 add default poweroff
- kdump.conf default shell fix
- kdump.conf default default action fix
- kdump.conf.5 remove module option
- kdump.conf remove kdump_pre/kdump_post
- kdump.conf: remove link_delay

* Mon May 28 2012 Dave Young <ruyang@redhat.com> - 2.0.3-48
- do_default_action cleanup, Resolves: bz805773
- add rhcrashkernel-param for anaconda use, Resolves: bz707441
- Basic iscsi target dump support (software initiator), Resolves bz822701
- Static ip configuratio support, Resolves: bz822739
- udev rules fix, Resolves: bz808817

* Thu May 3 2012 Dave Young <ruyang@redhat.com> - 2.0.3-47
- remove dracut-files.tgz2

* Wed May 2 2012 Dave Young <ruyang@redhat.com> - 2.0.3-46
- mkdumprd: Start using --hostonly and --add kdumpbase while calling dracut
- get_mp function cleanup
- move kdump script order to the end of pre pivot
- port raw dump from rhel6
- remove multi dump

* Mon Apr 23 2012 Dave Young <ruyang@redhat.com> - 2.0.3-45
- update dracut-files.tbz2

* Thu Apr 19 2012 Dave Young <dyoung@redhat.com> - 2.0.3-44
- update ppc64 sysconfig, resolve bug 811449
- deal with nic rename issue, resolve bug 810107
- update x86_64 sysconfig, resolve bug 813711

* Wed Apr 11 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.3-43
- variable name fix from Dave Young.

* Fri Mar 30 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.3-42
- get ip addr with getent
- spec: depends on dracut-network
- Handle net option for nfs in kdump.conf correctly

* Mon Feb 27 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.3-41
- Bump this version.

* Wed Feb 22 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-40
- Fixup sysytemd service file.

* Wed Feb 22 2012 Dave Young <ruyang@redhat.com> - 2.0.2-39
- Add ssh dump support, resolve bug 789253.

* Fri Jan 27 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-38
- Pull the latest makedumpfile release, 1.4.2.

* Fri Jan 27 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-37
- Add initial NFS dump support, experimental.

* Wed Jan 25 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-36
- Really upload the dracut module.

* Wed Jan 25 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-35
- Fix various bugs for nfs dump.

* Wed Jan 25 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-34
- kdump.sh cleanup for fstab handling, from Dave Young.

* Wed Jan 25 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-33
- Handle rootfs correctly.

* Tue Jan 10 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-32
- Fix add_dracut_arg in mkdumprd.

* Tue Jan 10 2012 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-31
- Update kdump dracut module with the latest dracut kdump branch.

* Fri Dec 16 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-30
- Update kdump dracut module to use the latest dracut feature.

* Fri Sep 9 2011 Tom Callaway <spot@fedoraproject.org> - 2.0.2-29
- fix systemd scriptlets

* Wed Sep 7 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-28
- Rename mkdumprd2 to mkdumpramfs.

* Wed Aug 31 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-27
- Add debug_mem_level debugging option, from Jan Stancek.
  Resolve Bug 731395.

* Mon Aug 15 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-26
- Fix several issues caused by the previous revert.

* Mon Aug 15 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-25
- Switch back to old mkdumprd and also keep the new one.

* Tue Aug 2 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-24
- Fix default action handling.

* Tue Aug 2 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-23
- Install modified kdump.conf in initrd.

* Tue Aug 2 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-22
- Handle lvm in pre-pivot hook.

* Tue Aug 2 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-21
- Fix udev rules in module-setup.sh

* Mon Aug 1 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-20
- Generate udev rules in module-setup.sh

* Mon Aug 1 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-19
- Generate udev rules to handle device names.

* Mon Aug 1 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-18
- Fix dump to local filesystem and raw dump.

* Mon Aug 1 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-17
- Depend on dracut-network.

* Mon Aug 1 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-16
- Move dracut module detection code to module-setup.sh.

* Thu Jul 28 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-15
- Use shutdown module of dracut to handle reboot/shutdown/halt.

* Wed Jul 27 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-14
- Wait for loginit.

* Wed Jul 27 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-13
- Use absolute path of reboot/halt/poweroff.

* Wed Jul 27 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-12
- Don't use consolehelper, use real reboot/halt/poweroff.

* Wed Jul 27 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-11
- Rename initrd to initramfs.

* Wed Jul 27 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-10
- Don't depend on busybox, as it doesn't save much space.

* Tue Jul 26 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-9
- Parse default action.

* Mon Jul 25 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-8
- Move path/core_collector/default parsing code to initrd.

* Mon Jul 25 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-7
- Remove obsolete code in kdumpctl.

* Mon Jul 25 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-6
- Support core_collector and extran_bins.

* Thu Jul 21 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-5
- Bypass '-d' option.

* Thu Jul 21 2011 Cong Wang <xiyou.wangcong@gmail.com> - 2.0.2-4
- Update initramfs infrastructure to make it working
  with dracut.

* Wed Jul 06 2011 Neil Horman <nhorman@redhat.com> - 2.0.2-3
- Removed sysv init script from package

* Mon Jul 04 2011 Neil Horman <nhorman@redhat.com> - 2.0.2-2
- Added systemd unit file (bz 716994)

* Fri Jun 24 2011 Neil Horman <nhorman@redhat.com> - 2.0.2-1
- Updated to upstream version 2.0.2

* Thu Jun 02 2011 Neil Horman <nhorman@redhat.com> - 2.0.0-47
- Fixed misuse of readlink command after directory change (bz 710744)

* Tue Apr 26 2011 Neil Horman <nhorman@redhat.com> - 2.0.0-46
- Fix some grammer in man page (bz 673817)

* Mon Mar 28 2011 Neil Horman <nhorman@redhat.com> - 2.0.0-45
- Fix misuse of basename in mkdumprd (bz 683769)

* Thu Mar 10 2011 Neil Horman <nhorman@redhat.com> - 2.0.0-44
- Fix build break in purgatory makefile

* Thu Mar 10 2011 Neil Horman <nhorman@redhat.com> - 2.0.0-43
- Remove vestigual emitdms code and call from mkdumprd

* Mon Feb 07 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.0-42
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Fri Oct 22 2010 Neil Horman <nhorman@redhat.com> - 2.0.0-41
- Fixed dhcp retry mechanism (bz 645734)

* Wed Sep 29 2010 jkeating - 2.0.0-40
- Rebuilt for gcc bug 634757

* Wed Sep 22 2010 Neil Horman <nhorman@redhat.com> - 2.0.0-39
- fix finding modalias/mkdumprd hang (bz 635893)

* Wed Aug 11 2010 David Malcolm <dmalcolm@redhat.com> - 2.0.0-38
- recompiling .py files against Python 2.7 (rhbz#623327)

* Sun Jun 13 2010 Lubomir Rintel <lkundrak@v3.sk> - 2.0.0-37
- Fix a syntax error in kdump init script

* Sun Jun 13 2010 Lubomir Rintel <lkundrak@v3.sk> - 2.0.0-36
- Cosmetic mkdumprd fixes (drop an unused function, streamline another)

* Sat May 29 2010 CAI Qian <caiqian@redhat.com> - 2.0.0-35
- Forward-port from F13
- Fixed kernel text area search in kcore (bz 587750)

* Sat May 29 2010 CAI Qian <caiqian@redhat.com> - 2.0.0-34
- Massive forward-port from RHEL6
- Update kexec-kdump-howto.txt
- Update docs to reflect use of ext4
- Update mkdumprd to pull in all modules needed
- Fix mkdumprd typo
- Removed universal add of ata_piix from mkdumprd
- Fix infinite loop from modprobe changes
- Fixed kexec-kdump-howto.doc for RHEL6
- Update makedumpfile to 1.3.5
- Improved mkdumprd run time
- Cai's fix for broken regex
- Fixing crashkernel syntax parsing
- Fix initscript to return proper LSB return codes
- Fixed bad call to resolve_dm_name
- Added poweroff option to mkdumprd
- Fixed readlink issue
- Fixed x86_64 page_offset specifictaion
- Fixed lvm setup loop to not hang
- Added utsname support to makedumpfile for 2.6.32
- Fix critical_disks list to exclude cciss/md
- Add help info for -b option
- Add ability to handle firmware hotplug events
- Update mkdumprd to deal with changes in busybox fsck
- Vitaly's fix to detect need for 64 bit elf
- Fix major/minor numbers on /dev/rtc
- Fix ssh id propogation w/ selinux
- Add blacklist feature to kdump.conf
- Removed rhpl code from firstboot
- Fixed firstboot enable sense
- Remove bogus debug comment from mkdumprd.
- Handle SPARSEMEM properly
- Fix scp monitoring script
- Fix firstboot to find grub on EFI systems
- Fixed mkdumprd to remove dup insmod
- Fixed kdump fsck pause
- Fixed kdump option handling
- fixed raid5 module detection

* Thu Mar 11 2010 Neil Horman <nhorman@redhat.com> - 2.0.0-33
- Remove nash references from mkdumprd

* Wed Feb 17 2010 Neil Horman <nhorman@redhat.com> - 2.0.0-32
- Fixed spec file error

* Wed Feb 17 2010 Neil Horman <nhorman@redhat.com> - 2.0.0-31
- Adding kdump.conf man page
- Adding disk timeout parameter (bz 566135)

* Tue Dec 01 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-30
- Fix raid support in mkdumprd (bz 519767)

* Mon Nov 23 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-29
- Updating firstboot script to RHEL-6 version (bz 539812)

* Fri Nov 06 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-28
- Added abrt infrastructure to kdump init script (bz 533370)

* Tue Sep 15 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-27
- Fixing permissions on dracut module files

* Fri Sep 11 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-26
- Rebuild for translation team (bz 522415)

* Thu Sep 10 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-25
- Fix dracut module check file (bz 522486)

* Thu Aug 13 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-24
- update kdump adv conf init script & dracut module

* Wed Jul 29 2009 Neil Horman <nhorman@redhat.com> - 2.0,0-23
- Remove mkdumprd2 and start replacement with dracut

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.0-22
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Jul 06 2009 Neil Horman <nhorman@redhat.com> 2.0.0-21
- Fixed build break

* Mon Jul 06 2009 Neil Horman <nhorman@redhat.com> 2.0.0-20
- Make makedumpfile a dynamic binary

* Mon Jul 06 2009 Neil Horman <nhorman@redhat.com> 2.0.0-19
- Fix build issue 

* Mon Jul 06 2009 Neil Horman <nhorman@redhat.com> 2.0.0-18
- Updated initscript to use mkdumprd2 if manifest is present
- Updated spec to require dash
- Updated sample manifest to point to correct initscript
- Updated populate_std_files helper to fix sh symlink

* Mon Jul 06 2009 Neil Horman <nhorman@redhat.com> 2.0.0-17
- Fixed mkdumprd2 tarball creation

* Tue Jun 23 2009 Neil Horman <nhorman@redhat.com> 2.0.0-16
- Fix up kdump so it works with latest firstboot

* Mon Jun 15 2009 Neil Horman <nhorman@redhat.com> 2.0.0-15
- Fixed some stat drive detect bugs by E. Biederman (bz505701)

* Wed May 20 2009 Neil Horman <nhorman@redhat.com> 2.0.0-14
- Put early copy of mkdumprd2 out in the wild (bz 466392)

* Fri May 08 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-13
- Update makedumpfile to v 1.3.3 (bz 499849)

* Tue Apr 07 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-12
- Simplifed rootfs mounting code in mkdumprd (bz 494416)

* Sun Apr 05 2009 Lubomir Rintel <lkundrak@v3.sk> - 2.0.0-11
- Install the correct configuration for i586

* Fri Apr 03 2009 Neil Horman <nhorman@redhat.com> - 2.0.0-10
- Fix problem with quoted CORE_COLLECTOR string (bz 493707)

* Thu Apr 02 2009 Orion Poplawski <orion@cora.nwra.com> - 2.0.0-9
- Add BR glibc-static

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.0-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Dec 04 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 2.0.0-7
- Rebuild for Python 2.6

* Mon Dec 01 2008 Neil Horman <nhorman@redhat.com> - 2.0.0.6
- adding makedumpfile man page updates (bz 473212)

* Mon Dec 01 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 2.0.0-5
- Rebuild for Python 2.6

* Wed Nov 05 2008 Neil Horman <nhorman@redhat.com> - 2.0.0-3
- Correct source file to use proper lang package (bz 335191)

* Wed Oct 29 2008 Neil Horman <nhorman@redhat.com> - 2.0.0-2
- Fix mkdumprd typo (bz 469001)

* Mon Sep 15 2008 Neil Horman <nhorman@redhat.com> - 2.0.0-2
- Fix sysconfig files to not specify --args-linux on x86 (bz 461615)

* Wed Aug 27 2008 Neil Horman <nhorman@redhat.com> - 2.0.0-1
- Update kexec-tools to latest upstream version

* Wed Aug 27 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-16
- Fix mkdumprd to properly use UUID/LABEL search (bz 455998)

* Tue Aug  5 2008 Tom "spot" Callaway <tcallawa@redhat.com> - 1.102pre-15
- fix license tag

* Mon Jul 28 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-14
- Add video reset section to docs (bz 456572)

* Fri Jul 11 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-13
- Fix mkdumprd to support dynamic busybox (bz 443878)

* Wed Jun 11 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-12
- Added lvm to bin list (bz 443878)

* Thu Jun 05 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-11
- Update to latest makedumpfile from upstream
- Mass import of RHEL fixes missing in rawhide

* Thu Apr 24 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-10
- Fix mkdumprd to properly pull in libs for lvm/mdadm (bz 443878)

* Wed Apr 16 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-9
- Fix cmdline length issue

* Tue Mar 25 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-8
- Fixing ARCH definition for bz 438661

* Mon Mar 24 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-7
- Adding patches for bz 438661

* Fri Feb 22 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-6
- Bringing rawhide up to date with bugfixes from RHEL5
- Adding patch to prevent kexec buffer overflow on ppc (bz 428684)

* Tue Feb 19 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-5
- Modifying mkdumprd to include dynamic executibles (bz 433350)

* Tue Feb 12 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-4
- bumping rev number for rebuild

* Wed Jan 02 2008 Neil Horman <nhorman@redhat.com> - 1.102pre-3
- Fix ARCH placement in kdump init script (bz 427201)
- Fix BuildRequires
- Fix Makedumpfile to build with new libelf

* Mon Oct 01 2007 Neil Horman <nhorman@redhat.com> - 1.102pre-2
- Fix triggerpostun script (bz 308151)

* Thu Aug 30 2007 Neil Horman <nhorman@redhat.com> - 1.102pre-1
- Bumping kexec version to latest horms tree (bz 257201)
- Adding trigger to remove initrds when a kernel is removed

* Wed Aug 22 2007 Neil Horman <nhorman@redhat.com> - 1.101-81
- Add xen-syms patch to makedumpfile (bz 250341)

* Wed Aug 22 2007 Neil Horman <nhorman@redhat.com> - 1.101-80
- Fix ability to determine space on nfs shares (bz 252170)

* Tue Aug 21 2007 Neil Horman <nhorman@redhat.com> - 1.101-79
- Update kdump.init to always create sparse files (bz 253714)

* Fri Aug 10 2007 Neil Horman <nhorman@redhat.com> - 1.101-78
- Update init script to handle xen kernel cmdlnes (bz 250803)

* Wed Aug 01 2007 Neil Horman <nhorman@redhat.com> - 1.101-77
- Update mkdumprd to suppres notifications /rev makedumpfile (bz 250341)

* Thu Jul 19 2007 Neil Horman <nhorman@redhat.com> - 1.101-76
- Fix mkdumprd to suppress informative messages (bz 248797)

* Wed Jul 18 2007 Neil Horman <nhorman@redhat.com> - 1.101-75
- Updated fr.po translations (bz 248287)

* Tue Jul 17 2007 Neil Horman <nhorman@redhat.com> - 1.101-74
- Fix up add_buff to retry locate_hole on segment overlap (bz 247989)

* Mon Jul 09 2007 Neil Horman <nhorman@redhat.com> - 1.101-73
- Fix up language files for kexec (bz 246508)

* Thu Jul 05 2007 Neil Horman <nhorman@redhat.com> - 1.101-72
- Fixing up initscript for LSB (bz 246967)

* Tue Jun 19 2007 Neil Horman <nhorman@redhat.com> - 1.101-71
- Fixed conflict in mkdumprd in use of /mnt (bz 222911)

* Mon Jun 18 2007 Neil Horman <nhorman@redhat.com> - 1.101-70
- Fixed kdump.init to properly read cmdline (bz 244649)

* Wed Apr 11 2007 Neil Horman <nhorman@redhat.com> - 1.101-69
- Fixed up kdump.init to enforce mode 600 on authorized_keys2 (bz 235986)

* Tue Apr 10 2007 Neil Horman <nhorman@redhat.com> - 1.101-68
- Fix alignment of bootargs and device-tree structures on ppc64

* Tue Apr 10 2007 Neil Horman <nhorman@redhat.com> - 1.101-67
- Allow ppc to boot ppc64 kernels (bz 235608)

* Tue Apr 10 2007 Neil Horman <nhorman@redhat.com> - 1.101-66
- Reduce rmo_top to 0x7c000000 for PS3 (bz 235030)

* Mon Mar 26 2007 Neil Horman <nhorman@redhat.com> - 1.101-65
- Fix spec to own kexec_tools directory (bz 219035)

* Wed Mar 21 2007 Neil Horman <nhorman@redhat.com> - 1.101-64
- Add fix for ppc memory region computation (bz 233312)

* Thu Mar 15 2007 Neil Horman <nhorman@redhat.com> - 1.101-63
- Adding extra check to avoid oom kills on nfs mount failure (bz 215056)

* Tue Mar 06 2007 Neil Horman <nhorman@redhat.com> - 1.101-62
- Updating makedumpfile to version 1.1.1 (bz 2223743)

* Thu Feb 22 2007 Neil Horman <nhorman@redhat.com> - 1.101-61
- Adding multilanguage infrastructure to firstboot_kdump (bz 223175)

* Mon Feb 12 2007 Neil Horman <nhorman@redhat.com> - 1.101-60
- Fixing up file permissions on kdump.conf (bz 228137)

* Fri Feb 09 2007 Neil Horman <nhorman@redhat.com> - 1.101-59
- Adding mkdumprd man page to build

* Thu Jan 25 2007 Neil Horman <nhorman@redhat.com> - 1.101-58
- Updating kdump.init and mkdumprd with most recent RHEL5 fixes
- Fixing BuildReq to require elfutils-devel-static

* Thu Jan 04 2007 Neil Horman <nhorman@redhat.com> - 1.101-56
- Fix option parsing problem for bzImage files (bz 221272)

* Fri Dec 15 2006 Neil Horman <nhorman@redhat.com> - 1.101-55
- Wholesale update of RHEL5 revisions 55-147

* Tue Aug 29 2006 Neil Horman <nhorman@redhat.com> - 1.101-54
- integrate default elf format patch

* Tue Aug 29 2006 Neil Horman <nhorman@redhat.com> - 1.101-53
- Taking Viveks x86_64 crashdump patch (rcv. via email)

* Tue Aug 29 2006 Neil Horman <nhorman@redhat.com> - 1.101-52
- Taking ia64 tools patch for bz 181358

* Mon Aug 28 2006 Neil Horman <nhorman@redhat.com> - 1.101-51
- more doc updates
- added patch to fix build break from kernel headers change

* Thu Aug 24 2006 Neil Horman <nhorman@redhat.com> - 1.101-50
- repo patch to enable support for relocatable kernels.

* Thu Aug 24 2006 Neil Horman <nhorman@redhat.com> - 1.101-49
- rewriting kcp to properly do ssh and scp
- updating mkdumprd to use new kcp syntax

* Wed Aug 23 2006 Neil Horman <nhorman@redhat.com> - 1.101-48
- Bumping revision number 

* Tue Aug 22 2006 Jarod Wilson <jwilson@redhat.com> - 1.101-47
- ppc64 no-more-platform fix

* Mon Aug 21 2006 Jarod Wilson <jwilson@redhat.com> - 1.101-46
- ppc64 fixups:
  - actually build ppc64 binaries (bug 203407)
  - correct usage output
  - avoid segfault in command-line parsing
- install kexec man page
- use regulation Fedora BuildRoot

* Fri Aug 18 2006 Neil Horman <nhorman@redhat.com> - 1.101-45
- fixed typo in mkdumprd for bz 202983
- fixed typo in mkdumprd for bz 203053
- clarified docs in kdump.conf with examples per bz 203015

* Tue Aug 15 2006 Neil Horman <nhorman@redhat.com> - 1.101-44
- updated init script to implement status function/scrub err messages
 
* Wed Aug 09 2006 Jarod Wilson <jwilson@redhat.com> - 1.101-43
- Misc spec cleanups and macro-ifications

* Wed Aug 09 2006 Jarod Wilson <jwilson@redhat.com> - 1.101-42
- Add %%dir /var/crash, so default kdump setup works

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-41
- fix another silly makefile error for makedumpfile 

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-40
- exclude makedumpfile from build on non-x86[_64] arches 

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-39
- exclude makedumpfile from build on non-x86[_64] arches 

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-38
- updating makedumpfile makefile to use pkg-config on glib-2.0

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-37
- updating makedumpfile makefile to use pkg-config

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-36
- Removing unneeded deps after Makefile fixup for makedumpfile

* Thu Aug 03 2006 Neil Horman <nhorman@redhat.com> - 1.101-35
- fixing up FC6/RHEL5 BuildRequires line to build in brew

* Wed Aug 02 2006 Neil Horman <nhorman@redhat.com> - 1.101-34
- enabling makedumpfile in build

* Wed Aug 02 2006 Neil Horman <nhorman@redhat.com> - 1.101-33
- added makedumpfile source to package

* Mon Jul 31 2006 Neil Horman <nhorman@redhat.com> - 1.101-32
- added et-dyn patch to allow loading of relocatable kernels

* Thu Jul 27 2006 Neil Horman <nhorman@redhat.com> - 1.101-30
- fixing up missing patch to kdump.init

* Wed Jul 19 2006 Neil Horman <nhorman@redhat.com> - 1.101-30
- add kexec frontend (bz 197695)

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 1.101-29
- rebuild

* Fri Jul 07 2006 Neil Horman <nhorman@redhat.com> 1.101-27.fc6
- Buildrequire zlib-devel

* Thu Jun 22 2006 Neil Horman <nhorman@redhat.com> -1.101-19
- Bumping rev number

* Thu Jun 22 2006 Neil Horman <nhorman@redhat.com> -1.101-17
- Add patch to allow ppc64 to ignore args-linux option

* Wed Mar 08 2006 Bill Nottingham <notting@redhat.com> - 1.101-16
- fix scriptlet - call chkconfig --add, change the default in the
  script itself (#183633)

* Wed Mar 08 2006 Thomas Graf <tgraf@redhat.com> - 1.101-15
- Don't add kdump service by default, let the user manually add it to
  avoid everyone seeing a warning.

* Tue Mar 07 2006 Thomas Graf <tgraf@redhat.com> - 1.101-14
- Fix kdump.init to call kexec from its new location

* Mon Mar  6 2006 Jeremy Katz <katzj@redhat.com> - 1.101-13
- proper requires for scriptlets

* Mon Mar 06 2006 Thomas Graf <tgraf@redhat.com> - 1.101-12
- Move kexec and kdump binaries to /sbin

* Thu Mar 02 2006 Thomas Graf <tgraf@redhat.com> - 1.101-11
- Fix argument order when stopping kexec

* Mon Feb 27 2006 Thomas Graf <tgraf@redhat.com> - 1.101-10
- kdump7.patch
   o Remove elf32 core headers support for x86_64
   o Fix x86 prepare elf core header routine
   o Fix ppc64 kexec -p failure for gcc 4.10
   o Fix few warnings for gcc 4.10
   o Add the missing --initrd option for ppc64
   o Fix ppc64 persistent root device bug
- Remove --elf32-core-headers from default configuration, users
  may re-add it via KEXEC_ARGS.
- Remove obsolete KEXEC_HEADERS
* Wed Feb 22 2006 Thomas Graf <tgraf@redhat.com> - 1.101-9
- Remove wrong quotes around --command-line in kdump.init

* Fri Feb 17 2006 Jeff Moyer <jmoyer@redhat.com> - 1.101-8
- Fix the service stop case.  It was previously unloading the wrong kernel.
- Implement the "restart" function.
- Add the "irqpoll" option as a default kdump kernel commandline parameter.
- Create a default kernel command line in the sysconfig file upon rpm install.

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 1.101-7.1.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Thu Feb 02 2006 Thomas Graf <tgraf@redhat.com> - 1.101-7.1
- Add patch to enable the kdump binary for x86_64
* Wed Feb 01 2006 Thomas Graf <tgraf@redhat.com>
- New kdump patch to support s390 arch + various fixes
- Include kdump in x86_64 builds
* Mon Jan 30 2006 Thomas Graf <tgraf@redhat.com>
- New kdump patch to support x86_64 userspace

* Fri Dec 16 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt for new gcj

* Wed Nov 16 2005 Thomas Graf <tgraf@redhat.com> - 1.101-5
- Report missing kdump kernel image as warning
 
* Thu Nov  3 2005 Jeff Moyer <jmoyer@redhat.com> - 1.101-4
- Build for x86_64 as well.  Kdump support doesn't work there, but users
  should be able to use kexec.

* Fri Sep 23 2005 Jeff Moyer <jmoyer@redhat.com> - 1.101-3
- Add a kdump sysconfig file and init script
- Spec file additions for pre/post install/uninstall

* Thu Aug 25 2005 Jeff Moyer <jmoyer@redhat.com>
- Initial prototype for RH/FC5
