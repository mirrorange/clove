#!/usr/bin/env python3
"""Build script for Clove - builds frontend and creates Python wheel."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def clean_directories():
    """Clean build directories."""
    print("\n📦 Cleaning build directories...")
    dirs_to_clean = ["dist", "build", "app.egg-info", "clove.egg-info"]
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  ✓ Removed {dir_name}")


def check_node_installed():
    """Check if Node.js is installed."""
    try:
        result = run_command(["node", "--version"], check=False)
        if result.returncode == 0:
            print(f"  ✓ Node.js {result.stdout.strip()} detected")
            return True
    except FileNotFoundError:
        pass

    print("  ✗ Node.js not found. Please install Node.js to build the frontend.")
    return False


def check_pnpm_installed():
    """Check if pnpm is installed."""
    try:
        result = run_command(["pnpm", "--version"], check=False)
        if result.returncode == 0:
            print(f"  ✓ pnpm {result.stdout.strip()} detected")
            return True
    except FileNotFoundError:
        pass

    print("  ✗ pnpm not found. Installing pnpm...")
    run_command(["npm", "install", "-g", "pnpm"])
    return True


def build_frontend():
    """Build the frontend application."""
    print("\n🎨 Building frontend...")

    front_dir = Path("front")
    if not front_dir.exists():
        print("  ✗ Frontend directory not found")
        return False

    if not check_node_installed():
        return False

    if not check_pnpm_installed():
        return False

    if not (front_dir / "node_modules").exists():
        print("  📦 Installing frontend dependencies...")
        run_command(["pnpm", "install"], cwd=front_dir)

    print("  🔨 Building frontend assets...")
    run_command(["pnpm", "run", "build"], cwd=front_dir)

    print("  📂 Copying built files to app/static...")
    static_dir = Path("app/static")

    if static_dir.exists():
        shutil.rmtree(static_dir)

    shutil.copytree(front_dir / "dist", static_dir)
    print("  ✓ Frontend build complete")

    return True


def build_wheel():
    """Build the Python wheel."""
    print("\n🐍 Building Python wheel...")

    try:
        import build
    except ImportError:
        print("  📦 Installing build tool...")
        run_command([sys.executable, "-m", "pip", "install", "build"])

    run_command([sys.executable, "-m", "build", "--wheel"])

    dist_dir = Path("dist")
    if dist_dir.exists():
        wheels = list(dist_dir.glob("*.whl"))
        if wheels:
            print(f"  ✓ Created wheel: {wheels[0].name}")
            return True

    print("  ✗ Failed to create wheel")
    return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build script for Clove - builds frontend and creates Python wheel."
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend build and only build the Python wheel",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning build directories before building",
    )
    return parser.parse_args()


def main():
    """Main build process."""
    args = parse_args()

    print("🚀 Building Clove...")

    if not args.no_clean:
        clean_directories()

    if args.skip_frontend:
        print("\n⏭️  Frontend build skipped (--skip-frontend specified)")
        if not Path("app/static").exists():
            print(
                "⚠️  No static files found. The wheel will be built without frontend assets."
            )
            print(
                "   You may need to build the frontend separately or copy static files manually."
            )
    else:
        frontend_built = build_frontend()
        if not frontend_built:
            print("\n⚠️  Frontend build skipped. Using existing static files.")
            if not Path("app/static").exists():
                print(
                    "❌ No static files found. Please build frontend manually or ensure app/static exists."
                )
                sys.exit(1)

    if build_wheel():
        print("\n✅ Build complete!")
        print("\n📦 Installation instructions:")
        print("  1. Install the wheel:")
        print("     pip install dist/*.whl")
        print("  2. Run Clove:")
        print("     clove")
        print("\n📝 Note: You can also install in development mode:")
        print("     pip install -e .")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
