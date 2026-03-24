import subprocess


def ssh_cmd(profile, user, ip, password, cmd):
    ssh_binary = profile.get("ssh.binary", "ssh")
    ssh_options = profile.get_list("ssh.connect_options", [])
    ssh_target = profile.get("ssh.target", "{user}@{ip}").format(
        user=user,
        ip=ip
    )

    result = subprocess.run(
        [
            "sshpass",
            "-p", password,
            ssh_binary,
            *ssh_options,
            ssh_target,
            cmd
        ],
        capture_output=True,
        text=True
    )

    return result.stdout.strip() or "Unknown"


def get_dut_info(profile, user, ip, password):
    hostname_cmd = profile.get("dut_info.hostname_command", "hostname")
    os_release_cmd = profile.get(
        "dut_info.os_release_command",
        "cat /etc/os-release"
    )
    os_hash_cmd = profile.get(
        "dut_info.os_hash_command",
        "sha256sum /etc/os-release 2>/dev/null | awk '{print $1}'"
    )
    config_hash_cmd = profile.get(
        "dut_info.config_hash_command",
        "sha256sum /etc/ssh/sshd_config 2>/dev/null | awk '{print $1}'"
    )

    hostname = ssh_cmd(profile, user, ip, password, hostname_cmd)
    os_release = ssh_cmd(profile, user, ip, password, os_release_cmd)
    os_hash = ssh_cmd(profile, user, ip, password, os_hash_cmd)
    config_hash = ssh_cmd(profile, user, ip, password, config_hash_cmd)

    version = "Unknown"
    for line in os_release.splitlines():
        if line.startswith("PRETTY_NAME="):
            version = line.split("=", 1)[1].strip().strip('"')
            break

    return {
        "dut_name": hostname if hostname else "Unknown",
        "dut_version": version,
        "os_hash": os_hash if os_hash else "Unknown",
        "config_hash": config_hash if config_hash else "Unknown"
    }