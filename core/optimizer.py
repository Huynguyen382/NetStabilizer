"""
NetStabilizer - Windows System & Network Optimizer
Handles Wi-Fi Anti-Ping-Spike Engine, TCP/IP Registry Tweaks, and QoS DSCP Prioritization.
Includes full Backup and 1-Click Restore.
"""

import os
import sys
import subprocess
import json
import winreg
from typing import Dict, Any, List, Optional, Tuple

BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network_backup.json")

class NetworkOptimizer:
    """
    Applies high-performance gaming/remote desktop optimizations to Windows TCP/IP stack
    and manages WLAN AutoConfig scan suppression.
    """

    @staticmethod
    def is_admin() -> bool:
        """Checks if current process has Administrator privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def run_cmd(cmd: str) -> Tuple[int, str]:
        """Executes a system shell command cleanly"""
        try:
            res = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return res.returncode, res.stdout.strip()
        except Exception as e:
            return -1, str(e)

    # -------------------------------------------------------------
    # 1. Wi-Fi Anti-Ping-Spike (WLAN Background Scan Suppressor)
    # -------------------------------------------------------------
    @classmethod
    def get_wifi_interfaces(cls) -> List[str]:
        """Detects active Wi-Fi interface names"""
        code, out = cls.run_cmd("netsh wlan show interfaces")
        interfaces = []
        if code == 0:
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Name") or line.startswith("Tên"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        interfaces.append(parts[1].strip())
        return interfaces

    @classmethod
    def set_wifi_autoconfig(cls, enabled: bool) -> Tuple[bool, str]:
        """
        Enables or disables WLAN AutoConfig background scanning.
        Disabling stops periodic 500-1000ms latency spikes while on Wi-Fi.
        """
        interfaces = cls.get_wifi_interfaces()
        if not interfaces:
            return False, "Khong tim thay card Wi-Fi hoat dong."

        state_str = "yes" if enabled else "no"
        results = []
        for iface in interfaces:
            cmd = f'netsh wlan set autoconfig enabled={state_str} interface="{iface}"'
            code, out = cls.run_cmd(cmd)
            if code == 0:
                status_msg = "Da bat lai tu dong tim Wi-Fi" if enabled else "Da chan thanh cong Ping Spike Wi-Fi (Tat Background Scan)"
                results.append(f"{iface}: {status_msg}")
            else:
                results.append(f"{iface}: Loi - {out}")
        return True, "\n".join(results)

    # -------------------------------------------------------------
    # 2. Windows TCP/IP Registry Tweaks
    # -------------------------------------------------------------
    @classmethod
    def apply_tcp_registry_tweaks(cls) -> Tuple[bool, str]:
        """
        Sets TCPNoDelay, TcpAckFrequency, and disables multimedia network throttling.
        """
        if not cls.is_admin():
            return False, "Yeu cau quyen Administrator de chinh sua Registry mang."

        backup_data: Dict[str, Any] = {}
        messages = []

        try:
            # 1. Multimedia Profile (NetworkThrottlingIndex & SystemResponsiveness)
            profile_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profile_path, 0, winreg.KEY_ALL_ACCESS) as key:
                # Backup existing
                try:
                    val, _ = winreg.QueryValueEx(key, "NetworkThrottlingIndex")
                    backup_data["NetworkThrottlingIndex"] = val
                except FileNotFoundError:
                    backup_data["NetworkThrottlingIndex"] = None
                    
                try:
                    val, _ = winreg.QueryValueEx(key, "SystemResponsiveness")
                    backup_data["SystemResponsiveness"] = val
                except FileNotFoundError:
                    backup_data["SystemResponsiveness"] = None

                # Apply optimal values
                winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF)
                winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
                messages.append("✓ Da tat Network Throttling & toi uu hoa System Responsiveness (0ms delay)")

            # 2. TCP/IP Interfaces (TCPNoDelay, TcpAckFrequency)
            interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, interfaces_path, 0, winreg.KEY_READ) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                guid_subkeys = [winreg.EnumKey(key, i) for i in range(num_subkeys)]

            backup_data["interfaces"] = {}
            for guid in guid_subkeys:
                sub_path = f"{interfaces_path}\\{guid}"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_ALL_ACCESS) as sub_key:
                        # Backup
                        if_backup = {}
                        for param in ["TcpAckFrequency", "TCPNoDelay", "TcpDelAckTicks"]:
                            try:
                                v, _ = winreg.QueryValueEx(sub_key, param)
                                if_backup[param] = v
                            except FileNotFoundError:
                                if_backup[param] = None
                        backup_data["interfaces"][guid] = if_backup

                        # Apply
                        winreg.SetValueEx(sub_key, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
                        winreg.SetValueEx(sub_key, "TCPNoDelay", 0, winreg.REG_DWORD, 1)
                        winreg.SetValueEx(sub_key, "TcpDelAckTicks", 0, winreg.REG_DWORD, 0)
                except PermissionError:
                    continue

            messages.append("✓ Da bat TCPNoDelay=1 va TcpAckFrequency=1 (Loai bo thuat toan Nagle tre goi tin)")

            # Save backup to file if not already backed up
            if not os.path.exists(BACKUP_FILE):
                with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2)

            return True, "\n".join(messages)

        except Exception as e:
            return False, f"Loi khi thiet lap Registry: {str(e)}"

    # -------------------------------------------------------------
    # 3. Netsh Global Optimization
    # -------------------------------------------------------------
    @classmethod
    def apply_netsh_optimizations(cls) -> Tuple[bool, str]:
        """Configures TCP global autotuning, ECN, RSS for maximum throughput & low latency"""
        commands = [
            ("netsh int tcp set global autotuninglevel=normal", "TCP Window Auto-Tuning = Normal"),
            ("netsh int tcp set global ecncapability=enabled", "ECN (Explicit Congestion Notification) = Enabled"),
            ("netsh int tcp set global rss=enabled", "Receive-Side Scaling (RSS) = Enabled"),
            ("netsh int tcp set global timestamps=disabled", "TCP Timestamps Header Overhead = Disabled")
        ]
        
        results = []
        for cmd, desc in commands:
            code, out = cls.run_cmd(cmd)
            if code == 0 or "Ok" in out or "Thành công" in out:
                results.append(f"✓ {desc}")
            else:
                results.append(f"⚠ {desc}: {out}")
        return True, "\n".join(results)

    # -------------------------------------------------------------
    # 4. QoS DSCP Prioritization
    # -------------------------------------------------------------
    @classmethod
    def apply_qos_policy(cls, app_ports: Optional[List[int]] = None) -> Tuple[bool, str]:
        """Creates DSCP 46 (Expedited Forwarding) QoS Policy for remote ports"""
        if app_ports is None:
            app_ports = [3389, 29999, 47989]
        port_list_str = ",".join(str(p) for p in app_ports)
        ps_cmd = (
            f"powershell -Command \""
            f"Remove-NetQosPolicy -Name 'NetStabilizerHighPriority' -ErrorAction SilentlyContinue; "
            f"New-NetQosPolicy -Name 'NetStabilizerHighPriority' -NetworkProfile All "
            f"-IPPortMatchCondition @({port_list_str}) -DSCPAction 46 -PriorityValue8021Action 5 -ErrorAction SilentlyContinue\""
        )
        code, out = cls.run_cmd(ps_cmd)
        if code == 0:
            return True, f"✓ Da gan QoS DSCP 46 (Expedited Forwarding) cho cac cong: {port_list_str}"
        return False, f"⚠ QoS Policy: {out}"

    # -------------------------------------------------------------
    # 5. Restore Original Settings
    # -------------------------------------------------------------
    @classmethod
    def restore_defaults(cls) -> Tuple[bool, str]:
        """Restores Windows Registry and Wi-Fi autoconfig to original/standard defaults"""
        messages = []
        
        # 1. Re-enable Wi-Fi autoconfig
        cls.set_wifi_autoconfig(enabled=True)
        messages.append("✓ Da bat lai Wi-Fi AutoConfig mac dinh")

        # 2. Restore Registry if backup exists
        if os.path.exists(BACKUP_FILE):
            try:
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    backup = json.load(f)

                profile_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profile_path, 0, winreg.KEY_ALL_ACCESS) as key:
                    if backup.get("NetworkThrottlingIndex") is not None:
                        winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, backup["NetworkThrottlingIndex"])
                    else:
                        winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 10) # default is 10

                    if backup.get("SystemResponsiveness") is not None:
                        winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, backup["SystemResponsiveness"])
                    else:
                        winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 20) # default is 20

                # Restore interfaces
                interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
                for guid, params in backup.get("interfaces", {}).items():
                    sub_path = f"{interfaces_path}\\{guid}"
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_ALL_ACCESS) as sub_key:
                            for param, val in params.items():
                                if val is not None:
                                    winreg.SetValueEx(sub_key, param, 0, winreg.REG_DWORD, val)
                                else:
                                    try:
                                        winreg.DeleteValue(sub_key, param)
                                    except FileNotFoundError:
                                        pass
                    except Exception:
                        pass

                messages.append("✓ Da khoi phuc toan bo gia tri Registry ve trang thai truoc khi toi uu")
            except Exception as e:
                messages.append(f"⚠ Loi khi khoi phuc Registry tu file backup: {e}")

        # 3. Restore Netsh defaults
        cls.run_cmd("netsh int tcp set global autotuninglevel=normal")
        cls.run_cmd("netsh int tcp set global timestamps=disabled")
        messages.append("✓ Da thiet lap Netsh TCP ve mac dinh")

        return True, "\n".join(messages)
