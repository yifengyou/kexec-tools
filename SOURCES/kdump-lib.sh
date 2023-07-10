#!/bin/sh
#
# Kdump common variables and functions
#

DEFAULT_PATH="/var/crash/"
FENCE_KDUMP_CONFIG_FILE="/etc/sysconfig/fence_kdump"
FENCE_KDUMP_SEND="/usr/libexec/fence_kdump_send"
FADUMP_ENABLED_SYS_NODE="/sys/kernel/fadump_enabled"
LVM_CONF="/etc/lvm/lvm.conf"

is_fadump_capable()
{
    # Check if firmware-assisted dump is enabled
    # if no, fallback to kdump check
    if [ -f $FADUMP_ENABLED_SYS_NODE ]; then
        rc=`cat $FADUMP_ENABLED_SYS_NODE`
        [ $rc -eq 1 ] && return 0
    fi
    return 1
}

is_squash_available() {
    for kmodule in squashfs overlay loop; do
        if [ -z "$KDUMP_KERNELVER" ]; then
            modprobe --dry-run $kmodule &>/dev/null || return 1
        else
            modprobe -S $KDUMP_KERNELVER --dry-run $kmodule &>/dev/null || return 1
        fi
    done
}

perror_exit() {
    derror "$@"
    exit 1
}

is_ssh_dump_target()
{
    grep -q "^ssh[[:blank:]].*@" /etc/kdump.conf
}

is_nfs_dump_target()
{
    grep -q "^nfs" /etc/kdump.conf || \
        [[ $(get_dracut_args_fstype "$(grep "^dracut_args .*\-\-mount" /etc/kdump.conf)") = nfs* ]]
}

is_raw_dump_target()
{
    grep -q "^raw" /etc/kdump.conf
}

is_fs_type_nfs()
{
    local _fstype=$1
    [ $_fstype = "nfs" ] || [ $_fstype = "nfs4" ] && return 0
    return 1
}

is_fs_dump_target()
{
    egrep -q "^ext[234]|^xfs|^btrfs|^minix" /etc/kdump.conf
}

is_lvm2_thinp_device()
{
    _device_path=$1
    _lvm2_thin_device=$(lvm lvs -S 'lv_layout=sparse && lv_layout=thin' \
        --nosuffix --noheadings -o vg_name,lv_name "$_device_path" 2> /dev/null)

    [ -n "$_lvm2_thin_device" ]
}

strip_comments()
{
    echo $@ | sed -e 's/\(.*\)#.*/\1/'
}

# Read from kdump config file stripping all comments
read_strip_comments()
{
    # strip heading spaces, and print any content starting with
    # neither space or #, and strip everything after #
    sed -n -e "s/^\s*\([^# \t][^#]\+\).*/\1/gp" $1
}

# Check if fence kdump is configured in Pacemaker cluster
is_pcs_fence_kdump()
{
    # no pcs or fence_kdump_send executables installed?
    type -P pcs > /dev/null || return 1
    [ -x $FENCE_KDUMP_SEND ] || return 1

    # fence kdump not configured?
    (pcs cluster cib | grep 'type="fence_kdump"') &> /dev/null || return 1
}

# Check if fence_kdump is configured using kdump options
is_generic_fence_kdump()
{
    [ -x $FENCE_KDUMP_SEND ] || return 1

    grep -q "^fence_kdump_nodes" /etc/kdump.conf
}

to_dev_name() {
    local dev="${1//\"/}"

    case "$dev" in
    UUID=*)
        dev=`blkid -U "${dev#UUID=}"`
        ;;
    LABEL=*)
        dev=`blkid -L "${dev#LABEL=}"`
        ;;
    esac
    echo $dev
}

is_user_configured_dump_target()
{
    return $(is_mount_in_dracut_args || is_ssh_dump_target || is_nfs_dump_target || \
             is_raw_dump_target || is_fs_dump_target)
}

get_user_configured_dump_disk()
{
    local _target

    _target=$(egrep "^ext[234]|^xfs|^btrfs|^minix|^raw" /etc/kdump.conf 2>/dev/null |awk '{print $2}')
    [ -n "$_target" ] && echo $_target && return

    _target=$(get_dracut_args_target "$(grep "^dracut_args .*\-\-mount" /etc/kdump.conf)")
    [ -b "$_target" ] && echo $_target
}

get_root_fs_device()
{
    findmnt -k -f -n -o SOURCE /
}

get_save_path()
{
    local _save_path=$(awk '$1 == "path" {print $2}' /etc/kdump.conf)
    [ -z "$_save_path" ] && _save_path=$DEFAULT_PATH

    # strip the duplicated "/"
    echo $_save_path | tr -s /
}

