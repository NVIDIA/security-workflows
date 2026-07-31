# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Mark the locally built TruffleHog wheel as platform-specific."""

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel


class bdist_wheel(_bdist_wheel):
    """The downloaded executable makes this wheel platform-specific."""

    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        _, _, platform = super().get_tag()
        return "py3", "none", platform


setup(cmdclass={"bdist_wheel": bdist_wheel})
