#!/bin/bash

# Development setup script for conda environment
echo "Setting up development environment..."

# Create or update conda environment
conda env create -f environment.yml --force
conda activate ra

# Install development tools
conda install -c conda-forge pytest pytest-cov black isort flake8 mypy pre-commit bandit jupyter -y

# Install package in development mode
pip install -e .

# Setup pre-commit hooks
pre-commit install

echo "Development environment setup complete!"
echo "To activate: conda activate ra" 