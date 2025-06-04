import pkg_resources
import sys

def check_package(package_name):
    try:
        pkg_resources.get_distribution(package_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False

# List of packages to check from environment.yml
packages_to_check = [
    'opencv-python',  # opencv
    'numpy',
    'matplotlib',
    'scipy',
    'scikit-image',
    'scikit-learn',
    'pandas',
    'pillow',
    'gradio',
    'streamlit',
    'PyPDF2',
    'requests',
    'readlif',
    'biopython',
    'openai',
    'joblib',
    'streamlit-drawable-canvas',
    'boto3',
    'botocore',
    'azure-identity',
    'azure-mgmt-resource',
    'spacy',
    'en_ner_bionlp13cg_md'
]

print("Checking package installations...")
print("-" * 50)

missing_packages = []
for package in packages_to_check:
    if check_package(package):
        print(f"✓ {package} is installed")
    else:
        print(f"✗ {package} is NOT installed")
        missing_packages.append(package)

print("\nSummary:")
print("-" * 50)
if missing_packages:
    print(f"Missing packages ({len(missing_packages)}):")
    for package in missing_packages:
        print(f"- {package}")
else:
    print("All packages are installed!") 