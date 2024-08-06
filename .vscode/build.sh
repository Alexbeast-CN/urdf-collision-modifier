#!/bin/bash
set -e

# Change python interpreter to /usr/bin/python3
export PATH="/usr/bin:$PATH"

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

# Limit the thread number for compiling
# thread_count=$(nproc --all)
# threads_for_compilation=$((thread_count - 6))
# export MAKEFLAGS="-j $threads_for_compilation"

BUILD_TYPE=RelWithDebInfo
colcon build \
    --cmake-args  -DCMAKE_BUILD_TYPE=RelWithDebInfo\
    -Wall -Wextra -Wpedantic \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    --symlink-install \
    --parallel-workers 4
    # --packages-select dd6ax_path_follower \
