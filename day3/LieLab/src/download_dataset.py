"""Download official archive or safely extract a manually supplied ZIP."""

import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from .common import config, parser


def acquire(c, archive=None):
    dest = c["paths"]["raw"]
    archive = Path(archive).resolve() if archive else dest / "dataset.zip"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        try:
            with urllib.request.urlopen(
                c["dataset_url"], timeout=30
            ) as r, partial.open("wb") as f:
                shutil.copyfileobj(r, f)
            partial.replace(archive)
        except Exception as e:
            partial.unlink(missing_ok=True)
            try:
                # System curl uses the platform certificate store; TLS validation stays enabled.
                subprocess.run(
                    [
                        "curl",
                        "-fL",
                        "--retry",
                        "2",
                        "--connect-timeout",
                        "30",
                        "--max-time",
                        "300",
                        c["dataset_url"],
                        "-o",
                        str(partial),
                    ],
                    check=True,
                )
                partial.replace(archive)
            except (OSError, subprocess.SubprocessError) as fallback:
                partial.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Download failed: {e}; {fallback}. Supply --zip /path/dataset.zip"
                ) from fallback
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            target = (dest / item.filename).resolve()
            if (
                not target.is_relative_to(dest.resolve())
                or (item.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe archive member: " + item.filename)
        z.extractall(dest)
    print(f"Extracted to {dest}. Review included terms/README before use.")


def main():
    p = parser(__doc__)
    p.add_argument("--zip")
    a = p.parse_args()
    acquire(config(a.config), a.zip)


if __name__ == "__main__":
    main()
