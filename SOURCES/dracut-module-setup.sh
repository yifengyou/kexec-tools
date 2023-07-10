#!/bin/bash

_save_kdump_netifs() {
    local _name

    if [[ -n $2 ]]; then
        _name=$2
    else
        _name=$1
    fi
    unique_netifs[$1]=$_name
}

_get_kdump_netifs() {
    echo -n "${!unique_netifs[@]}"
}

kdump_module_init() {
    if ! [[ -d "${initdir}/tmp" ]]; then
        mkdir -p "${initdir}/tmp"
    fi

    . /lib/kdump/kdump-lib.sh
}

check() {
    [[ $debug ]] && set -x
    #kdumpctl sets this explicitly
    if [ -z "$IN_KDUMP" ] || [ ! -f /etc/kdump.conf ]
    then
        return 1
    fi
    return 0
}

depends() {
    local _dep="base shutdown"

    kdump_module_init

    add_opt_module() {
        [[ " $omit_dracutmodules " != *\ $1\ * ]] && _dep="$_dep $1"
    }

    if is_squash_available; then
        add_opt_module squash
    else
        dwarning "Required modules to build a squashed kdump image is missing!"
    fi

    add_opt_module watchdog-modules
    if is_wdt_active; then
        add_opt_module watchdog
    fi

    if is_ssh_dump_target; then
        _dep="$_dep ssh-client"
    fi

    if is_lvm2_thinp_dump_target; then
        if grep -q lvmthinpool-monitor <<< $(dracut --list-modules); then
            add_opt_module lvmthinpool-monitor
        else
            dwarning "Required lvmthinpool-monitor modules is missing! Please upgrade dracut >= 057."
        fi
    fi

    if [ "$(uname -m)" = "s390x" ]; then
        _dep="$_dep znet"
    fi

    if [ -n "$( find /sys/devices -name drm )" ] || [ -d /sys/module/hyperv_fb ]; then
        add_opt_module drm
    fi

    if is_generic_fence_kdump || is_pcs_fence_kdump; then
        _dep="$_dep network"
    fi

    echo $_dep
}

kdump_is_bridge() {
     [ -d /sys/class/net/"$1"/bridge ]
}

kdump_is_bond() {
     [ -d /sys/class/net/"$1"/bonding ]
}

kdump_is_team() {
     [ -f /usr/bin/teamnl ] && teamnl $1 ports &> /dev/null
}

kdump_is_vlan() {
     [ -f /proc/net/vlan/"$1" ]
}

# $1: netdev name
source_ifcfg_file() {
    local ifcfg_file

    ifcfg_file=$(get_ifcfg_filename $1)
    if [ -f "${ifcfg_file}" ]; then
        . ${ifcfg_file}
    else
        dwarning "The ifcfg file of $1 is not found!"
    fi
}

# $1: netdev name
kdump_setup_dns() {
    local _nameserver _dns
    local _dnsfile=${initdir}/etc/cmdline.d/42dns.conf

    source_ifcfg_file $1

    [ -n "$DNS1" ] && echo "nameserver=$DNS1" > "$_dnsfile"
    [ -n "$DNS2" ] && echo "nameserver=$DNS2" >> "$_dnsfile"

    while read content;
    do
        _nameserver=$(echo $content | grep ^nameserver)
        [ -z "$_nameserver" ] && continue

        _dns=$(echo $_nameserver | cut -d' ' -f2)
        [ -z "$_dns" ] && continue

        if [ ! -f $_dnsfile ] || [ ! $(cat $_dnsfile | grep -q $_dns) ]; then
            echo "nameserver=$_dns" >> "$_dnsfile"
        fi
    done < "/etc/resolv.conf"
}

# $1: repeat times
# $2: string to be repeated
# $3: separator
repeatedly_join_str() {
    local _count="$1"
    local _str="$2"
    local _separator="$3"
    local i _res

    if [[ "$_count" -le 0 ]]; then
        echo -n ""
        return
    fi

    i=0
    _res="$_str"
    ((_count--))

    while [[ "$i" -lt "$_count" ]]; do
        ((i++))
        _res="${_res}${_separator}${_str}"
    done
    echo -n "$_res"
}