get_block_dump_target()
{
    local _target _path

    if is_ssh_dump_target || is_nfs_dump_target; then
        return
    fi

    _target=$(get_user_configured_dump_disk)
    [ -n "$_target" ] && echo $(to_dev_name $_target) && return

    # Get block device name from local save path
    _path=$(get_save_path)
    _target=$(get_target_from_path $_path)
    [ -b "$_target" ] && echo $(to_dev_name $_target)
}

is_dump_to_rootfs()
{
    grep -E "^(failure_action|default)[[:space:]]dump_to_rootfs" /etc/kdump.conf >/dev/null
}

is_lvm2_thinp_dump_target()
{
    _target=$(get_block_dump_target)
    [ -n "$_target" ] && is_lvm2_thinp_device "$_target"
}

get_failure_action_target()
{
    local _target

    if is_dump_to_rootfs; then
        # Get rootfs device name
        _target=$(get_root_fs_device)
        [ -b "$_target" ] && echo $(to_dev_name $_target) && return
        # Then, must be nfs root
        echo "nfs"
    fi
}

# Get kdump targets(including root in case of dump_to_rootfs).
get_kdump_targets()
{
    local _target _root
    local kdump_targets

    _target=$(get_block_dump_target)
    if [ -n "$_target" ]; then
        kdump_targets=$_target
    elif is_ssh_dump_target; then
        kdump_targets="ssh"
    else
        kdump_targets="nfs"
    fi

    # Add the root device if dump_to_rootfs is specified.
    _root=$(get_failure_action_target)
    if [ -n "$_root" -a "$kdump_targets" != "$_root" ]; then
        kdump_targets="$kdump_targets $_root"
    fi

    echo "$kdump_targets"
}

# Return the bind mount source path, return the path itself if it's not bind mounted
# Eg. if /path/to/src is bind mounted to /mnt/bind, then:
# /mnt/bind -> /path/to/src, /mnt/bind/dump -> /path/to/src/dump
#
# findmnt uses the option "-v, --nofsroot" to exclusive the [/dir]
# in the SOURCE column for bind-mounts, then if $_mntpoint equals to
# $_mntpoint_nofsroot, the mountpoint is not bind mounted directory.
#
# Below is just an example for mount info
# /dev/mapper/atomicos-root[/ostree/deploy/rhel-atomic-host/var], if the
# directory is bind mounted. The former part represents the device path, rest
# part is the bind mounted directory which quotes by bracket "[]".
get_bind_mount_source()
{
    local _path=$1
    # In case it's a sub path in a mount point, get the mount point first
    local _mnt_top=$(df $_path | tail -1 | awk '{print $NF}')
    local _mntpoint=$(findmnt $_mnt_top | tail -n 1 | awk '{print $2}')
    local _mntpoint_nofsroot=$(findmnt -v $_mnt_top | tail -n 1 | awk '{print $2}')

    if [[ "$_mntpoint" = $_mntpoint_nofsroot ]]; then
        echo $_path && return
    fi

    _mntpoint=${_mntpoint#*$_mntpoint_nofsroot}
    _mntpoint=${_mntpoint#[}
    _mntpoint=${_mntpoint%]}
    _path=${_path#$_mnt_top}

    echo $_mntpoint$_path
}

# Return the current underlaying device of a path, ignore bind mounts
get_target_from_path()
{
    local _target

    _target=$(df $1 2>/dev/null | tail -1 |  awk '{print $1}')
    [[ "$_target" == "/dev/root" ]] && [[ ! -e /dev/root ]] && _target=$(get_root_fs_device)
    echo $_target
}

is_mounted()
{
    findmnt -k -n $1 &>/dev/null
}

get_mount_info()
{
    local _info_type=$1 _src_type=$2 _src=$3; shift 3
    local _info=$(findmnt -k -n -r -o $_info_type --$_src_type $_src $@)

    [ -z "$_info" ] && [ -e "/etc/fstab" ] && _info=$(findmnt -s -n -r -o $_info_type --$_src_type $_src $@)

    echo $_info
}

get_fs_type_from_target()
{
    get_mount_info FSTYPE source $1 -f
}

get_mntopt_from_target()
{
    get_mount_info OPTIONS source $1 -f
}
# Find the general mount point of a dump target, not the bind mount point
get_mntpoint_from_target()
{
    # Expcilitly specify --source to findmnt could ensure non-bind mount is returned
    get_mount_info TARGET source $1 -f
}

# Get the path where the target will be mounted in kdump kernel
# $1: kdump target device
get_kdump_mntpoint_from_target()
{
    local _mntpoint=$(get_mntpoint_from_target $1)

    # mount under /sysroot if dump to root disk or mount under
    # mount under /kdumproot if dump target is not mounted in first kernel
    # mount under /kdumproot/$_mntpoint in other cases in 2nd kernel.
    # systemd will be in charge to umount it.
    if [ -z "$_mntpoint" ];then
        _mntpoint="/kdumproot"
    else
        if [ "$_mntpoint" = "/" ];then
            _mntpoint="/sysroot"
        else
            _mntpoint="/kdumproot/$_mntpoint"
        fi
    fi

    # strip duplicated "/"
    echo $_mntpoint | tr -s "/"
}

# get_option_value <option_name>
# retrieves value of option defined in kdump.conf
get_option_value() {
    strip_comments `grep "^$1[[:space:]]\+" /etc/kdump.conf | tail -1 | cut -d\  -f2-`
}

kdump_get_persistent_dev() {
    local dev="${1//\"/}"

    case "$dev" in
    UUID=*)
        dev=`blkid -U "${dev#UUID=}"`
        ;;
    LABEL=*)
        dev=`blkid -L "${dev#LABEL=}"`
        ;;
    esac
    echo $(get_persistent_dev "$dev")
}

