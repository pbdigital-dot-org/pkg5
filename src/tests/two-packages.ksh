#!/bin/ksh -px
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END

# Copyright 2007 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

eval `pkgsend open library/libc@0.1-1`
if [ $? != 0 ]; then
	echo \*\* script aborted:  couldn\'t open library/libc
	exit 1
fi

echo $PKG_TRANS_ID
pkgsend add dir 0755 root bin /lib
pkgsend add file 0555 root bin \
	/lib/libc.so.1 /lib/libc.so.1
pkgsend add link /lib/libc.so /lib/libc.so.1
pkgsend close

eval `pkgsend open application/cat@0.1-1`
if [ $? != 0 ]; then
	echo \*\* script aborted:  couldn\'t open application/cat
	exit 1
fi

echo $PKG_TRANS_ID
pkgsend add depend require pkg:/library/libc@0.1-1
pkgsend add dir 0755 root bin /usr
pkgsend add dir 0755 root bin /usr/bin
pkgsend add file 0555 root bin \
	/usr/bin/cat /usr/bin/cat
pkgsend close
