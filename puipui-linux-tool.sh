#!/bin/bash
# vim: set ts=4:
#---help---
# Usage: puipui-linux-tool [options]
#
# This script builds puipui linux kernel and it's initramfs.
#
# Options:
#   -u Only updates linux kernel config files. it does not build kernel or initramfs.
#---help---

set -eu

version=0.0.1

srcdir="$PWD"
target_arch="aarch64" # TODO: add x86_64
#kernver=5.19.12
kernver=5.15.71
name="PUI PUI Linux"

#if [ -z "$SOURCE_DATE_EPOCH" ]; then
	SOURCE_DATE_EPOCH=$(date -u "+%s")
#fi

msg() { echo -e "\033]2; $*\007\n=== $*"; }

usage() {
	sed -En '/^#---help---/,/^#---help---/p' "$0" | sed -E 's/^# ?//; 1d;$d;'
}

fetch_kernel() {
	# Download linux kernel
	local url=https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-"$kernver".tar.xz
        local archive=${url##*/}
        (cd $srcdir && curl -OL $url)
        tar -xvf "$srcdir"/"$archive" -C "$srcdir"
}

_kernelarch() {
	local arch="$1"
	case "$arch" in
		aarch64*) arch="arm64" ;;
	esac
	echo "$arch"
}

_kconfig() {
	local fname="$1"
	echo "kconfig/$fname"
}

_prepareconfig() {
	local _arch="$1"
	local _config=$(_kconfig $_arch.config)
	local _builddir="$srcdir"/build-$_arch
	mkdir -p "$_builddir"

	cp "$srcdir"/$_config "$_builddir"/.config
	msg "Configuring $name kernel ($_arch)"
	make -C "$srcdir"/linux-$kernver \
		O="$_builddir" \
		ARCH="$(_kernelarch $_arch)" \
		olddefconfig
}

build() {
	unset LDFLAGS
	export KBUILD_BUILD_TIMESTAMP="$(date -Ru${SOURCE_DATE_EPOCH:+d @$SOURCE_DATE_EPOCH})"
	for _arch in $target_arch; do
		_prepareconfig "$_arch"
	done
	for _arch in $target_arch; do
		msg "Building $_arch $name kernel"
		cd "$srcdir"/build-$_arch
		make ARCH="$(_kernelarch $_arch)" \
			CC="${CC:-gcc}" \
			AWK="${AWK:-mawk}" \
			KBUILD_BUILD_VERSION="$version-PUI PUI!"
	done
}

updateconfigs() {
	for _arch in $target_arch; do
		msg "Update $name kernel config ($_arch)"
		local _config=$(_kconfig $_arch.config)
		local _builddir="$srcdir"/build-$_arch
		mkdir -p "$_builddir"
		local actions="listnewconfig oldconfig"
		if ! [ -f "$_builddir"/.config ]; then
			cp "$srcdir"/$_config "$_builddir"/.config
			actions="olddefconfig"
			env | grep ^CONFIG_ >> "$_builddir"/.config || true
		fi
		make -j1 -C "$srcdir"/linux-$kernver \
			O="$_builddir" \
			ARCH="$(_kernelarch $_arch)" \
			$actions savedefconfig

		cp "$_builddir"/defconfig "$srcdir"/$_config
	done
}

while getopts ':uhv' OPTION; do
	case "$OPTION" in
		u) updateconfigs || true; exit 0;;
		h) usage; exit 0;;
		v) echo "puipui-linux-tool $version"; exit 0;;
	esac
done

if ! [ -d linux-"$kernver" ]; then
	fetch_kernel
fi

build