is_ostree()
{
    test -f /run/ostree-booted
}

# fixme, try the best to decide whether the ipv6 addr is allocated by slaac or dhcp6
is_ipv6_auto()
{
    local _netdev=$1
    local _auto=$(cat /proc/sys/net/ipv6/conf/$_netdev/autoconf)
    if [ $_auto -eq 1 ]; then
        return 0
    else
        return 1
    fi
}

is_ipv6_address()
{
    echo $1 | grep -q ":"
}

# get ip address or hostname from nfs/ssh config value
get_remote_host()
{
    local _config_val=$1

    # ipv6 address in kdump.conf is around with "[]",
    # factor out the ipv6 address
    _config_val=${_config_val#*@}
    _config_val=${_config_val%:/*}
    _config_val=${_config_val#[}
    _config_val=${_config_val%]}
    echo $_config_val
}

is_hostname()
{
    local _hostname=`echo $1 | grep ":"`

    if [ -n "$_hostname" ]; then
        return 1
    fi
    echo $1 | grep -q "[a-zA-Z]"
}

# Copied from "/etc/sysconfig/network-scripts/network-functions"
get_hwaddr()
{
    if [ -f "/sys/class/net/${1}/address" ]; then
        awk '{ print toupper($0) }' < /sys/class/net/${1}/address
    elif [ -d "/sys/class/net/${1}" ]; then
       LC_ALL= LANG= ip -o link show ${1} 2>/dev/null | \
            awk '{ print toupper(gensub(/.*link\/[^ ]* ([[:alnum:]:]*).*/,
                                        "\\1", 1)); }'
    fi
}

get_ifcfg_by_device()
{
    grep -E -i -l "^[[:space:]]*DEVICE=\"*${1}\"*[[:space:]]*$" \
         /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1
}

get_ifcfg_by_hwaddr()
{
    grep -E -i -l "^[[:space:]]*HWADDR=\"*${1}\"*[[:space:]]*$" \
         /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1
}

get_ifcfg_by_uuid()
{
    grep -E -i -l "^[[:space:]]*UUID=\"*${1}\"*[[:space:]]*$" \
         /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1
}

get_ifcfg_by_name()
{
    grep -E -i -l "^[[:space:]]*NAME=\"*${1}\"*[[:space:]]*$" \
         /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1
}

is_nm_running()
{
    [ "$(LANG=C nmcli -t --fields running general status 2>/dev/null)" = "running" ]
}

is_nm_handling()
{
    LANG=C nmcli -t --fields device,state  dev status 2>/dev/null \
          | grep -q "^\(${1}:connected\)\|\(${1}:connecting.*\)$"
}

# $1: netdev name
get_ifcfg_nmcli()
{
    local nm_uuid nm_name
    local ifcfg_file

    # Get the active nmcli config name of $1
    if is_nm_running && is_nm_handling "${1}" ; then
        # The configuration "uuid" and "name" generated by nm is wrote to
        # the ifcfg file as "UUID=<nm_uuid>" and "NAME=<nm_name>".
        nm_uuid=$(LANG=C nmcli -t --fields uuid,device c show --active 2>/dev/null \
                  | grep "${1}" | head -1 | cut -d':' -f1)
        nm_name=$(LANG=C nmcli -t --fields name,device c show --active 2>/dev/null \
                  | grep "${1}" | head -1 | cut -d':' -f1)
        ifcfg_file=$(get_ifcfg_by_uuid "${nm_uuid}")
        [ -z "${ifcfg_file}" ] && ifcfg_file=$(get_ifcfg_by_name "${nm_name}")
    fi

    echo -n "${ifcfg_file}"
}

