# Third-Party Components

This experimental bundle is not approved for public redistribution. Review
all bundled components, native libraries and source-availability obligations
before sharing. Versions and files below describe the identified build; review
them again for each build environment.

- pystray 0.19.5, Copyright (C) 2016-2022 Moses Palmér: LGPL version 3 or later.
  The license texts are in `pystray-0.19.5.dist-info/COPYING.LGPL` and
  `pystray-0.19.5.dist-info/COPYING`. Upstream source:
  https://github.com/moses-palmer/pystray/tree/v0.19.5
  The Windows modules used by this build are provided as Python source under
  `pystray/`; compatible modifications to these files can be loaded on the next
  launch. The distributor must review the LGPL's source, replacement and
  reverse-engineering provisions and ensure any required source remains available.
- Pyodide 0.27.7 and matplotlib-pyodide 0.2.3: MPL 2.0. A license copy is in
  `licenses/MPL-2.0.txt`. Upstream source:
  https://github.com/pyodide/pyodide/tree/0.27.7
  Ensure recipients can obtain the corresponding source, including any changes.
- OpenBLAS 0.3.26 in the Pyodide runtime: BSD 3-Clause. The copyright and
  license are in `licenses/OPENBLAS-0.3.26.txt`. Upstream source:
  https://github.com/OpenMathLib/OpenBLAS/tree/v0.3.26
- Python: the build interpreter's license and notices are in
  `licenses/PYTHON.txt`. Source: https://github.com/python/cpython
- Pillow and six for the launcher: their license files are in the corresponding
  `.dist-info` directories. NumPy's native build and its bundled components have
  notices under `numpy-*.dist-info/licenses/`.
- PyInstaller: the bootloader exception is described at
  https://pyinstaller.org/en/stable/license.html
- Other Pyodide scientific packages and transitive dependencies: see the
  METADATA and license files inside each `pyodide/*.whl`. The archives can be
  opened as ZIP files. Their individual terms need review.
- OpenSSL and Microsoft runtime DLLs are also included. The build interpreter's
  OpenSSL version is recorded in `licenses/build-manifest.json`. Its applicable
  license and any Microsoft runtime redistribution terms have not been
  comprehensively reviewed. OpenSSL 3.5.7 declares Apache License 2.0:
  https://github.com/openssl/openssl/tree/openssl-3.5.7
  Microsoft requires checking the applicable license terms and REDIST list:
  https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files

Before distribution, make the source corresponding to this exact application
build available alongside it, and verify that the Pyodide and pystray sources
and any required notices remain accessible to recipients.

The application's own license is included separately in `LICENSE`.