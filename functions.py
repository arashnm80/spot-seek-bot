from variables import *
import subprocess
import sys
import requests
from log import *
import shutil
import telebot
import asyncio

def get_single_mp3(directory):
    mp3_files = [f for f in os.listdir(directory) if f.endswith('.mp3')]
    if len(mp3_files) == 1:
        return mp3_files[0]
    elif len(mp3_files) == 0:
        raise FileNotFoundError("no .mp3 file was found.")
    else:
        raise RuntimeError("more than one .mp3 file was found.")

def clear_files(folder_path):
    for name in os.listdir(folder_path):
        if name == ".gitkeep":
            continue  # ne pas toucher à .gitkeep

        path = os.path.join(folder_path, name)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
                print(f"Deleted file: {name}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Deleted folder: {name}")
        except Exception as e:
            print(f"Error deleting {name}: {e}")

# experimental - to see if has effect on spotdl rate limits
def delete_spotdl_cache():
    # Path to the directory
    directory = spotdl_cache_path

    # Check if the directory exists and remove it
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f'{directory} has been removed.')
    else:
        print(f'{directory} does not exist.')

def delete_yt_dlp_cache():
    # Path to the directory
    directory = yt_dlp_cache_path

    # Check if the directory exists and remove it
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f'{directory} has been removed.')
    else:
        print(f'{directory} does not exist.')

def get_spotdl_download_env():
    """PATH for proxychains+spotDL: repo .venv/bin (spotdl + Deno) then system Deno."""
    env = os.environ.copy()
    extra = []
    venv_bin = os.path.join(spotdl_venv_dir, "bin")
    if os.path.isdir(venv_bin):
        extra.append(venv_bin)
    if os.path.isdir(system_deno_dir):
        extra.append(system_deno_dir)
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def _ensure_repo_deno():
    """Install Deno into .venv/bin. ~/.spotdl is wiped each download, so do not keep Deno only there.
    CLI `spotdl --download-deno` prompts if Deno is already on PATH; use the library instead.
    Do not fail the bot if download needs network and system Deno exists."""
    venv_bin = os.path.join(spotdl_venv_dir, "bin")
    venv_python = os.path.join(venv_bin, "python")
    dest = os.path.join(venv_bin, "deno")
    os.makedirs(venv_bin, exist_ok=True)

    if os.path.isfile(dest) and os.access(dest, os.X_OK):
        print(f"Deno already at {dest}")
        return

    downloaded = None
    try:
        result = subprocess.run(
            [
                venv_python,
                "-c",
                "from spotdl.utils.deno import download_deno; print(download_deno())",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            downloaded = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
            print(f"spotdl downloaded Deno to {downloaded}")
        else:
            print(f"spotdl Deno download failed: {result.stderr.strip() or result.stdout.strip()}")
    except Exception as e:
        print(f"spotdl Deno download skipped/failed: {e}")

    sources = []
    if downloaded:
        sources.append(downloaded)
    sources.extend([
        os.path.join(os.path.expanduser("~"), ".config", "spotdl", "deno"),
        os.path.join(os.path.expanduser("~"), ".spotdl", "deno"),
        os.path.join(system_deno_dir, "deno"),
    ])
    for src in sources:
        if src and os.path.isfile(src) and os.access(src, os.X_OK):
            try:
                os.link(src, dest)
            except OSError:
                shutil.copy2(src, dest)
            os.chmod(dest, 0o755)
            print(f"Deno available at {dest} (from {src})")
            return

    if os.path.isfile(os.path.join(system_deno_dir, "deno")):
        print(f"Using system Deno at {system_deno_dir}/deno")
    else:
        print("Warning: Deno not found; yt-dlp bestaudio may 403 under proxychains")


def setup_spotdl_executable():
    """Ensure in-repo .venv has pip spotdl + yt-dlp. Does not wget the GitHub ELF or download music."""
    venv_python = os.path.join(spotdl_venv_dir, "bin", "python")
    venv_pip = os.path.join(spotdl_venv_dir, "bin", "pip")

    try:
        if not os.path.isfile(venv_python):
            print(f"Creating spotdl venv at {spotdl_venv_dir}")
            subprocess.run([sys.executable, "-m", "venv", spotdl_venv_dir], check=True)

        packages_ok = False
        if os.path.isfile(venv_python):
            probe = subprocess.run(
                [venv_python, "-c", "import spotdl, yt_dlp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            packages_ok = probe.returncode == 0

        if not packages_ok:
            print("Installing spotdl + yt-dlp into in-repo venv")
            subprocess.run([venv_pip, "install", "-U", "pip"], check=True)
            if os.path.isfile(spotdl_requirements_file):
                subprocess.run([venv_pip, "install", "-r", spotdl_requirements_file], check=True)
            else:
                subprocess.run(
                    [venv_pip, "install", "spotdl", "yt-dlp[default,curl-cffi]"],
                    check=True,
                )
        print(f"spotdl ready at {spotdl_bin}")
    except Exception as e:
        print(f"Failed to ensure spotdl venv: {e}")
        raise

    _ensure_repo_deno()

async def do_with_retry(send_func, *args, **kwargs):
    """
    Calls a Telegram function (like send_message, send_photo, send_media_group, etc.)
    and automatically handles 429 errors with retry_after.
    """
    try:
        return await send_func(*args, **kwargs)
    except telebot.asyncio_helper.ApiTelegramException as e:
        if e.error_code == 429:
            # extract retry_after from description
            retry_after = int(e.description.split("retry after ")[1])
            print(f"[!] Rate limit reached, waiting {retry_after} sec")
            await asyncio.sleep(retry_after)
            return await send_func(*args, **kwargs)
        else:
            raise