# $1: netdev name
get_ifcfg_legacy()
{
    local ifcfg_file

    ifcfg_file="/etc/sysconfig/network-scripts/ifcfg-${1}"
    [ -f "${ifcfg_file}" ] && echo -n "${ifcfg_file}" && return

    ifcfg_file=$(get_ifcfg_by_name "${1}")
    [ -f "${ifcfg_file}" ] && echo -n "${ifcfg_file}" && return

    local hwaddr=$(get_hwaddr "${1}")
    if [ -n "$hwaddr" ]; then
        ifcfg_file=$(get_ifcfg_by_hwaddr "${hwaddr}")
        [ -f "${ifcfg_file}" ] && echo -n "${ifcfg_file}" && return
    fi

    ifcfg_file=$(get_ifcfg_by_device "${1}")

    echo -n "${ifcfg_file}"
}

# $1: netdev name
# Return the ifcfg file whole name(including the path) of $1 if any.
get_ifcfg_filename() {
    local ifcfg_file

    ifcfg_file=$(get_ifcfg_nmcli "${1}")
    if [ -z "${ifcfg_file}" ]; then
        ifcfg_file=$(get_ifcfg_legacy "${1}")
    fi

    echo -n "${ifcfg_file}"
}

# returns 0 when omission of a module is desired in dracut_args
# returns 1 otherwise
is_dracut_mod_omitted() {
    local dracut_args dracut_mod=$1

    set -- $(grep  "^dracut_args" /etc/kdump.conf)
    while [ $# -gt 0 ]; do
        case $1 in
            -o|--omit)
                [[ " ${2//[^[:alnum:]]/ } " ==  *" $dracut_mod "* ]] && return 0
        esac
        shift
    done

    return 1
}

