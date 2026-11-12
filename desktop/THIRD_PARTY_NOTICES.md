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
  opened as ZIP files. The reviewed 0.27.7 runtime wheels each contain license
  files; some packages and bundled components have multiple licenses.
- OpenSSL 3.5.7: Apache License 2.0, Copyright (c) 1998-2026 The OpenSSL
  Project Authors and Copyright (c) 1995-1998 Eric A. Young and Tim J. Hudson.
  An Apache 2.0 license text is included in `licenses/PYTHON.txt`. The build
  interpreter's OpenSSL version is recorded in `licenses/build-manifest.json`.
  OpenSSL source and notices:
  https://github.com/openssl/openssl/tree/openssl-3.5.7
- libffi: its copyright and license are included in `licenses/PYTHON.txt`.
- Microsoft runtime DLLs: Microsoft requires checking the applicable license
  terms, provenance and REDIST list for the distributor's environment:
  https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files

The application's browser and desktop build source is in
`source/application-source.zip`. This is the snapshot used for this build; it
does not include the full repository, examples, private data or generated
outputs. Before distribution, verify the Pyodide and pystray source and all
required notices remain accessible to recipients, and review the Microsoft
runtime terms and all other applicable obligations.

The application's own license is included separately in `LICENSE`.