#!/bin/bash

FILE=$1
MESSAGE=$2

if [ -z "$FILE" ] || [ -z "$MESSAGE" ]; then
  echo "Usage: ./gitpush_file.sh <file_path> \"commit message\""
  exit 1
fi

if [ ! -f "$FILE" ]; then
  echo "Error: File '$FILE' does not exist."
  exit 1
fi

# Check for large file (>50MB)
echo "Checking file size..."
FILE_SIZE=$(du -m "$FILE" | cut -f1)
if [ "$FILE_SIZE" -gt 50 ]; then
  echo "Warning: File '$FILE' is ${FILE_SIZE}MB."
  echo "GitHub has a hard limit of 100MB and recommends files under 50MB."
  read -p "Do you want to continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting push. Consider using Git LFS for large files."
    exit 1
  fi
fi

CURRENT_BRANCH=$(git branch --show-current)

git add "$FILE"
git commit -m "$MESSAGE"

# Push with large buffer if needed
echo "Pushing changes to origin/$CURRENT_BRANCH..."
git -c http.postBuffer=524288000 push origin "$CURRENT_BRANCH"
