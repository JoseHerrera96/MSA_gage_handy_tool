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
  launch. The LGPL permits modification of the library and reverse engineering
  for debugging such modifications. Preserve those rights and ensure any
  required source remains available to recipients.
- Pyodide 0.27.7 and matplotlib-pyodide 0.2.3: MPL 2.0. A license copy is in
  `licenses/MPL-2.0.txt`. Upstream source:
  https://github.com/pyodide/pyodide/tree/0.27.7
  Its `pyodide-build` submodule is:
  https://github.com/pyodide/pyodide-build/tree/438b59b5a5e881cef2ab76522ec4c416612b5298
  matplotlib-pyodide 0.2.3 source:
  https://github.com/pyodide/matplotlib-pyodide/tree/v0.2.3
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
- Microsoft UCRT and API-set DLLs: the `--system-ucrt` build does not distribute
  local copies and requires Windows 10 or later. Windows supplies the UCRT:
  https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment
  The alternative SDK build includes verified Windows SDK 10.0.22621.2428
  redistributables and `licenses/WINDOWS-SDK.rtf`. That SDK license and REDIST
  list impose conditions on redistribution:
  https://learn.microsoft.com/en-us/legal/windows-sdk/redist
- Microsoft Visual C++ runtime DLLs: review the applicable Visual Studio
  license and redistribution terms for the distributor's environment:
  https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution

## Distribution review

The `--system-ucrt` build omits the Windows SDK UCRT files and their SDK
license. Its build script verifies the two Visual C++ DLLs against Microsoft
14.42.34438.0; those files remain subject to applicable Visual Studio terms.
The presence of those binaries does not itself establish the distributor's
eligibility or compliance. See `licenses/build-manifest.json` for the selected
mode.

For the `sdk-redist-review` build, the 40 UCRT/API-set DLLs match the verified
Windows SDK redistributable, and both Visual C++ runtime DLLs match the verified
Microsoft 14.42.34438.0 redistributable. Their Microsoft signatures were valid
when checked. All 15 Pyodide wheels contain license files; this check does not
establish that every license obligation has been satisfied.

Before sharing the SDK-based build, the distributor must address the following:

- The included SDK license requires distributors and external end users to
  agree to terms protecting the distributable code at least as much as that
  agreement. This application does not currently request that agreement.
  Including the SDK license file is not itself evidence of acceptance.
- The SDK license requires a valid copyright notice. The application's
  `LICENSE` has a year but does not identify a copyright holder. The owner
  should determine the appropriate notice and whether it meets this requirement.
- The SDK license includes an obligation for the distributor to indemnify,
  defend and hold Microsoft harmless in connection with certain claims. This is
  an obligation of the distributor, not something a build script can accept.
- For either build, Visual Studio Community is installed, but installation alone does not prove
  that the distributor qualifies under the applicable license for their use.
- Confirm the corresponding source and any patches for the distributed MPL
  and LGPL components are available to recipients, and review the LGPL's
  modification, replacement and reverse-engineering provisions. The source ZIP
  included in the bundle contains application source, not all third-party source.

These points require review in the distributor's circumstances; they are not
an assertion that the bundle is ready for public distribution.

The application's browser and desktop build source is in
`source/application-source.zip`. This is the snapshot used for this build; it
does not include the full repository, examples, private data or generated
outputs. Before distribution, verify the Pyodide and pystray source and all
required notices remain accessible to recipients, and review the Microsoft
runtime terms and all other applicable obligations.

The application's own license is included separately in `LICENSE`.