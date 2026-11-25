"""Lambda 用の Linux バイナリを含む ZIP を生成する。AWS には接続しない。"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    root = Path(__file__).resolve().parent
    destination = root / "dist" / "image_compression.zip"
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="image-compression-") as temporary:
        package = Path(temporary) / "package"
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--disable-pip-version-check", "--no-cache-dir", "--no-compile",
                "--platform", "manylinux_2_28_x86_64",
                "--platform", "manylinux2014_x86_64",
                "--implementation", "cp", "--python-version", "3.13",
                "--only-binary=:all:", "--target", str(package),
                "-r", str(root / "requirements.txt"),
            ],
            check=True,
        )
        shutil.copy2(root / "handler.py", package / "handler.py")
        archive = Path(temporary) / "image_compression.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path in sorted(package.rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                info = zipfile.ZipInfo(path.relative_to(package).as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, path.read_bytes())
        shutil.copyfile(archive, destination)
    print(f"Lambda ZIP: {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