# $1: prefix
# $2: ipv6_flag="-6" indicates it's IPv6
# Given a prefix, calculate the netmask (equivalent of "ipcalc -m")
# by concatenating three parts,
#  1) the groups with all bits set 1
#  2) a group with partial bits set to 0
#  3) the groups with all bits set to 0
cal_netmask_by_prefix() {
    local _prefix="$1"
    local _ipv6_flag="$2" _ipv6
    local _bits_per_octet=8
    local _count _res _octets_per_group _octets_total _seperator _total_groups
    local _max_group_value _max_group_value_repr _bits_per_group _tmp _zero_bits

    if [[ "$_ipv6_flag" == "-6" ]]; then
        _ipv6=1
    else
        _ipv6=0
    fi

    if [[ "$_prefix" -lt 0  ||  "$_prefix" -gt 128 ]] || \
        ( ((!_ipv6)) && [[ "$_prefix" -gt 32 ]] ); then
        derror "Bad prefix:$_prefix for calculating netmask"
        exit 1
    fi

    if ((_ipv6)); then
        _octets_per_group=2
        _octets_total=16
        _seperator=":"
    else
        _octets_per_group=1
        _octets_total=4
        _seperator="."
    fi

    _total_groups=$((_octets_total/_octets_per_group))
    _bits_per_group=$((_octets_per_group * _bits_per_octet))
    _max_group_value=$(((1 << _bits_per_group) - 1))

    if ((_ipv6)); then
        _max_group_value_repr=$(printf "%x" $_max_group_value)
    else
        _max_group_value_repr="$_max_group_value"
    fi

    _count=$((_prefix/_octets_per_group/_bits_per_octet))
    _first_part=$(repeatedly_join_str "$_count" "$_max_group_value_repr" "$_seperator")
    _res="$_first_part"

    _tmp=$((_octets_total*_bits_per_octet-_prefix))
    _zero_bits=$(expr $_tmp % $_bits_per_group)
    if [[ "$_zero_bits" -ne 0 ]]; then
        _second_part=$((_max_group_value >> _zero_bits << _zero_bits))
        if ((_ipv6)); then
            _second_part=$(printf "%x" $_second_part)
        fi
        ((_count++))
        if [[ -z "$_first_part" ]]; then
            _res="$_second_part"
        else
            _res="${_first_part}${_seperator}${_second_part}"
        fi
    fi

    _count=$((_total_groups-_count))
    if [[ "$_count" -eq 0 ]]; then
        echo -n "$_res"
        return
    fi

    if ((_ipv6)) && [[ "$_count" -gt 1 ]] ; then
        # use condensed notion for IPv6
        _third_part=":"
    else
        _third_part=$(repeatedly_join_str "$_count" "0" "$_seperator")
    fi

    if [[ -z "$_res" ]] && ((!_ipv6)) ; then
        echo -n "${_third_part}"
    else
        echo -n "${_res}${_seperator}${_third_part}"
    fi
}

