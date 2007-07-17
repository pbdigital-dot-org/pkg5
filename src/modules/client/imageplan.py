#!/usr/bin/python
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
#

# Copyright 2007 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import os
import re
import urllib

import pkg.catalog as catalog
import pkg.fmri as fmri

import pkg.client.pkgplan as pkgplan
import pkg.client.retrieve as retrieve # XXX inventory??

UNEVALUATED = 0
EVALUATED_OK = 1
EVALUATED_ERROR = 2
EXECUTED_OK = 3
EXECUTED_ERROR = 4

class ImagePlan(object):
        """An image plan takes a list of requested packages, an Image (and its
        policy restrictions), and returns the set of package operations needed
        to transform the Image to the list of requested packages.

        Use of an ImagePlan involves the identification of the Image, the
        Catalogs (implicitly), and a set of complete or partial package FMRIs.
        The Image's policy, which is derived from its type and configuration
        will cause the formulation of the plan or an exception state.

        XXX In the current formulation, an ImagePlan can handle [null ->
        PkgFmri] and [PkgFmri@Version1 -> PkgFmri@Version2], for a set of
        PkgFmri objects.  With a correct Action object definition, deletion
        should be able to be represented as [PkgFmri@V1 -> null].

        XXX Should we allow downgrades?  There's an "arrow of time" associated
        with the smf(5) configuration method, so it's better to direct
        manipulators to snapshot-based rollback, but if people are going to do
        "pkg delete fmri; pkg install fmri@v(n - 1)", then we'd better have a
        plan to identify when this operation is safe or unsafe."""

        def __init__(self, image):
                self.image = image
                self.goal_fmris = []
                self.state = UNEVALUATED

                self.target_fmris = []
                self.pkg_plans = []

        def __str__(self):
                if self.state == UNEVALUATED:
                        s = "UNEVALUATED: "
                        for t in self.target_fmris:
                                s = s + "%s\n" % t
                        return s

                for pp in self.pkg_plans:
                        s = s + "%s\n" % pp
                return s

        def set_goal_pkg_fmris(self, pflist):
                self.goal_pkg_fmris = pflist

        def is_proposed_fmri(self, fmri):
                for pf in self.target_fmris:
                        if fmri.is_same_pkg(pf):
                                if not fmri.is_successor(pf):
                                        return True
                                else:
                                        return False
                return False

        def propose_fmri(self, fmri):
                # is a version of fmri.stem in the inventory?
                if self.image.is_installed(fmri):
                        return

                #   is there a freeze or incorporation statement?
                #   do any of them eliminate this fmri version?
                #     discard

                # is a version of fmri in our target_fmris?
                n = range(len(self.target_fmris))
                if n == []:
                        self.target_fmris.append(fmri)
                        return

                for i in n:
                        p = self.target_fmris[i]
                        if fmri.is_same_pkg(p):
                                if fmri.is_successor(p):
                                        self.target_fmris[i] = fmri
                                        break

                return

        def evaluate_fmri(self, pfmri):

                # [image] do we have this manifest?
                if not self.image.has_manifest(pfmri):
                        retrieve.get_manifest(self.image, pfmri)

                m = self.image.get_manifest(pfmri)

                # [manifest] examine manifest for dependencies
                for a in m.actions:
                        if a.name != "depend":
                                continue

                        f = fmri.PkgFmri(a.attrs["fmri"],
                            self.image.attrs["Build-Release"])

                        if self.image.is_installed(f):
                                continue

                        if self.is_proposed_fmri(f):
                                continue

                        # XXX LOG  "%s not in pending transaction;
                        # checking catalog" % f

                        required = True
                        excluded = False

                        if a.attrs["type"] == "optional" and \
                            not self.image.attrs["Policy-Require-Optional"]:
                                required = False
                        elif a.attrs["type"] == "exclude":
                                excluded = True

                        if not required:
                                continue

                        if excluded:
                                raise RuntimeError, "excluded by '%s'" % f

                        # treat-as-required, treat-as-required-unless-pinned, ignore
                        # skip if ignoring
                        #     if pinned
                        #       ignore if treat-as-required-unless-pinned
                        #     else
                        #       **evaluation of incorporations**
                        #     [imageplan] pursue installation of this package -->
                        #     backtrack or reset??

                        mvs = self.image.get_matching_pkgs(f)

                        cf = f
                        for i in mvs:
                                if i[1].is_successor(cf):
                                         cf = i[1]

                        # XXX LOG "adding dependency %s" % pfmri
                        self.evaluate_fmri(cf)

                pp = pkgplan.PkgPlan(self.image)

                try:
                        pp.propose_destination(pfmri, m)
                except RuntimeError:
                        print "pkg: %s already installed" % pfmri
                        return

                pp.evaluate()

                self.pkg_plans.append(pp)

        def evaluate(self):
                assert self.state == UNEVALUATED

                for f in self.target_fmris:
                        self.evaluate_fmri(f)

                self.state = EVALUATED_OK

        def execute(self):
                """Invoke the evaluated image plan, constructing each package
                plan."""
                assert self.state == EVALUATED_OK

                # image related operations, like a snapshot

                for p in self.pkg_plans:
                        p.preexecute()

                for p in self.pkg_plans:
                        # per-package image operations (further snapshots)
                        p.execute()

                for p in self.pkg_plans:
                        p.postexecute()

                self.state = EXECUTED_OK

