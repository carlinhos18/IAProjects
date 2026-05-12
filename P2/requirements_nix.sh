#!/usr/bin/env bash
nix-shell -p python313Packages.scikit-learn \
    python313Packages.numpy \
    python313Packages.pandas \
    python313Packages.livereload