#$1: netdev name
#$2: srcaddr
#if it use static ip echo it, or echo null
kdump_static_ip() {
    local _netdev="$1" _srcaddr="$2" kdumpnic="$3" _ipv6_flag
    local _netmask _gateway _ipaddr _target _nexthop _prefix

    _ipaddr=$(ip addr show dev $_netdev permanent | awk "/ $_srcaddr\/.* /{print \$2}")

    if is_ipv6_address $_srcaddr; then
        _ipv6_flag="-6"
    fi

    if [ -n "$_ipaddr" ]; then
        _gateway=$(ip $_ipv6_flag route list dev $_netdev | \
                awk '/^default /{print $3}' | head -n 1)

        if [ "x" !=  "x"$_ipv6_flag ]; then
            # _ipaddr="2002::56ff:feb6:56d5/64", _netmask is the number after "/"
            _netmask=${_ipaddr#*\/}
            _srcaddr="[$_srcaddr]"
            _gateway="[$_gateway]"
        else
            _prefix=$(cut -d'/' -f2 <<< "$_ipaddr")
            _netmask=$(cal_netmask_by_prefix "$_prefix" "$_ipv6_flag")
            if [[ "$?" -ne 0 ]]; then
                derror "Failed to calculate netmask for $_ipaddr"
                exit 1
            fi
        fi
        echo -n "${_srcaddr}::${_gateway}:${_netmask}::"
    fi

    /sbin/ip $_ipv6_flag route show | grep -v default | grep ".*via.* $_netdev " |\
    while read _route; do
        _target=`echo $_route | cut -d ' ' -f1`
        _nexthop=`echo $_route | cut -d ' ' -f3`
        if [ "x" !=  "x"$_ipv6_flag ]; then
            _target="[$_target]"
            _nexthop="[$_nexthop]"
        fi
        echo "rd.route=$_target:$_nexthop:$kdumpnic"
    done >> ${initdir}/etc/cmdline.d/45route-static.conf
}

kdump_get_mac_addr() {
    cat /sys/class/net/$1/address
}

#Bonding or team master modifies the mac address
#of its slaves, we should use perm address
kdump_get_perm_addr() {
    local addr=$(ethtool -P $1 | sed -e 's/Permanent address: //')
    if [ -z "$addr" ] || [ "$addr" = "00:00:00:00:00:00" ]
    then
        derror "Can't get the permanent address of $1"
    else
        echo "$addr"
    fi
}

# Prefix kernel assigned names with "kdump-". EX: eth0 -> kdump-eth0
# Because kernel assigned names are not persistent between 1st and 2nd
# kernel. We could probably end up with eth0 being eth1, eth0 being
# eth1, and naming conflict happens.
kdump_setup_ifname() {
    local _ifname

    # If ifname already has 'kdump-' prefix, we must be switching from
    # fadump to kdump. Skip prefixing 'kdump-' in this case as adding
    # another prefix may truncate the ifname. Since an ifname with
    # 'kdump-' is already persistent, this should be fine.
    if [[ $1 =~ eth* ]] && [[ ! $1 =~ ^kdump-* ]]; then
        _ifname="kdump-$1"
    else
        _ifname="$1"
    fi

    echo "$_ifname"
}

kdump_install_nm_netif_allowlist() {
    local _netif _except_netif _netif_allowlist _netif_allowlist_nm_conf

    for _netif in $1; do
        _per_mac=$(kdump_get_perm_addr "$_netif")
        if [[ "$_per_mac" != 'not set' ]]; then
            _except_netif="mac:$_per_mac"
        else
            _except_netif="interface-name:${unique_netifs[${_netif}]}"
        fi
        _netif_allowlist="${_netif_allowlist}except:${_except_netif};"
    done

    _netif_allowlist_nm_conf=${initdir}/tmp/netif_allowlist_nm_conf
    cat << EOF > "$_netif_allowlist_nm_conf"
[device-others]
match-device=${_netif_allowlist}
managed=false
EOF

    inst "$_netif_allowlist_nm_conf" "/etc/NetworkManager/conf.d/10-kdump-netif_allowlist.conf"
    rm -f "$_netif_allowlist_nm_conf"
}

kdump_setup_bridge() {
    local _netdev=$1
    local _brif _dev _mac _kdumpdev
    for _dev in `ls /sys/class/net/$_netdev/brif/`; do
        _kdumpdev=""
        if kdump_is_bond "$_dev"; then
            kdump_setup_bond "$_dev"
        elif kdump_is_team "$_dev"; then
            kdump_setup_team "$_dev"
        elif kdump_is_vlan "$_dev"; then
            kdump_setup_vlan "$_dev"
        else
            _mac=$(kdump_get_mac_addr $_dev)
            _kdumpdev=$(kdump_setup_ifname $_dev)
            echo -n " ifname=$_kdumpdev:$_mac" >> ${initdir}/etc/cmdline.d/41bridge.conf
        fi
        _save_kdump_netifs "$_dev" "$_kdumpdev"
        [[ -z $_kdumpdev ]] && _kdumpdev=$_dev
        _brif+="$_kdumpdev,"
    done
    echo " bridge=$_netdev:$(echo $_brif | sed -e 's/,$//')" >> ${initdir}/etc/cmdline.d/41bridge.conf
}

kdump_setup_bond() {
    local _netdev=$1
    local _dev _mac _slaves _kdumpdev
    for _dev in `cat /sys/class/net/$_netdev/bonding/slaves`; do
        _mac=$(kdump_get_perm_addr $_dev)
        _kdumpdev=$(kdump_setup_ifname $_dev)
        _save_kdump_netifs "$_dev" "$_kdumpdev"
        echo -n " ifname=$_kdumpdev:$_mac" >> ${initdir}/etc/cmdline.d/42bond.conf
        _slaves+="$_kdumpdev,"
    done
    echo -n " bond=$_netdev:$(echo $_slaves | sed 's/,$//')" >> ${initdir}/etc/cmdline.d/42bond.conf
    # Get bond options specified in ifcfg

    source_ifcfg_file $_netdev

    bondoptions=":$(echo $BONDING_OPTS | xargs echo | tr " " ",")"
    echo "$bondoptions" >> ${initdir}/etc/cmdline.d/42bond.conf
}

kdump_setup_team() {
    local _netdev=$1
    local _dev _mac _slaves _kdumpdev
    for _dev in `teamnl $_netdev ports | awk -F':' '{print $2}'`; do
        _mac=$(kdump_get_perm_addr $_dev)
        _kdumpdev=$(kdump_setup_ifname $_dev)
        _save_kdump_netifs "$_dev" "$_kdumpdev"
        echo -n " ifname=$_kdumpdev:$_mac" >> ${initdir}/etc/cmdline.d/44team.conf
        _slaves+="$_kdumpdev,"
    done
    echo " team=$_netdev:$(echo $_slaves | sed -e 's/,$//')" >> ${initdir}/etc/cmdline.d/44team.conf
    #Buggy version teamdctl outputs to stderr!
    #Try to use the latest version of teamd.
    teamdctl "$_netdev" config dump > ${initdir}/tmp/$$-$_netdev.conf
    if [ $? -ne 0 ]
    then
        derror "teamdctl failed."
        exit 1
    fi
    inst_dir /etc/teamd
    inst_simple ${initdir}/tmp/$$-$_netdev.conf "/etc/teamd/$_netdev.conf"
    rm -f ${initdir}/tmp/$$-$_netdev.conf
}

kdump_setup_vlan() {
    local _netdev=$1
    local _phydev="$(awk '/^Device:/{print $2}' /proc/net/vlan/"$_netdev")"
    local _netmac="$(kdump_get_mac_addr $_phydev)"
    local _kdumpdev

    #Just support vlan over bond and team
    if kdump_is_bridge "$_phydev"; then
        derror "Vlan over bridge is not supported!"
        exit 1
    elif kdump_is_bond "$_phydev"; then
        kdump_setup_bond "$_phydev"
	echo " vlan=$(kdump_setup_ifname $_netdev):$_phydev" > ${initdir}/etc/cmdline.d/43vlan.conf
    else
        _kdumpdev="$(kdump_setup_ifname $_phydev)"
	echo " vlan=$(kdump_setup_ifname $_netdev):$_kdumpdev ifname=$_kdumpdev:$_netmac" > ${initdir}/etc/cmdline.d/43vlan.conf
    fi
    _save_kdump_netifs "$_phydev" "$_kdumpdev"
}

# find online znet device
# return ifname (_netdev)
# code reaped from the list_configured function of
# https://github.com/hreinecke/s390-tools/blob/master/zconf/znetconf
find_online_znet_device() {
	local CCWGROUPBUS_DEVICEDIR="/sys/bus/ccwgroup/devices"
	local NETWORK_DEVICES d ifname ONLINE

	[ ! -d "$CCWGROUPBUS_DEVICEDIR" ] && return
	NETWORK_DEVICES=$(find $CCWGROUPBUS_DEVICEDIR)
	for d in $NETWORK_DEVICES
	do
		[ ! -f "$d/online" ] && continue
		read ONLINE < $d/online
		if [ $ONLINE -ne 1 ]; then
			continue
		fi
		# determine interface name, if there (only for qeth and if
		# device is online)
		if [ -f $d/if_name ]
		then
			read ifname < $d/if_name
		elif [ -d $d/net ]
		then
			ifname=$(ls $d/net/)
		fi
		[ -n "$ifname" ] && break
	done
	echo -n "$ifname"
}

# setup s390 znet cmdline
# $1: netdev name
kdump_setup_znet() {
    local _options=""
    local _netdev=$1

    source_ifcfg_file $_netdev

    [[ -z "$NETTYPE" ]] && return
    [[ -z "$SUBCHANNELS" ]] && return

    for i in $OPTIONS; do
        _options=${_options},$i
    done
    echo rd.znet=${NETTYPE},${SUBCHANNELS}${_options} rd.znet_ifname=$(kdump_setup_ifname $_netdev):${SUBCHANNELS} > ${initdir}/etc/cmdline.d/30znet.conf
}

# Setup dracut to bringup a given network interface
kdump_setup_netdev() {
    local _netdev=$1 _srcaddr=$2
    local _static _proto _ip_conf _ip_opts _ifname_opts kdumpnic
    local _netmac=$(kdump_get_mac_addr $_netdev)
    local _znet_netdev

    kdumpnic=$(kdump_setup_ifname $_netdev)

    _znet_netdev=$(find_online_znet_device)
    if [[ -n "$_znet_netdev" ]]; then
        $(kdump_setup_znet "$_znet_netdev")
        if [[ $? != 0 ]]; then
            derror "Failed to set up znet"
            exit 1
        fi
    fi

    _static=$(kdump_static_ip $_netdev $_srcaddr $kdumpnic)
    if [ -n "$_static" ]; then
        _proto=none
    elif is_ipv6_address $_srcaddr; then
        _proto=auto6
    else
        _proto=dhcp
    fi

    _ip_conf="${initdir}/etc/cmdline.d/40ip.conf"
    _ip_opts=" ip=${_static}$kdumpnic:${_proto}"

    # dracut doesn't allow duplicated configuration for same NIC, even they're exactly the same.
    # so we have to avoid adding duplicates
    # We should also check /proc/cmdline for existing ip=xx arg.
    # For example, iscsi boot will specify ip=xxx arg in cmdline.
    if [ ! -f $_ip_conf ] || ! grep -q $_ip_opts $_ip_conf &&\
        ! grep -q "ip=[^[:space:]]*$_netdev" /proc/cmdline; then
        echo "$_ip_opts" >> $_ip_conf
    fi

    if kdump_is_bridge "$_netdev"; then
        kdump_setup_bridge "$_netdev"
    elif kdump_is_bond "$_netdev"; then
        kdump_setup_bond "$_netdev"
    elif kdump_is_team "$_netdev"; then
        kdump_setup_team "$_netdev"
    elif kdump_is_vlan "$_netdev"; then
        kdump_setup_vlan "$_netdev"
    else
        _ifname_opts=" ifname=$kdumpnic:$_netmac"
        echo "$_ifname_opts" >> $_ip_conf
    fi
    _save_kdump_netifs "$_netdev" "$_kdumpdev"

    kdump_setup_dns "$_netdev"

    if [ ! -f ${initdir}/etc/cmdline.d/50neednet.conf ]; then
        # network-manager module needs this parameter
        echo "rd.neednet" >> ${initdir}/etc/cmdline.d/50neednet.conf
    fi
}

get_ip_route_field()
{
    if `echo $1 | grep -q $2`; then
        echo ${1##*$2} | cut -d ' ' -f1
    fi
}

#Function:kdump_install_net
#$1: config values of net line in kdump.conf
#$2: srcaddr of network device
kdump_install_net() {
    local _server _netdev _srcaddr _route _serv_tmp
    local config_val="$1"

    _server=$(get_remote_host $config_val)

    if is_hostname $_server; then
        _serv_tmp=`getent ahosts $_server | grep -v : | head -n 1`
        if [ -z "$_serv_tmp" ]; then
            _serv_tmp=`getent ahosts $_server | head -n 1`
        fi
        _server=`echo $_serv_tmp | cut -d' ' -f1`
    fi

    _route=`/sbin/ip -o route get to $_server 2>&1`
    [ $? != 0 ] && echo "Bad kdump location: $config_val" && exit 1

    #the field in the ip output changes if we go to another subnet
    _srcaddr=$(get_ip_route_field "$_route" "src")
    _netdev=$(get_ip_route_field "$_route" "dev")

    kdump_setup_netdev "${_netdev}" "${_srcaddr}"

    #save netdev used for kdump as cmdline
    # Whoever calling kdump_install_net() is setting up the default gateway,
    # ie. bootdev/kdumpnic. So don't override the setting if calling
    # kdump_install_net() for another time. For example, after setting eth0 as
    # the default gate way for network dump, eth1 in the fence kdump path will
    # call kdump_install_net again and we don't want eth1 to be the default
    # gateway.
    if [ ! -f ${initdir}/etc/cmdline.d/60kdumpnic.conf ] &&
       [ ! -f ${initdir}/etc/cmdline.d/70bootdev.conf ]; then
        echo "kdumpnic=$(kdump_setup_ifname $_netdev)" > ${initdir}/etc/cmdline.d/60kdumpnic.conf
        echo "bootdev=$(kdump_setup_ifname $_netdev)" > ${initdir}/etc/cmdline.d/70bootdev.conf
    fi
}

# install etc/kdump/pre.d and /etc/kdump/post.d
kdump_install_pre_post_conf() {
    if [ -d /etc/kdump/pre.d ]; then
        for file in /etc/kdump/pre.d/*; do
            if [ -x "$file" ]; then
                dracut_install $file
            elif [ $file != "/etc/kdump/pre.d/*" ]; then
               echo "$file is not executable"
            fi
        done
    fi

    if [ -d /etc/kdump/post.d ]; then
        for file in /etc/kdump/post.d/*; do
            if [ -x "$file" ]; then
                dracut_install $file
            elif [ $file != "/etc/kdump/post.d/*" ]; then
                echo "$file is not executable"
            fi
        done
    fi
}

default_dump_target_install_conf()
{
    local _target _fstype
    local _mntpoint _save_path

    is_user_configured_dump_target && return

    _save_path=$(get_bind_mount_source $(get_save_path))
    _target=$(get_target_from_path $_save_path)
    _mntpoint=$(get_mntpoint_from_target $_target)

    _fstype=$(get_fs_type_from_target $_target)
    if is_fs_type_nfs $_fstype; then
        kdump_install_net "$_target"
        _fstype="nfs"
    else
        _target=$(kdump_get_persistent_dev $_target)
    fi

    echo "$_fstype $_target" >> ${initdir}/tmp/$$-kdump.conf

    # don't touch the path under root mount
    if [ "$_mntpoint" != "/" ]; then
        _save_path=${_save_path##"$_mntpoint"}
    fi

    #erase the old path line, then insert the parsed path
    sed -i "/^path/d" ${initdir}/tmp/$$-kdump.conf
    echo "path $_save_path" >> ${initdir}/tmp/$$-kdump.conf
}

#install kdump.conf and what user specifies in kdump.conf
kdump_install_conf() {
    local _opt _val _pdev
    sed -ne '/^#/!p' /etc/kdump.conf > ${initdir}/tmp/$$-kdump.conf

    while read _opt _val;
    do
        # remove inline comments after the end of a directive.
        case "$_opt" in
        raw)
            _pdev=$(persistent_policy="by-id" kdump_get_persistent_dev $_val)
            sed -i -e "s#^$_opt[[:space:]]\+$_val#$_opt $_pdev#" ${initdir}/tmp/$$-kdump.conf
            ;;
        ext[234]|xfs|btrfs|minix)
            _pdev=$(kdump_get_persistent_dev $_val)
            sed -i -e "s#^$_opt[[:space:]]\+$_val#$_opt $_pdev#" ${initdir}/tmp/$$-kdump.conf
            ;;
        ssh|nfs)
            kdump_install_net "$_val"
            ;;
        dracut_args)
            if [[ $(get_dracut_args_fstype "$_val") = nfs* ]] ; then
                kdump_install_net "$(get_dracut_args_target "$_val")"
            fi
            ;;
        kdump_pre|kdump_post|extra_bins)
            dracut_install $_val
            ;;
        core_collector)
            dracut_install "${_val%%[[:blank:]]*}"
            ;;
        esac
    done <<< "$(read_strip_comments /etc/kdump.conf)"

    kdump_install_pre_post_conf

    default_dump_target_install_conf

    kdump_configure_fence_kdump  "${initdir}/tmp/$$-kdump.conf"
    inst "${initdir}/tmp/$$-kdump.conf" "/etc/kdump.conf"
    rm -f ${initdir}/tmp/$$-kdump.conf
}

# Default sysctl parameters should suffice for kdump kernel.
# Remove custom configurations sysctl.conf & sysctl.d/*
remove_sysctl_conf() {

    # As custom configurations like vm.min_free_kbytes can lead
    # to OOM issues in kdump kernel, avoid them
    rm -f "${initdir}/etc/sysctl.conf"
    rm -rf "${initdir}/etc/sysctl.d"
    rm -rf "${initdir}/run/sysctl.d"
    rm -rf "${initdir}/usr/lib/sysctl.d"
}

kdump_iscsi_get_rec_val() {

    local result

    # The open-iscsi 742 release changed to using flat files in
    # /var/lib/iscsi.

    result=$(/sbin/iscsiadm --show -m session -r ${1} | grep "^${2} = ")
    result=${result##* = }
    echo $result
}

kdump_get_iscsi_initiator() {
    local _initiator
    local initiator_conf="/etc/iscsi/initiatorname.iscsi"

    [ -f "$initiator_conf" ] || return 1

    while read _initiator; do
        [ -z "${_initiator%%#*}" ] && continue # Skip comment lines

        case $_initiator in
            InitiatorName=*)
                initiator=${_initiator#InitiatorName=}
                echo "rd.iscsi.initiator=${initiator}"
                return 0;;
            *) ;;
        esac
    done < ${initiator_conf}

    return 1
}

# Figure out iBFT session according to session type
is_ibft() {
    [ "$(kdump_iscsi_get_rec_val $1 "node.discovery_type")" = fw ]
}

kdump_setup_iscsi_device() {
    local path=$1
    local tgt_name; local tgt_ipaddr;
    local username; local password; local userpwd_str;
    local username_in; local password_in; local userpwd_in_str;
    local netdev
    local srcaddr
    local idev
    local netroot_str ; local initiator_str;
    local netroot_conf="${initdir}/etc/cmdline.d/50iscsi.conf"
    local initiator_conf="/etc/iscsi/initiatorname.iscsi"

    dinfo "Found iscsi component $1"

    # Check once before getting explicit values, so we can bail out early,
    # e.g. in case of pure-hardware(all-offload) iscsi.
    if ! /sbin/iscsiadm -m session -r ${path} &>/dev/null ; then
        return 1
    fi

    if is_ibft ${path}; then
        return
    fi

    # Remove software iscsi cmdline generated by 95iscsi,
    # and let kdump regenerate here.
    rm -f ${initdir}/etc/cmdline.d/95iscsi.conf

    tgt_name=$(kdump_iscsi_get_rec_val ${path} "node.name")
    tgt_ipaddr=$(kdump_iscsi_get_rec_val ${path} "node.conn\[0\].address")

    # get and set username and password details
    username=$(kdump_iscsi_get_rec_val ${path} "node.session.auth.username")
    [ "$username" == "<empty>" ] && username=""
    password=$(kdump_iscsi_get_rec_val ${path} "node.session.auth.password")
    [ "$password" == "<empty>" ] && password=""
    username_in=$(kdump_iscsi_get_rec_val ${path} "node.session.auth.username_in")
    [ -n "$username" ] && userpwd_str="$username:$password"

    # get and set incoming username and password details
    [ "$username_in" == "<empty>" ] && username_in=""
    password_in=$(kdump_iscsi_get_rec_val ${path} "node.session.auth.password_in")
    [ "$password_in" == "<empty>" ] && password_in=""

    [ -n "$username_in" ] && userpwd_in_str=":$username_in:$password_in"

    netdev=$(/sbin/ip route get to ${tgt_ipaddr} | \
        sed 's|.*dev \(.*\).*|\1|g')
    srcaddr=$(echo $netdev | awk '{ print $3; exit }')
    netdev=$(echo $netdev | awk '{ print $1; exit }')

    kdump_setup_netdev $netdev $srcaddr

    # prepare netroot= command line
    # FIXME: Do we need to parse and set other parameters like protocol, port
    #        iscsi_iface_name, netdev_name, LUN etc.

    if is_ipv6_address $tgt_ipaddr; then
        tgt_ipaddr="[$tgt_ipaddr]"
    fi
    netroot_str="netroot=iscsi:${userpwd_str}${userpwd_in_str}@$tgt_ipaddr::::$tgt_name"

    [[ -f $netroot_conf ]] || touch $netroot_conf

    # If netroot target does not exist already, append.
    if ! grep -q $netroot_str $netroot_conf; then
         echo $netroot_str >> $netroot_conf
         dinfo "Appended $netroot_str to $netroot_conf"
    fi

    # Setup initator
    initiator_str=$(kdump_get_iscsi_initiator)
    [ $? -ne "0" ] && derror "Failed to get initiator name" && return 1

    # If initiator details do not exist already, append.
    if ! grep -q "$initiator_str" $netroot_conf; then
         echo "$initiator_str" >> $netroot_conf
         dinfo "Appended "$initiator_str" to $netroot_conf"
    fi
}

kdump_check_iscsi_targets () {
    # If our prerequisites are not met, fail anyways.
    type -P iscsistart >/dev/null || return 1

    kdump_check_setup_iscsi() {
        local _dev
        _dev=$1

        [[ -L /sys/dev/block/$_dev ]] || return
        cd "$(readlink -f /sys/dev/block/$_dev)"
        until [[ -d sys || -d iscsi_session ]]; do
            cd ..
        done
        [[ -d iscsi_session ]] && kdump_setup_iscsi_device "$PWD"
    }

    [[ $hostonly ]] || [[ $mount_needs ]] && {
        for_each_host_dev_and_slaves_all kdump_check_setup_iscsi
    }
}

# hostname -a is deprecated, do it by ourself
get_alias() {
    local ips
    local entries
    local alias_set

    ips=$(hostname -I)
    for ip in $ips
    do
            # in /etc/hosts, alias can come at the 2nd column
            entries=$(grep $ip /etc/hosts | awk '{ $1=""; print $0 }')
            if [ $? -eq 0 ]; then
                    alias_set="$alias_set $entries"
            fi
    done

    echo $alias_set
}

is_localhost() {
    local hostnames=$(hostname -A)
    local shortnames=$(hostname -A -s)
    local aliasname=$(get_alias)
    local nodename=$1

    hostnames="$hostnames $shortnames $aliasname"

    for name in ${hostnames}; do
        if [ "$name" == "$nodename" ]; then
            return 0
        fi
    done
    return 1
}

# retrieves fence_kdump nodes from Pacemaker cluster configuration
get_pcs_fence_kdump_nodes() {
    local nodes

    # get cluster nodes from cluster cib, get interface and ip address
    nodelist=`pcs cluster cib | xmllint --xpath "/cib/status/node_state/@uname" -`

    # nodelist is formed as 'uname="node1" uname="node2" ... uname="nodeX"'
    # we need to convert each to node1, node2 ... nodeX in each iteration
    for node in ${nodelist}; do
        # convert $node from 'uname="nodeX"' to 'nodeX'
        eval $node
        nodename=$uname
        # Skip its own node name
        if [ "$nodename" = `hostname` -o "$nodename" = `hostname -s` ]; then
            continue
        fi
        nodes="$nodes $nodename"
    done

    echo $nodes
}

# retrieves fence_kdump args from config file
get_pcs_fence_kdump_args() {
    if [ -f $FENCE_KDUMP_CONFIG_FILE ]; then
        . $FENCE_KDUMP_CONFIG_FILE
        echo $FENCE_KDUMP_OPTS
    fi
}

get_generic_fence_kdump_nodes() {
    local filtered
    local nodes

    nodes=$(get_option_value "fence_kdump_nodes")
    for node in ${nodes}; do
        # Skip its own node name
        if is_localhost $node; then
            continue
        fi
        filtered="$filtered $node"
    done
    echo $filtered
}

# setup fence_kdump in cluster
# setup proper network and install needed files
kdump_configure_fence_kdump () {
    local kdump_cfg_file=$1
    local nodes
    local args

    if is_generic_fence_kdump; then
        nodes=$(get_generic_fence_kdump_nodes)

    elif is_pcs_fence_kdump; then
        nodes=$(get_pcs_fence_kdump_nodes)

        # set appropriate options in kdump.conf
        echo "fence_kdump_nodes $nodes" >> ${kdump_cfg_file}

        args=$(get_pcs_fence_kdump_args)
        if [ -n "$args" ]; then
            echo "fence_kdump_args $args" >> ${kdump_cfg_file}
        fi

    else
        # fence_kdump not configured
        return 1
    fi

    # setup network for each node
    for node in ${nodes}; do
        kdump_install_net $node
    done

    dracut_install /etc/hosts
    dracut_install /etc/nsswitch.conf
    dracut_install $FENCE_KDUMP_SEND
}

# Install a random seed used to feed /dev/urandom
# By the time kdump service starts, /dev/uramdom is already fed by systemd
kdump_install_random_seed() {
    local poolsize=`cat /proc/sys/kernel/random/poolsize`

    if [ ! -d ${initdir}/var/lib/ ]; then
        mkdir -p ${initdir}/var/lib/
    fi

    dd if=/dev/urandom of=${initdir}/var/lib/random-seed \
       bs=$poolsize count=1 2> /dev/null
}

remove_cpu_online_rule() {
    local file=${initdir}/usr/lib/udev/rules.d/40-redhat.rules

    sed -i '/SUBSYSTEM=="cpu"/d' $file
}

kdump_install_systemd_conf() {
    local failure_action=$(get_option_value "failure_action")

    # Kdump turns out to require longer default systemd mount timeout
    # than 1st kernel(90s by default), we use default 300s for kdump.
    grep -r "^[[:space:]]*DefaultTimeoutStartSec=" ${initdir}/etc/systemd/system.conf* &>/dev/null
    if [ $? -ne 0 ]; then
        mkdir -p ${initdir}/etc/systemd/system.conf.d
        echo "[Manager]" > ${initdir}/etc/systemd/system.conf.d/kdump.conf
        echo "DefaultTimeoutStartSec=300s" >> ${initdir}/etc/systemd/system.conf.d/kdump.conf
    fi

    # Forward logs to console directly, and don't read Kmsg, this avoids
    # unneccessary memory consumption and make console output more useful.
    # Only do so for non fadump image.
    mkdir -p ${initdir}/etc/systemd/journald.conf.d
    echo "[Journal]" > ${initdir}/etc/systemd/journald.conf.d/kdump.conf
    echo "Storage=volatile" >> ${initdir}/etc/systemd/journald.conf.d/kdump.conf
    echo "ReadKMsg=no" >> ${initdir}/etc/systemd/journald.conf.d/kdump.conf
    echo "ForwardToConsole=yes" >> ${initdir}/etc/systemd/journald.conf.d/kdump.conf
}

install() {
    declare -A unique_netifs
    local arch _netifs

    kdump_module_init
    kdump_install_conf
    remove_sysctl_conf

    # Onlining secondary cpus breaks kdump completely on KVM on Power hosts
    # Though we use maxcpus=1 by default but 40-redhat.rules will bring up all
    # possible cpus by default. (rhbz1270174 rhbz1266322)
    # Thus before we get the kernel fix and the systemd rule fix let's remove
    # the cpu online rule in kdump initramfs.
    arch=$(uname -m)
    if [[ "$arch" = "ppc64le" ]] || [[ "$arch" = "ppc64" ]]; then
        remove_cpu_online_rule
    fi

    if is_ssh_dump_target; then
        kdump_install_random_seed
    fi
    dracut_install -o /etc/adjtime /etc/localtime
    inst "$moddir/monitor_dd_progress" "/kdumpscripts/monitor_dd_progress"
    chmod +x ${initdir}/kdumpscripts/monitor_dd_progress
    inst "/bin/dd" "/bin/dd"
    inst "/bin/tail" "/bin/tail"
    inst "/bin/date" "/bin/date"
    inst "/bin/sync" "/bin/sync"
    inst "/bin/cut" "/bin/cut"
    inst "/bin/head" "/bin/head"
    inst "/sbin/makedumpfile" "/sbin/makedumpfile"
    inst "/sbin/vmcore-dmesg" "/sbin/vmcore-dmesg"
    inst "/usr/bin/printf" "/sbin/printf"
    inst "/usr/bin/logger" "/sbin/logger"
    inst "/usr/bin/chmod" "/sbin/chmod"
    inst "/lib/kdump/kdump-lib.sh" "/lib/kdump-lib.sh"
    inst "/lib/kdump/kdump-lib-initramfs.sh" "/lib/kdump-lib-initramfs.sh"
    inst "/lib/kdump/kdump-logger.sh" "/lib/kdump-logger.sh"
    inst "$moddir/kdump.sh" "/usr/bin/kdump.sh"
    inst "$moddir/kdump-capture.service" "$systemdsystemunitdir/kdump-capture.service"
    systemctl -q --root "$initdir" add-wants initrd.target kdump-capture.service
    inst "$moddir/kdump-error-handler.sh" "/usr/bin/kdump-error-handler.sh"
    inst "$moddir/kdump-error-handler.service" "$systemdsystemunitdir/kdump-error-handler.service"
    # Replace existing emergency service and emergency target
    cp "$moddir/kdump-emergency.service" "$initdir/$systemdsystemunitdir/emergency.service"
    cp "$moddir/kdump-emergency.target" "$initdir/$systemdsystemunitdir/emergency.target"
    # Also redirect dracut-emergency to kdump error handler
    ln_r "$systemdsystemunitdir/emergency.service" "$systemdsystemunitdir/dracut-emergency.service"

    # Check for all the devices and if any device is iscsi, bring up iscsi
    # target. Ideally all this should be pushed into dracut iscsi module
    # at some point of time.
    kdump_check_iscsi_targets

    _netifs=$(_get_kdump_netifs)
    if [[ -n "$_netifs" ]]; then
        kdump_install_nm_netif_allowlist "$_netifs"
    fi

    kdump_install_systemd_conf

    # For the lvm type target under kdump, in /etc/lvm/lvm.conf we can
    # safely replace "reserved_memory=XXXX"(default value is 8192) with
    # "reserved_memory=1024" to lower memory pressure under kdump. We do
    # it unconditionally here, if "/etc/lvm/lvm.conf" doesn't exist, it
    # actually does nothing.
    sed -i -e \
      's/\(^[[:space:]]*reserved_memory[[:space:]]*=\)[[:space:]]*[[:digit:]]*/\1 1024/' \
      ${initdir}/etc/lvm/lvm.conf &>/dev/null

    # Save more memory by dropping switch root capability
    dracut_no_switch_root
}
