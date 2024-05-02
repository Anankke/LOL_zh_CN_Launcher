import subprocess
import time
from pathlib import Path

import psutil
from ruamel.yaml import YAML, scalarstring
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class YamlProcessor:
    def __init__(self, file_path):
        self.RCS_path = None
        self.file_path = Path(file_path)
        self.yaml = YAML()

    def transform(self, data):
        return (
            scalarstring.DoubleQuotedScalarString(data)
            if isinstance(data, str)
            else [self.transform(item) for item in data]
            if isinstance(data, list)
            else {k: self.transform(v) for k, v in data.items()}
            if isinstance(data, dict)
            else data
        )

    def get_rcs_path(self):
        if self.RCS_path:
            return self.RCS_path
        with self.file_path.open("r") as file:
            data = self.yaml.load(file)
            self.RCS_path = Path(
                data["product_install_root"] + "/Riot Client/RiotClientServices.exe"
            )
        return self.RCS_path

    def process_yaml(self):
        while True:
            try:
                with self.file_path.open("r+") as file:
                    data = self.yaml.load(file)
                    locale_data = data.setdefault("locale_data", {})
                    available_locales = locale_data.setdefault("available_locales", [])
                    if (
                        "zh_CN" not in available_locales
                        or locale_data["default_locale"] != "zh_CN"
                        or data["settings"]["locale"] != "zh_CN"
                    ):
                        if "zh_CN" not in available_locales:
                            available_locales.append("zh_CN")
                        locale_data["default_locale"] = "zh_CN"
                        data["settings"]["locale"] = "zh_CN"
                        file.seek(0)
                        self.yaml.dump(self.transform(data), file)
                        file.truncate()
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.1)


class LolLauncher:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.processor = YamlProcessor(self.file_path)
        self.event_handler = FileSystemEventHandler()
        self.event_handler.on_modified = lambda event: self.processor.process_yaml()
        self.processor.process_yaml()
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler, path=str(self.file_path.parent), recursive=False
        )
        self.observer.start()

    def open_exe(self):
        subprocess.Popen(
            [
                str(self.processor.get_rcs_path()),
                "--launch-product=league_of_legends",
                "--launch-patchline=live",
            ]
        )

    def run(self):
        self.open_exe()
        try:
            while True:
                if "LeagueClientUxRender.exe" in (
                    p.name() for p in psutil.process_iter()
                ):
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.observer.stop()
            self.observer.join()


file_path = "C:/ProgramData/Riot Games/Metadata/league_of_legends.live/league_of_legends.live.product_settings.yaml"
launcher = LolLauncher(file_path)
launcher.run()
