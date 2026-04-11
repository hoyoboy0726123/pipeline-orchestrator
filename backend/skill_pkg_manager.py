"""
Skill 套件管理器 — 管理 AI技能節點可用的 Python 第三方套件
"""
import subprocess
import sys
from pathlib import Path

_PKG_FILE = Path(__file__).parent / "skill_packages.txt"


def _read_packages() -> list[str]:
    """讀取 skill_packages.txt，回傳套件名清單（忽略空行和註解）"""
    if not _PKG_FILE.exists():
        return []
    lines = _PKG_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def _write_packages(packages: list[str]) -> None:
    """寫入套件清單到 skill_packages.txt（保留 header 註解）"""
    header = (
        "# AI技能節點可用的 Python 套件\n"
        "# 後端啟動時自動安裝缺少的套件到本專案 venv\n"
        "# 可透過管理介面新增或移除\n\n"
    )
    _PKG_FILE.write_text(header + "\n".join(packages) + "\n", encoding="utf-8")


def _is_installed(pkg_name: str) -> bool:
    """檢查套件是否已安裝"""
    # 套件名可能有 extras (e.g. "uvicorn[standard]") 或版本 (e.g. "pandas==2.0")
    # 只取基礎名稱
    base = pkg_name.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", base],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _pip_install(pkg_name: str) -> tuple[bool, str]:
    """安裝單一套件，回傳 (成功, 訊息)"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name, "-q"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, f"✅ {pkg_name} 安裝成功"
        return False, f"❌ {pkg_name} 安裝失敗：{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"❌ {pkg_name} 安裝逾時"
    except Exception as e:
        return False, f"❌ {pkg_name} 安裝錯誤：{e}"


def _pip_uninstall(pkg_name: str) -> tuple[bool, str]:
    """移除單一套件"""
    base = pkg_name.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", base, "-y", "-q"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return True, f"✅ {base} 已移除"
        return False, f"❌ {base} 移除失敗：{result.stderr.strip()}"
    except Exception as e:
        return False, f"❌ {base} 移除錯誤：{e}"


def auto_install_packages() -> None:
    """後端啟動時自動安裝缺少的套件"""
    packages = _read_packages()
    if not packages:
        return
    missing = [p for p in packages if not _is_installed(p)]
    if not missing:
        print(f"✅ Skill 套件全部已安裝（{len(packages)} 個）")
        return
    print(f"📦 正在安裝缺少的 Skill 套件：{', '.join(missing)}")
    for pkg in missing:
        ok, msg = _pip_install(pkg)
        print(f"  {msg}")


def list_packages() -> list[dict]:
    """列出所有 skill 套件及安裝狀態"""
    packages = _read_packages()
    result = []
    for pkg in packages:
        base = pkg.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
        installed = _is_installed(pkg)
        # 取得版本
        version = ""
        if installed:
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "show", base],
                    capture_output=True, text=True, timeout=10,
                )
                for line in r.stdout.splitlines():
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
            except Exception:
                pass
        result.append({
            "name": pkg,
            "installed": installed,
            "version": version,
        })
    return result


def add_package(pkg_name: str) -> tuple[bool, str]:
    """新增套件：安裝 + 寫入清單"""
    pkg_name = pkg_name.strip()
    if not pkg_name:
        return False, "套件名稱不能為空"

    packages = _read_packages()
    base = pkg_name.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower()

    # 檢查是否已在清單中
    for p in packages:
        existing_base = p.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower()
        if existing_base == base:
            return False, f"{pkg_name} 已在清單中"

    # 先安裝
    ok, msg = _pip_install(pkg_name)
    if not ok:
        return False, msg

    # 寫入清單
    packages.append(pkg_name)
    _write_packages(packages)
    return True, msg


def remove_package(pkg_name: str) -> tuple[bool, str]:
    """移除套件：從清單移除 + 解除安裝"""
    pkg_name = pkg_name.strip()
    packages = _read_packages()
    base = pkg_name.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower()

    # 從清單中移除
    new_packages = []
    found = False
    for p in packages:
        existing_base = p.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower()
        if existing_base == base:
            found = True
        else:
            new_packages.append(p)

    if not found:
        return False, f"{pkg_name} 不在清單中"

    # 解除安裝
    _pip_uninstall(pkg_name)

    # 更新清單
    _write_packages(new_packages)
    return True, f"✅ {pkg_name} 已從清單移除並解除安裝"
