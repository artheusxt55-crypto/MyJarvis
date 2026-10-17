"""
MyJarvis — Setup and Installation
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_setup(install_service: bool = False, autostart: bool = True) -> int:
    """Run MyJarvis setup."""
    print("🔧 MyJarvis Setup")
    print("=" * 40)

    # 1. Create directories
    _create_directories()

    # 2. Copy config if not exists
    _install_config()

    # 3. Install Python package
    _install_package()

    # 4. Configure autostart
    if autostart:
        _setup_autostart()

    # 5. Install Windows Service (optional)
    if install_service:
        _install_windows_service()

    # 6. Verify installation
    _verify_installation()

    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("  1. Edit ~/.myjarvis/config.toml with your NVIDIA_API_KEY")
    print("  2. Run: myjarvis-daemon (or myjarvis-tray for tray icon)")
    print("  3. Test: myjarvis ask 'Olá, Jarvis'")

    return 0


def _create_directories() -> None:
    """Create MyJarvis directories."""
    dirs = [
        Path("~/.myjarvis").expanduser(),
        Path("~/.myjarvis/logs").expanduser(),
        Path("~/.myjarvis/skills").expanduser(),
        Path("~/.myjarvis/cache").expanduser(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  📁 {d}")


def _install_config() -> None:
    """Copy default config if not exists."""
    config_path = Path("~/.myjarvis/config.toml").expanduser()
    if not config_path.exists():
        # Copy from package
        import myjarvis
        pkg_config = Path(myjarvis.__file__).parent / "config.toml"
        if pkg_config.exists():
            shutil.copy2(pkg_config, config_path)
            print(f"  📄 Config copied to {config_path}")
        else:
            print(f"  ⚠️  Default config not found in package")
    else:
        print(f"  📄 Config already exists at {config_path}")


def _install_package() -> None:
    """Install MyJarvis package in development mode."""
    pkg_root = Path(__file__).parent.parent
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(pkg_root)],
            check=True,
            capture_output=True,
        )
        print("  📦 Package installed (editable mode)")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Package install failed: {e.stderr.decode() if e.stderr else e}")


def _setup_autostart() -> None:
    """Configure Windows auto-start via Task Scheduler."""
    try:
        # Get python executable and script path
        python_exe = sys.executable
        script_path = shutil.which("myjarvis-daemon") or shutil.which("myjarvis-tray")

        if not script_path:
            print("  ⚠️  myjarvis-daemon not found in PATH")
            return

        # Create task scheduler XML
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Name>MyJarvis</Name>
    <Description>MyJarvis AI Assistant Daemon</Description>
    <Author>{os.getenv('USERNAME')}</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>{script_path} --foreground</Arguments>
      <WorkingDirectory>{Path.home()}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

        # Save XML and register task
        xml_path = Path.home() / "myjarvis_task.xml"
        xml_path.write_text(task_xml, encoding="utf-16")

        subprocess.run(
            ["schtasks", "/create", "/tn", "MyJarvis", "/xml", str(xml_path), "/f"],
            check=True,
            capture_output=True,
        )
        xml_path.unlink(missing_ok=True)

        print("  🔄 Auto-start configured (Task Scheduler)")

    except Exception as e:
        print(f"  ⚠️  Auto-start setup failed: {e}")


def _install_windows_service() -> None:
    """Install as Windows Service (requires admin)."""
    try:
        import win32serviceutil
        import win32service
        import win32event

        print("  🔧 Installing Windows Service...")

        # This would require a proper service class
        # For now, just notify
        print("  ⚠️  Windows Service install not fully implemented")
        print("      Use Task Scheduler auto-start instead (default)")

    except ImportError:
        print("  ⚠️  pywin32 not available for service install")
    except Exception as e:
        print(f"  ⚠️  Service install failed: {e}")


def _verify_installation() -> None:
    """Verify installation works."""
    try:
        # Test import
        import myjarvis
        print(f"  ✅ Import OK: myjarvis {myjarvis.__version__}")

        # Test CLI
        result = subprocess.run(
            [sys.executable, "-m", "myjarvis", "--help"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("  ✅ CLI works")
        else:
            print(f"  ⚠️  CLI test failed: {result.stderr}")

    except Exception as e:
        print(f"  ⚠️  Verification failed: {e}")


def uninstall() -> int:
    """Uninstall MyJarvis."""
    print("🗑️  MyJarvis Uninstall")
    print("=" * 40)

    # Remove scheduled task
    try:
        subprocess.run(["schtasks", "/delete", "/tn", "MyJarvis", "/f"], capture_output=True)
        print("  🗑️  Auto-start task removed")
    except Exception:
        pass

    # Remove package
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "myjarvis"], capture_output=True)
        print("  🗑️  Package uninstalled")
    except Exception:
        pass

    # Ask about data
    data_dir = Path("~/.myjarvis").expanduser()
    if data_dir.exists():
        response = input(f"  Remove data directory {data_dir}? (y/N): ")
        if response.lower() == "y":
            shutil.rmtree(data_dir)
            print("  🗑️  Data directory removed")

    print("\n✅ Uninstall complete")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MyJarvis Setup")
    parser.add_argument("--service", action="store_true", help="Install as Windows Service")
    parser.add_argument("--no-autostart", action="store_true", help="Disable auto-start")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall MyJarvis")

    args = parser.parse_args()

    if args.uninstall:
        sys.exit(uninstall())
    else:
        sys.exit(run_setup(install_service=args.service, autostart=not args.no_autostart))