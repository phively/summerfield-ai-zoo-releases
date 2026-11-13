from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any


def _is_windows() -> bool:
    return os.name == "nt"


def _is_link(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def path_has_link(path: Path) -> bool:
    absolute = path.expanduser().absolute()
    return any(_is_link(part) for part in reversed((absolute, *absolute.parents)))


def acl_is_private(acl: Any) -> bool:
    if not isinstance(acl, dict) or not isinstance(acl.get("current_sid"), str):
        return False
    owner = acl["current_sid"]
    rules = acl.get("rules")
    if acl.get("owner_sid") != owner or not isinstance(rules, list) or not rules:
        return False
    owner_sids = {owner, "S-1-3-4"}
    allowed = owner_sids | {"S-1-5-18", "S-1-5-32-544"}
    owner_access = False
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("type") not in {"Allow", "Deny"}:
            return False
        if rule["type"] == "Allow":
            if rule.get("sid") not in allowed:
                return False
            owner_access |= rule["sid"] in owner_sids
    return owner_access


def _windows_acl(path: Path) -> Any:
    script = (
        "$ErrorActionPreference='Stop';"
        "$a=Get-Acl -LiteralPath $env:SHOPPING_PERMISSION_PATH;"
        "$s=[System.Security.Principal.SecurityIdentifier];"
        "$u=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$r=@($a.GetAccessRules($true,$true,$s)|ForEach-Object {"
        "@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString()}});"
        "@{current_sid=$u;owner_sid=$a.GetOwner($s).Value;rules=$r}|ConvertTo-Json -Depth 4 -Compress"
    )
    environment = dict(os.environ)
    environment["SHOPPING_PERMISSION_PATH"] = str(path.resolve(strict=True))
    executable = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
        env=environment, capture_output=True, text=True, check=True, timeout=10,
    )
    return json.loads(result.stdout)


def _set_windows_permissions(path: Path) -> bool:
    script = (
        "$ErrorActionPreference='Stop';"
        "$path=$env:SHOPPING_PERMISSION_PATH;"
        "$owner=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$acl=Get-Acl -LiteralPath $path;"
        "$acl.SetAccessRuleProtection($true,$false);"
        "foreach($rule in @($acl.Access)){[void]$acl.RemoveAccessRuleSpecific($rule)};"
        "$acl.SetOwner($owner);"
        "$rights=[System.Security.AccessControl.FileSystemRights]::FullControl;"
        "$inherit=[System.Security.AccessControl.InheritanceFlags]::None;"
        "$item=Get-Item -LiteralPath $path;"
        "if($item.PSIsContainer){$inherit=[System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit};"
        "$prop=[System.Security.AccessControl.PropagationFlags]::None;"
        "$allow=[System.Security.AccessControl.AccessControlType]::Allow;"
        "$sids=@($owner.Value,'S-1-3-4','S-1-5-18','S-1-5-32-544')|Select-Object -Unique;"
        "foreach($value in $sids){$sid=[System.Security.Principal.SecurityIdentifier]::new($value);"
        "$rule=[System.Security.AccessControl.FileSystemAccessRule]::new($sid,$rights,$inherit,$prop,$allow);"
        "[void]$acl.AddAccessRule($rule)};"
        "Set-Acl -LiteralPath $path -AclObject $acl"
    )
    try:
        environment = dict(os.environ)
        environment["SHOPPING_PERMISSION_PATH"] = str(path.resolve(strict=True))
        executable = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        subprocess.run(
            [str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
            env=environment, capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, KeyError, subprocess.SubprocessError):
        return False
    return True


def private_permissions(path: Path) -> bool:
    try:
        if _is_windows():
            return acl_is_private(_windows_acl(path))
        return not stat.S_IMODE(path.stat().st_mode) & 0o077
    except (OSError, KeyError, subprocess.SubprocessError, json.JSONDecodeError):
        return False


def private_file(path: Path) -> bool:
    return not path_has_link(path) and path.is_file() and private_permissions(path)


def private_directory(path: Path) -> bool:
    return not path_has_link(path) and path.is_dir() and private_permissions(path)


def _make_private(path: Path) -> None:
    if _is_windows():
        if not _set_windows_permissions(path) or not private_permissions(path):
            raise PermissionError("cannot establish private permissions for browser evidence")
        return
    os.chmod(path, 0o700)
    if not private_permissions(path):
        raise PermissionError("cannot establish private permissions for browser evidence")


def ensure_private_directory(path: Path, *, require_new: bool = False) -> Path:
    path = path.expanduser().absolute()
    if path_has_link(path):
        raise ValueError("browser evidence paths must not be symlinked")
    if path.exists():
        if require_new:
            raise FileExistsError("private evidence directory must be new")
        if not private_directory(path):
            raise ValueError("browser evidence directory permissions are not private")
        return path
    parent = path.parent
    if not parent.exists():
        ensure_private_directory(parent)
    elif not parent.is_dir() or path_has_link(parent):
        raise ValueError("browser evidence parent must be a real directory")
    path.mkdir(mode=0o700)
    try:
        _make_private(path)
        if not private_directory(path):
            raise PermissionError("cannot establish private permissions for browser evidence")
    except Exception:
        try:
            path.rmdir()
        except OSError:
            pass
        raise
    return path


def write_private_file(path: Path, content: bytes) -> Path:
    path = path.expanduser().absolute()
    if path_has_link(path):
        raise ValueError("browser evidence paths must not be symlinked")
    if path.exists():
        raise FileExistsError("browser capture sidecar already exists")
    if not private_directory(path.parent):
        raise PermissionError("browser evidence directory permissions are not private")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    created = True
    try:
        if _is_windows():
            if not _set_windows_permissions(path) or not private_permissions(path):
                raise PermissionError("cannot establish private permissions for browser evidence")
        else:
            os.fchmod(descriptor, 0o600)
            if not private_file(path):
                raise PermissionError("cannot establish private permissions for browser evidence")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        if created:
            try:
                path.unlink()
            except OSError:
                pass
        raise
    return path
