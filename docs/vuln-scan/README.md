# Build environments for vulnerability scans

Source files alone may not tell the scanner which dependency versions are used.
Prepare the environment for the version and configuration being scanned.

**Current workflow:** `build: true` enables scanner build mode; it is not a Python
environment setup step. A dependency-setup step and custom Detect properties are not
currently exposed as workflow inputs. The guidance below describes the preparation
needed when that support is available; it is not a caller configuration for today.

## Python projects

For an installed-package scan:

1. Build matching wheels using the project's normal, reviewed build process.
2. Inside the scanner container, create a separate virtual environment with a
   compatible Python version. Install the wheels and their runtime dependencies.
3. Run that environment's `python -m pip check`. Fix missing or incompatible
   dependencies before scanning.
4. Point Detect at that environment. Example Detect properties:

   ```text
   detect.included.detector.types=PIP
   detect.python.path=/work/scan-venv/bin/python
   detect.pip.path=/work/scan-venv/bin/pip
   detect.pip.project.name=<installed-package-name>
   ```

These are Detect properties, not workflow input names. The example paths must
exist inside the scanner container.

Keep build tools and test extras out of a runtime-only environment. If tests or
optional features are in scope, include their dependencies deliberately. Do not
remove genuine runtime dependencies just to make the scan pass.

## Common problems

- **Missing build dependencies:** follow the project's supported setup instructions.
  Do not assume scanner build mode supplies the required tools or Python packages.
- **Dynamic package metadata or dependency-resolution errors:** installed-package
  inspection can be an alternative, provided it covers the intended dependency set.
  PIP-only selection is not a whole-repository solution for mixed-language projects.
- **Dependencies installed in another job:** they are not automatically available
  inside the scanner container. Transfer build artifacts, then prepare the scan
  environment there; do not copy virtual environments across incompatible systems.

## Check the result

Check detailed scanner status, a complete report, and the expected dependency names
and versions. A successful exit or empty vulnerability report alone does not prove
dependencies were found. Do not hide analysis failures to get a pass.

Use the approved scanner image and trusted build artifacts. Keep credentials out
of setup commands, properties and logs. Do not modify the scanner's own Python
environment or bypass its authentication controls.