is_wdt_active() {
    local active

    [ -d /sys/class/watchdog ] || return 1
    for dir in /sys/class/watchdog/*; do
        [ -f "$dir/state" ] || continue
        active=$(< "$dir/state")
        [ "$active" =  "active" ] && return 0
    done
    return 1
}

# If "dracut_args" contains "--mount" information, use it
# directly without any check(users are expected to ensure
# its correctness).
is_mount_in_dracut_args()
{
    grep -q "^dracut_args .*\-\-mount" /etc/kdump.conf
}

# If $1 contains dracut_args "--mount", return <filesystem type>
get_dracut_args_fstype()
{
    echo $1 | grep "\-\-mount" | sed "s/.*--mount .\(.*\)/\1/" | cut -d' ' -f3
}

# If $1 contains dracut_args "--mount", return <device>
get_dracut_args_target()
{
    echo $1 | grep "\-\-mount" | sed "s/.*--mount .\(.*\)/\1/" | cut -d' ' -f1
}

check_crash_mem_reserved()
{
    local mem_reserved

    mem_reserved=$(cat /sys/kernel/kexec_crash_size)
    if [ $mem_reserved -eq 0 ]; then
        derror "No memory reserved for crash kernel"
        return 1
    fi

    return 0
}

check_kdump_feasibility()
{
    if [ ! -e /sys/kernel/kexec_crash_loaded ]; then
        derror "Kdump is not supported on this kernel"
        return 1
    fi
    check_crash_mem_reserved
    return $?
}

check_current_kdump_status()
{
    if [ ! -f /sys/kernel/kexec_crash_loaded ];then
        derror "Perhaps CONFIG_CRASH_DUMP is not enabled in kernel"
        return 1
    fi

    rc=`cat /sys/kernel/kexec_crash_loaded`
    if [ $rc == 1 ]; then
        return 0
    else
        return 1
    fi
}

# remove_cmdline_param <kernel cmdline> <param1> [<param2>] ... [<paramN>]
# Remove a list of kernel parameters from a given kernel cmdline and print the result.
# For each "arg" in the removing params list, "arg" and "arg=xxx" will be removed if exists.
remove_cmdline_param()
{
    local cmdline=$1
    shift

    for arg in $@; do
        cmdline=`echo $cmdline | \
                 sed -e "s/\b$arg=[^ ]*//g" \
                 -e "s/^$arg\b//g" \
                 -e "s/[[:space:]]$arg\b//g" \
                 -e "s/\s\+/ /g"`
    done
    echo $cmdline
}

#
# This function returns the "apicid" of the boot
# cpu (cpu 0) if present.
#
get_bootcpu_apicid()
{
    awk '                                                       \
        BEGIN { CPU = "-1"; }                                   \
        $1=="processor" && $2==":"      { CPU = $NF; }          \
        CPU=="0" && /^apicid/           { print $NF; }          \
        '                                                       \
        /proc/cpuinfo
}

#
# append_cmdline <kernel cmdline> <parameter name> <parameter value>
# This function appends argument "$2=$3" to string ($1) if not already present.
#
append_cmdline()
{
    local cmdline=$1
    local newstr=${cmdline/$2/""}

    # unchanged str implies argument wasn't there
    if [ "$cmdline" == "$newstr" ]; then
        cmdline="${cmdline} ${2}=${3}"
    fi

    echo $cmdline
}

# This function check iomem and determines if we have more than
# 4GB of ram available. Returns 1 if we do, 0 if we dont
need_64bit_headers()
{
    return `tail -n 1 /proc/iomem | awk '{ split ($1, r, "-"); \
    print (strtonum("0x" r[2]) > strtonum("0xffffffff")); }'`
}

# Check if secure boot is being enforced.
#
# Per Peter Jones, we need check efivar SecureBoot-$(the UUID) and
# SetupMode-$(the UUID), they are both 5 bytes binary data. The first four
# bytes are the attributes associated with the variable and can safely be
# ignored, the last bytes are one-byte true-or-false variables. If SecureBoot
# is 1 and SetupMode is 0, then secure boot is being enforced.
#
# Assume efivars is mounted at /sys/firmware/efi/efivars.
is_secure_boot_enforced()
{
    local secure_boot_file setup_mode_file
    local secure_boot_byte setup_mode_byte

    # On powerpc, secure boot is enforced if:
    #   host secure boot: /ibm,secure-boot/os-secureboot-enforcing DT property exists
    #   guest secure boot: /ibm,secure-boot >= 2
    if [ -f /proc/device-tree/ibm,secureboot/os-secureboot-enforcing ]; then
		return 0
    fi
    if [ -f /proc/device-tree/ibm,secure-boot ] && \
       [ $(lsprop /proc/device-tree/ibm,secure-boot | tail -1) -ge 2 ]; then
		return 0
    fi

    # Detect secure boot on x86 and arm64
    secure_boot_file=$(find /sys/firmware/efi/efivars -name SecureBoot-* 2>/dev/null)
    setup_mode_file=$(find /sys/firmware/efi/efivars -name SetupMode-* 2>/dev/null)

    if [ -f "$secure_boot_file" ] && [ -f "$setup_mode_file" ]; then
        secure_boot_byte=$(hexdump -v -e '/1 "%d\ "' $secure_boot_file|cut -d' ' -f 5)
        setup_mode_byte=$(hexdump -v -e '/1 "%d\ "' $setup_mode_file|cut -d' ' -f 5)

        if [ "$secure_boot_byte" = "1" ] && [ "$setup_mode_byte" = "0" ]; then
            return 0
        fi
    fi

    # Detect secure boot on s390x
    if [[ -e "/sys/firmware/ipl/secure" && "$(cat /sys/firmware/ipl/secure)" == "1" ]]; then
        return 0
    fi

    return 1
}

#
# prepare_kexec_args <kexec args>
# This function prepares kexec argument.
#
prepare_kexec_args()
{
    local kexec_args=$1
    local found_elf_args

    ARCH=`uname -m`
    if [ "$ARCH" == "i686" -o "$ARCH" == "i386" ]
    then
        need_64bit_headers
        if [ $? == 1 ]
        then
            found_elf_args=`echo $kexec_args | grep elf32-core-headers`
            if [ -n "$found_elf_args" ]
            then
                dwarn "Warning: elf32-core-headers overrides correct elf64 setting"
            else
                kexec_args="$kexec_args --elf64-core-headers"
            fi
        else
            found_elf_args=`echo $kexec_args | grep elf64-core-headers`
            if [ -z "$found_elf_args" ]
            then
                kexec_args="$kexec_args --elf32-core-headers"
            fi
        fi
    fi
    echo $kexec_args
}

# prepare_kdump_kernel <kdump_kernelver>
# This function return kdump_kernel given a kernel version.
prepare_kdump_kernel()
{
    local kdump_kernelver=$1
    local dir img boot_dirlist boot_imglist kdump_kernel machine_id
    read -r machine_id < /etc/machine-id

    boot_dirlist=${KDUMP_BOOTDIR:-"/boot /boot/efi /efi /"}
    boot_imglist="$KDUMP_IMG-$kdump_kernelver$KDUMP_IMG_EXT $machine_id/$kdump_kernelver/$KDUMP_IMG"

    # The kernel of OSTree based systems is not in the standard locations.
    if is_ostree; then
        boot_dirlist="$(echo /boot/ostree/*) $boot_dirlist"
    fi

    # Use BOOT_IMAGE as reference if possible, strip the GRUB root device prefix in (hd0,gpt1) format
    boot_img="$(grep -P -o '^BOOT_IMAGE=(\S+)' /proc/cmdline | sed "s/^BOOT_IMAGE=\((\S*)\)\?\(\S*\)/\2/")"
    if [[ "$boot_img" == *"$kdump_kernelver" ]]; then
        boot_imglist="$boot_img $boot_imglist"
    fi

    for dir in $boot_dirlist; do
        for img in $boot_imglist; do
            if [[ -f "$dir/$img" ]]; then
                kdump_kernel=$(echo "$dir/$img" | tr -s '/')
                break 2
            fi
        done
    done
    echo "$kdump_kernel"
}

#
# Detect initrd and kernel location, results are stored in global enviromental variables:
# KDUMP_BOOTDIR, KDUMP_KERNELVER, KDUMP_KERNEL, DEFAULT_INITRD, and KDUMP_INITRD
#
# Expectes KDUMP_BOOTDIR, KDUMP_IMG, KDUMP_IMG_EXT, KDUMP_KERNELVER to be loaded from config already
# and will prefer already set values so user can specify custom kernel/initramfs location
#
prepare_kdump_bootinfo()
{
    local boot_initrdlist nondebug_kernelver debug_kernelver
    local default_initrd_base var_target_initrd_dir

    if [[ -z $KDUMP_KERNELVER ]]; then
        KDUMP_KERNELVER=$(uname -r)

        # Fadump uses the regular bootloader, unlike kdump. So, use the same version
        # for default kernel and capture kernel unless specified explicitly with
        # KDUMP_KERNELVER option.
        if ! is_fadump_capable; then
            nondebug_kernelver=$(sed -n -e 's/\(.*\)+debug$/\1/p' <<< "$KDUMP_KERNELVER")
        fi
    fi

    # Use nondebug kernel if possible, because debug kernel will consume more memory and may oom.
    if [[ -n $nondebug_kernelver ]]; then
        dinfo "Trying to use $nondebug_kernelver."
        debug_kernelver=$KDUMP_KERNELVER
        KDUMP_KERNELVER=$nondebug_kernelver
    fi

    KDUMP_KERNEL=$(prepare_kdump_kernel "$KDUMP_KERNELVER")

    if ! [[ -e $KDUMP_KERNEL ]]; then
        if [[ -n $debug_kernelver ]]; then
            dinfo "Fallback to using debug kernel"
            KDUMP_KERNELVER=$debug_kernelver
            KDUMP_KERNEL=$(prepare_kdump_kernel "$KDUMP_KERNELVER")
        fi
    fi

    if ! [[ -e $KDUMP_KERNEL ]]; then
        derror "Failed to detect kdump kernel location"
        return 1
    fi

    if [[ "$KDUMP_KERNEL" == *"+debug" ]]; then
        dwarn "Using debug kernel, you may need to set a larger crashkernel than the default value."
    fi

    # Set KDUMP_BOOTDIR to where kernel image is stored
    KDUMP_BOOTDIR=$(dirname "$KDUMP_KERNEL")

    # Default initrd should just stay aside of kernel image, try to find it in KDUMP_BOOTDIR
    boot_initrdlist="initramfs-$KDUMP_KERNELVER.img initrd"
    for initrd in $boot_initrdlist; do
        if [[ -f "$KDUMP_BOOTDIR/$initrd" ]]; then
            default_initrd_base="$initrd"
            DEFAULT_INITRD="$KDUMP_BOOTDIR/$default_initrd_base"
            break
        fi
    done

    # Create kdump initrd basename from default initrd basename
    # initramfs-5.7.9-200.fc32.x86_64.img => initramfs-5.7.9-200.fc32.x86_64kdump.img
    # initrd => initrdkdump
    if [[ -z $default_initrd_base ]]; then
        kdump_initrd_base=initramfs-${KDUMP_KERNELVER}kdump.img
    elif [[ $default_initrd_base == *.* ]]; then
        kdump_initrd_base=${default_initrd_base%.*}kdump.${DEFAULT_INITRD##*.}
    else
        kdump_initrd_base=${default_initrd_base}kdump
    fi

    # Place kdump initrd in $(/var/lib/kdump) if $(KDUMP_BOOTDIR) not writable
    if [[ ! -w $KDUMP_BOOTDIR ]]; then
        var_target_initrd_dir="/var/lib/kdump"
        mkdir -p "$var_target_initrd_dir"
        KDUMP_INITRD="$var_target_initrd_dir/$kdump_initrd_base"
    else
        KDUMP_INITRD="$KDUMP_BOOTDIR/$kdump_initrd_base"
    fi
}

get_watchdog_drvs()
{
    local _wdtdrvs _drv _dir

    for _dir in /sys/class/watchdog/*; do
        # device/modalias will return driver of this device
        [[ -f "$_dir/device/modalias" ]] || continue
        _drv=$(< "$_dir/device/modalias")
        _drv=$(modprobe --set-version "$KDUMP_KERNELVER" -R $_drv 2>/dev/null)
        for i in $_drv; do
            if ! [[ " $_wdtdrvs " == *" $i "* ]]; then
                _wdtdrvs="$_wdtdrvs $i"
            fi
        done
    done

    echo $_wdtdrvs
}

#
# prepare_cmdline <commandline> <commandline remove> <commandline append>
# This function performs a series of edits on the command line.
# Store the final result in global $KDUMP_COMMANDLINE.
prepare_cmdline()
{
    local cmdline id

    if [ -z "$1" ]; then
        cmdline=$(cat /proc/cmdline)
    else
        cmdline="$1"
    fi

    # These params should always be removed
    cmdline=$(remove_cmdline_param "$cmdline" crashkernel panic_on_warn)
    # These params can be removed configurably
    cmdline=$(remove_cmdline_param "$cmdline" "$2")

    # Always remove "root=X", as we now explicitly generate all kinds
    # of dump target mount information including root fs.
    #
    # We do this before KDUMP_COMMANDLINE_APPEND, if one really cares
    # about it(e.g. for debug purpose), then can pass "root=X" using
    # KDUMP_COMMANDLINE_APPEND.
    cmdline=$(remove_cmdline_param "$cmdline" root)

    # With the help of "--hostonly-cmdline", we can avoid some interitage.
    cmdline=$(remove_cmdline_param "$cmdline" rd.lvm.lv rd.luks.uuid rd.dm.uuid rd.md.uuid fcoe)

    # Remove netroot, rd.iscsi.initiator and iscsi_initiator since
    # we get duplicate entries for the same in case iscsi code adds
    # it as well.
    cmdline=$(remove_cmdline_param "$cmdline" netroot rd.iscsi.initiator iscsi_initiator)

    cmdline="${cmdline} $3"

    id=$(get_bootcpu_apicid)
    if [ ! -z ${id} ] ; then
        cmdline=$(append_cmdline "${cmdline}" disable_cpu_apicid ${id})
    fi

    # If any watchdog is used, set it's pretimeout to 0. pretimeout let
    # watchdog panic the kernel first, and reset the system after the
    # panic. If the system is already in kdump, panic is not helpful
    # and only increase the chance of watchdog failure.
    for i in $(get_watchdog_drvs); do
        cmdline+=" $i.pretimeout=0"

        if [[ $i == hpwdt ]]; then
            # hpwdt have a special parameter kdumptimeout, is's only suppose
            # to be set to non-zero in first kernel. In kdump, non-zero
            # value could prevent the watchdog from resetting the system.
            cmdline+=" $i.kdumptimeout=0"
        fi
    done

    echo ${cmdline}
}

#get system memory size in the unit of GB
get_system_size()
{
    result=$(cat /proc/iomem  | grep "System RAM" | awk -F ":" '{ print $1 }' | tr [:lower:] [:upper:] | paste -sd+)
    result="+$result"
    # replace '-' with '+0x' and '+' with '-0x'
    sum=$( echo $result | sed -e 's/-/K0x/g' | sed -e 's/+/-0x/g' | sed -e 's/K/+/g' )
    size=$(printf "%d\n" $(($sum)))

    # in MB unit
    let size=$size/1024/1024
    # since RHEL-8.5 kernel round up total memory to 128M, so should user space
    let size=($size+127)/128
    let size=$size*128
    # in GB unit
    let size=$size/1024

    echo $size
}

get_recommend_size()
{
    local mem_size=$1
    local _ck_cmdline=$2
    local OLDIFS="$IFS"

    last_sz=""
    last_unit=""

    start=${_ck_cmdline: :1}
    if [ $mem_size -lt $start ]; then
        echo "0M"
        return
    fi
    IFS=','
    for i in $_ck_cmdline; do
        end=$(echo $i | awk -F "-" '{ print $2 }' | awk -F ":" '{ print $1 }')
        recommend=$(echo $i | awk -F "-" '{ print $2 }' | awk -F ":" '{ print $2 }')
        size=${end: : -1}
        unit=${end: -1}
        if [ $unit == 'T' ]; then
            let size=$size*1024
        fi
        if [ $mem_size -lt $size ]; then
            echo $recommend
            IFS="$OLDIFS"
            return
        fi
    done
    IFS="$OLDIFS"
}

# return recommended size based on current system RAM size
kdump_get_arch_recommend_size()
{
    if ! [[ -r "/proc/iomem" ]] ; then
        echo "Error, can not access /proc/iomem."
        return 1
    fi
    arch=$(lscpu | grep Architecture | awk -F ":" '{ print $2 }' | tr [:lower:] [:upper:])

    if [ $arch == "X86_64" ] || [ $arch == "S390X" ]; then
        ck_cmdline="1G-4G:160M,4G-64G:192M,64G-1T:256M,1T-:512M"
    elif [ $arch == "AARCH64" ]; then
        ck_cmdline="2G-:448M"
    elif [ $arch == "PPC64LE" ]; then
        if is_fadump_capable; then
            ck_cmdline="4G-16G:768M,16G-64G:1G,64G-128G:2G,128G-1T:4G,1T-2T:6G,2T-4T:12G,4T-8T:20G,8T-16T:36G,16T-32T:64G,32T-64T:128G,64T-:180G"
        else
            ck_cmdline="2G-4G:384M,4G-16G:512M,16G-64G:1G,64G-128G:2G,128G-:4G"
        fi
    fi

    ck_cmdline=$(echo $ck_cmdline | sed -e 's/-:/-102400T:/g')
    sys_mem=$(get_system_size)
    result=$(get_recommend_size $sys_mem "$ck_cmdline")
    echo $result
    return 0
}

# Print all underlying crypt devices of a block device
# print nothing if device is not on top of a crypt device
# $1: the block device to be checked in maj:min format
get_luks_crypt_dev()
{
    local _type

    [[ -b /dev/block/$1 ]] || return 1

    _type=$(blkid -u filesystem,crypto -o export -- "/dev/block/$1" | \
            sed -n -E "s/^TYPE=(.*)$/\1/p")
    [[ $_type == "crypto_LUKS" ]] && echo $1

    for _x in /sys/dev/block/$1/slaves/*; do
        [[ -f $_x/dev ]] || continue
        [[ $_x/subsystem -ef /sys/class/block ]] || continue
        get_luks_crypt_dev "$(< "$_x/dev")"
    done
}

# kdump_get_maj_min <device>
# Prints the major and minor of a device node.
# Example:
# $ get_maj_min /dev/sda2
# 8:2
kdump_get_maj_min() {
    local _majmin
    _majmin="$(stat -L -c '%t:%T' "$1" 2> /dev/null)"
    printf "%s" "$((0x${_majmin%:*})):$((0x${_majmin#*:}))"
}

get_all_kdump_crypt_dev()
{
    local _dev _crypt

    for _dev in $(get_block_dump_target); do
        _crypt=$(get_luks_crypt_dev $(kdump_get_maj_min "$_dev"))
        [[ -n "$_crypt" ]] && echo $_crypt
    done
}

check_vmlinux()
{
    # Use readelf to check if it's a valid ELF
    readelf -h $1 &>/dev/null || return 1
}

get_vmlinux_size()
{
    local size=0

    while read _type _offset _virtaddr _physaddr _fsize _msize _flg _aln; do
        size=$(( $size + $_msize ))
    done <<< $(readelf -l -W $1 | grep "^  LOAD" 2>/dev/stderr)

    echo $size
}

try_decompress()
{
    # The obscure use of the "tr" filter is to work around older versions of
    # "grep" that report the byte offset of the line instead of the pattern.

    # Try to find the header ($1) and decompress from here
    for pos in `tr "$1\n$2" "\n$2=" < "$4" | grep -abo "^$2"`
    do
        if ! type -P $3 > /dev/null; then
            ddebug "Signiature detected but '$3' is missing, skip this decompressor"
            break
        fi

        pos=${pos%%:*}
        tail -c+$pos "$img" | $3 > $5 2> /dev/null
        if check_vmlinux $5; then
            ddebug "Kernel is extracted with '$3'"
            return 0
        fi
    done

    return 1
}

# Borrowed from linux/scripts/extract-vmlinux
get_kernel_size()
{
    # Prepare temp files:
    local img=$1 tmp=$(mktemp /tmp/vmlinux-XXX)
    trap "rm -f $tmp" 0

    # Try to check if it's a vmlinux already
    check_vmlinux $img && get_vmlinux_size $img && return 0

    # That didn't work, so retry after decompression.
    try_decompress '\037\213\010' xy    gunzip    $img $tmp || \
    try_decompress '\3757zXZ\000' abcde unxz      $img $tmp || \
    try_decompress 'BZh'          xy    bunzip2   $img $tmp || \
    try_decompress '\135\0\0\0'   xxx   unlzma    $img $tmp || \
    try_decompress '\211\114\132' xy    'lzop -d' $img $tmp || \
    try_decompress '\002!L\030'   xxx   'lz4 -d'  $img $tmp || \
    try_decompress '(\265/\375'   xxx   unzstd    $img $tmp

    # Finally check for uncompressed images or objects:
    [[ $? -eq 0 ]] && get_vmlinux_size $tmp && return 0

    # Fallback to use iomem
    local _size=0
    for _seg in $(cat /proc/iomem  | grep -E "Kernel (code|rodata|data|bss)" | cut -d ":" -f 1); do
	    _size=$(( $_size + 0x${_seg#*-} - 0x${_seg%-*} ))
    done
    echo $_size
}
