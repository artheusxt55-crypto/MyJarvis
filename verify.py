#!/usr/bin/env python3
"""
MyJarvis — Quick verification script
Run after install to verify everything works
"""
import sys
import subprocess
from pathlib import Path

def test_imports():
    """Test all module imports."""
    print("Testing imports...")
    modules = [
        "myjarvis",
        "myjarvis.cli",
        "myjarvis.core.config",
        "myjarvis.core.jarvis",
        "myjarvis.daemon",
        "myjarvis.engine.custom_openai",
        "myjarvis.ipc.bridge",
        "myjarvis.skills.registry",
        "myjarvis.skills.windows_control",
        "myjarvis.skills.bluetooth",
        "myjarvis.skills.audio",
        "myjarvis.skills.filesystem",
        "myjarvis.skills.process",
        "myjarvis.skills.network",
        "myjarvis.skills.power",
        "myjarvis.skills.schedule",
        "myjarvis.skills.clipboard",
        "myjarvis.skills.screenshot",
    ]
    
    failed = []
    for mod in modules:
        try:
            __import__(mod)
            print(f"  ✅ {mod}")
        except Exception as e:
            print(f"  ❌ {mod}: {e}")
            failed.append(mod)
    
    return len(failed) == 0

def test_cli():
    """Test CLI entry point."""
    print("\nTesting CLI...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "myjarvis", "--help"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("  ✅ CLI works")
            return True
        else:
            print(f"  ❌ CLI failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ CLI error: {e}")
        return False

def test_config():
    """Test config loading."""
    print("\nTesting config...")
    try:
        from myjarvis.core.config import load_config, get_myjarvis_dir
        config_dir = get_myjarvis_dir()
        print(f"  Config dir: {config_dir}")
        
        config = load_config()
        print(f"  ✅ Config loaded")
        print(f"  Model: {config.intelligence.default_model}")
        print(f"  Engine: {config.intelligence.preferred_engine}")
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False

def test_skills_registry():
    """Test skills registry."""
    print("\nTesting skills registry...")
    try:
        from myjarvis.skills.registry import SkillRegistry
        registry = SkillRegistry(enabled_skills=["windows_control", "process"])
        print(f"  ✅ Registry loaded")
        print(f"  Skills: {registry.list_available()}")
        return True
    except Exception as e:
        print(f"  ❌ Registry error: {e}")
        return False

def test_engine():
    """Test custom engine registration."""
    print("\nTesting engine...")
    try:
        from openjarvis.core.registry import EngineRegistry
        engines = EngineRegistry.keys()
        print(f"  Available engines: {list(engines)}")
        if "nvidia-openai" in engines:
            print("  ✅ nvidia-openai engine registered")
            return True
        else:
            print("  ⚠️  nvidia-openai not registered (will register on first use)")
            return True
    except Exception as e:
        print(f"  ❌ Engine error: {e}")
        return False

def main():
    print("=" * 50)
    print("MyJarvis — Verification")
    print("=" * 50)
    
    all_ok = True
    all_ok &= test_imports()
    all_ok &= test_cli()
    all_ok &= test_config()
    all_ok &= test_skills_registry()
    all_ok &= test_engine()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ ALL CHECKS PASSED")
        print("\nNext steps:")
        print("  1. Edit ~/.myjarvis/config.toml with your NVIDIA_API_KEY")
        print("  2. Run: myjarvis ask 'Olá, Jarvis'")
        print("  3. Run daemon: myjarvis-daemon")
    else:
        print("❌ SOME CHECKS FAILED")
        print("Check errors above and reinstall if needed:")
        print("  pip install -e . --force-reinstall")
    print("=" * 50)
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())