import http.client
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))
from launcher import start_server
from build import build, stage_runtime


class DesktopServerTests(unittest.TestCase):
    def test_application_source_snapshot_excludes_data_and_matches_sources(self):
        import build as desktop_build

        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "snapshot"
            archive_path = desktop_build.stage_application_source(snapshot)
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIn("desktop/launcher.py", names)
                self.assertIn("tests/browser_poc_server.py", names)
                self.assertFalse(any(name.startswith(("data/", "outputs/")) for name in names))
                for name in names:
                    with self.subTest(source=name):
                        self.assertEqual(archive.read(name), (snapshot / name).read_bytes())

    def test_tray_opens_browser_and_stops_server(self):
        from unittest.mock import MagicMock
        import launcher

        server = MagicMock(server_port=12345)
        icon = MagicMock()
        tray = MagicMock()
        tray.Icon.return_value = icon
        tray.Menu.side_effect = lambda *items: items
        tray.MenuItem.side_effect = lambda text, action, **kwargs: (text, action)
        with patch.dict(sys.modules, {"pystray": tray}), patch.object(launcher, "start_server", return_value=server), patch.object(launcher.webbrowser, "open", return_value=True) as browser:
            def run(setup):
                setup(icon)
                items = tray.Icon.call_args.kwargs["menu"]
                self.assertEqual([item[0] for item in items], ["Abrir aplicacion", "Cerrar servidor"])
                items[0][1](icon, None)
                items[1][1](icon, None)

            icon.run.side_effect = run
            launcher.main()
        self.assertEqual(browser.call_count, 2)
        browser.assert_called_with("http://127.0.0.1:12345/app")
        icon.stop.assert_called_once()
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()

    def test_tray_failure_stops_server(self):
        from unittest.mock import MagicMock
        import launcher

        server = MagicMock(server_port=12345)
        tray = MagicMock()
        tray.Icon.side_effect = RuntimeError("tray unavailable")
        with patch.dict(sys.modules, {"pystray": tray}), patch.object(launcher, "start_server", return_value=server), patch.object(launcher, "show_error") as error:
            launcher.main()
        error.assert_called_once()
        self.assertIn("tray unavailable", error.call_args.args[0])
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()

    def test_build_rejects_unverified_core_and_existing_distribution(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            archive = directory / "core.tar.bz2"
            archive.write_bytes(b"not an official archive")
            with self.assertRaisesRegex(ValueError, "checksum"):
                stage_runtime(archive, directory, directory / "runtime")
            self.assertFalse((directory / "runtime").exists())
            (directory / "MSA-Handy-Tool").mkdir()
            with self.assertRaises(FileExistsError):
                build(archive, directory, directory)

    def test_build_uses_source_collection_hook(self):
        import build as desktop_build

        with tempfile.TemporaryDirectory() as temporary, patch.object(desktop_build, "stage_runtime"), patch.object(desktop_build, "stage_licenses"), patch.object(desktop_build.subprocess, "run") as run:
            def check_build(command, **kwargs):
                hook_directory = Path(command[command.index("--additional-hooks-dir") + 1])
                self.assertEqual((hook_directory / "hook-pystray.py").read_text().strip(), 'module_collection_mode = "py"')
                source_argument = next(value for value in command if value.endswith("application-source.zip;source"))
                self.assertTrue(Path(source_argument.split(";", 1)[0]).is_file())

            run.side_effect = check_build
            build(Path("core.tar.bz2"), Path("packages"), Path(temporary))
            command = run.call_args.args[0]
            self.assertIn("pystray", command)
            self.assertIn("six", command)

    def test_local_server_restricts_routes_and_stops(self):
        with tempfile.TemporaryDirectory() as temporary, patch("launcher.validate_pyodide_runtime", return_value=set()):
            server = start_server(Path(temporary))
            port = server.server_port
            self.assertEqual(server.server_address[0], "127.0.0.1")
            try:
                for path, expected in (("/app", 200), ("/runtime-config.json", 200), ("/", 404), ("/baseline.json", 404), ("/data/private/example.txt", 404)):
                    with self.subTest(path=path):
                        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                        connection.request("GET", path)
                        response = connection.getresponse()
                        self.assertEqual(response.status, expected)
                        if path == "/app":
                            self.assertNotIn("cdn.jsdelivr.net", response.getheader("Content-Security-Policy"))
                        if path == "/runtime-config.json":
                            self.assertIn(b'"/runtime/"', response.read())
                        connection.close()
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("GET", "/app", headers={"Host": "example.invalid"})
                self.assertEqual(connection.getresponse().status, 403)
                connection.close()
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("POST", "/app", body=b"synthetic")
                self.assertEqual(connection.getresponse().status, 501)
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
            with self.assertRaises(OSError):
                http.client.HTTPConnection("127.0.0.1", port, timeout=1).connect()


if __name__ == "__main__":
    unittest.main()