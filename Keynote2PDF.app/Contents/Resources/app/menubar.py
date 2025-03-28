import rumps
import os
import subprocess
import webbrowser


class Keynote2PDFMenuBar(rumps.App):
    def __init__(self):
        super().__init__("📄", quit_button=None)
        self.menu = [
            "Open Keynote2PDF",
            "Check Status",
            None,  # Separator
            "Start Service",
            "Stop Service",
            None,  # Separator
            "Uninstall",
            rumps.MenuItem("Quit"),
        ]

    @rumps.clicked("Open Keynote2PDF")
    def open_app(self, _):
        webbrowser.open("http://127.0.0.1:8080")

    @rumps.clicked("Check Status")
    def check_status(self, _):
        try:
            result = subprocess.run(
                ["curl", "-s", "-I", "http://127.0.0.1:8080"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and "200 OK" in result.stdout:
                rumps.notification("Keynote2PDF Status", "", "Service is running")
            else:
                rumps.notification("Keynote2PDF Status", "", "Service is not running")
        except Exception:
            rumps.notification("Keynote2PDF Status", "", "Service is not running")

    @rumps.clicked("Start Service")
    def start_service(self, _):
        subprocess.run(["launchctl", "start", "com.keynote2pdf.converter"])
        rumps.notification("Keynote2PDF", "", "Service started")

    @rumps.clicked("Stop Service")
    def stop_service(self, _):
        subprocess.run(["launchctl", "stop", "com.keynote2pdf.converter"])
        rumps.notification("Keynote2PDF", "", "Service stopped")

    @rumps.clicked("Uninstall")
    def uninstall(self, _):
        if rumps.alert(
            "Uninstall Keynote2PDF?",
            "This will remove all application files and settings.",
            ok="Uninstall",
            cancel="Cancel",
        ):
            # Stop the service
            subprocess.run(["launchctl", "stop", "com.keynote2pdf.converter"])
            subprocess.run(
                [
                    "launchctl",
                    "unload",
                    os.path.expanduser(
                        "~/Library/LaunchAgents/com.keynote2pdf.converter.plist"
                    ),
                ]
            )

            # Remove files
            subprocess.run(["rm", "-rf", os.path.expanduser("~/.keynote2pdf")])
            subprocess.run(
                [
                    "rm",
                    "-f",
                    os.path.expanduser(
                        "~/Library/LaunchAgents/com.keynote2pdf.converter.plist"
                    ),
                ]
            )

            # Quit the app
            rumps.quit_application()

    @rumps.clicked("Quit")
    def quit(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    Keynote2PDFMenuBar().run()
