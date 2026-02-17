#!/usr/bin/env python3
"""
PaxD Improved - Modern Package Manager with Rich UI
Enhanced version of PaxD with beautiful command line interface using Rich
"""

__name__ = "PaxD Improved"
__author__ = "mralfiem591"
__license__ = "MIT"
__version__ = "1.0.0"

import os
import sys
import json
import requests
import yaml
import argparse
import shutil
import stat
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Rich imports for beautiful UI
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich.layout import Layout
from rich.padding import Padding

# Initialize Rich console
console = Console()

class PaxDImproved:
    """Improved PaxD package manager with Rich UI"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.version = "1.0.0"
        self.version_phrase = "The Rich Experience Update"
        self.repository_file = os.path.join(os.path.dirname(__file__), "repository")
        self.local_app_data = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "PaxD")
        self.headers = {'User-Agent': 'PaxD-Improved/1.0.0'}
        
        # Ensure PaxD directory exists
        os.makedirs(self.local_app_data, exist_ok=True)
    
    def log_verbose(self, message: str):
        """Log verbose messages if verbose mode is enabled"""
        if self.verbose:
            console.print(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] [blue]DEBUG[/blue] {message}")
    
    def show_welcome(self):
        """Display welcome message with Rich formatting"""
        title_text = Text("PaxD Improved", style="bold magenta")
        subtitle_text = Text("Modern Package Manager with Beautiful Interface", style="italic cyan")
        
        welcome_panel = Panel(
            Align.center(f"{title_text}\n{subtitle_text}\n\nVersion {self.version}: {self.version_phrase}"),
            border_style="magenta",
            padding=(1, 2)
        )
        console.print(welcome_panel)
    
    def _read_repository_url(self) -> str:
        """Read repository URL from repository file"""
        self.log_verbose(f"Reading repository file: {self.repository_file}")
        
        if not os.path.exists(self.repository_file):
            console.print("[red]Repository file not found![/red]")
            raise FileNotFoundError("Repository file not found")
        
        with open(self.repository_file, 'r') as f:
            url = f.read().strip()
        
        self.log_verbose(f"Repository URL: {url}")
        return url
    
    def _resolve_repository_url(self, repo_url: str) -> str:
        """Resolve repository URL, handling optimised:: prefix"""
        if repo_url.startswith("optimised::"):
            return repo_url[11:]  # Remove optimised:: prefix
        return repo_url
    
    def _fetch_with_progress(self, url: str, description: str) -> requests.Response:
        """Fetch URL with a progress spinner"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(description, total=None)
            try:
                response = requests.get(url, headers=self.headers, allow_redirects=True)
                response.raise_for_status()
                return response
            except Exception as e:
                console.print(f"[red]Failed to fetch {url}: {e}[/red]")
                raise
    
    def _parse_jsonc(self, jsonc_text: str) -> dict:
        """Parse JSONC (JSON with comments) by removing comments"""
        lines = jsonc_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Find // that's not inside a string
            in_string = False
            escaped = False
            comment_pos = None
            
            for i, char in enumerate(line):
                if escaped:
                    escaped = False
                    continue
                if char == '\\':
                    escaped = True
                elif char == '"' and not escaped:
                    in_string = not in_string
                elif not in_string and char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    comment_pos = i
                    break
            
            if comment_pos is not None:
                cleaned_lines.append(line[:comment_pos].rstrip())
            else:
                cleaned_lines.append(line)
        
        cleaned_json = '\n'.join(cleaned_lines)
        return json.loads(cleaned_json)
    
    def _fetch_package_metadata(self, repo_url: str, package_name: str) -> Tuple[dict, str]:
        """Fetch package metadata, trying YAML first, then JSONC"""
        # Try package.yaml first
        yaml_url = f"{repo_url}/packages/{package_name}/package.yaml"
        
        try:
            response = self._fetch_with_progress(yaml_url, f"Fetching {package_name} metadata...")
            yaml_data = yaml.safe_load(response.text)
            return self._compile_paxd_manifest(yaml_data), "package.yaml"
        except Exception:
            pass
        
        # Try paxd.yaml
        yaml_url2 = f"{repo_url}/packages/{package_name}/paxd.yaml"
        try:
            response = self._fetch_with_progress(yaml_url2, f"Fetching {package_name} metadata...")
            yaml_data = yaml.safe_load(response.text)
            return self._compile_paxd_manifest(yaml_data), "paxd.yaml"
        except Exception:
            pass
        
        # Try legacy paxd JSONC
        package_url = f"{repo_url}/packages/{package_name}/paxd"
        try:
            response = self._fetch_with_progress(package_url, f"Fetching {package_name} metadata...")
            return self._parse_jsonc(response.text), "paxd"
        except Exception:
            pass
        
        console.print(f"[red]Package '{package_name}' not found in repository[/red]")
        raise Exception(f"Package {package_name} not found")
    
    def _compile_paxd_manifest(self, yaml_data: dict) -> dict:
        """Convert YAML data to PaxD manifest format"""
        required_fields = ["name", "author", "version", "description", "license"]
        for field in required_fields:
            if field not in yaml_data:
                raise ValueError(f"Missing required field: {field}")
        
        manifest = {
            "pkg_info": {
                "pkg_name": yaml_data["name"],
                "pkg_author": yaml_data["author"],
                "pkg_version": yaml_data["version"],
                "pkg_description": yaml_data["description"],
                "pkg_license": yaml_data["license"],
                "tags": yaml_data.get("tags", [])
            },
            "install": {}
        }
        
        install_config = yaml_data.get("install", {})
        
        if "files" in install_config:
            manifest["install"]["include"] = install_config["files"]
        
        if "dependencies" in install_config:
            deps = []
            dep_config = install_config["dependencies"]
            
            if "pip" in dep_config:
                for pkg in dep_config["pip"]:
                    deps.append(f"pip:{pkg}")
            
            if "paxd" in dep_config:
                for pkg in dep_config["paxd"]:
                    deps.append(f"paxd:{pkg}")
            
            if deps:
                manifest["install"]["depend"] = deps
        
        # Handle other install settings
        for setting in ["firstrun", "updaterun", "oneshot"]:
            if setting in install_config:
                manifest["install"][setting] = install_config[setting]
        
        if "main_executable" in install_config:
            manifest["install"]["mainfile"] = install_config["main_executable"]
        
        if "command_alias" in install_config:
            manifest["install"]["alias"] = install_config["command_alias"]
        
        if "checksum" in install_config:
            manifest["install"]["checksum"] = install_config["checksum"]
        
        return manifest
    
    def _calculate_file_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate checksum for a file"""
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def _verify_checksum_with_retry(self, file_path: str, expected_checksum: str, max_retries: int = 4) -> bool:
        """Verify file checksum with exponential backoff retry"""
        algorithm, expected_hash = expected_checksum.split(':', 1)
        
        for attempt in range(max_retries):
            try:
                actual_hash = self._calculate_file_checksum(file_path, algorithm)
                if actual_hash == expected_hash:
                    self.log_verbose(f"Checksum verified for {os.path.basename(file_path)}: {expected_checksum}")
                    return True
                else:
                    self.log_verbose(f"Checksum mismatch for {os.path.basename(file_path)}: expected {expected_hash}, got {actual_hash}")
                    
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 0.5  # Exponential backoff: 0.5s, 1s, 2s, 4s
                        console.print(f"[yellow]Checksum verification failed for {os.path.basename(file_path)}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})[/yellow]")
                        time.sleep(wait_time)
                    else:
                        console.print(f"[red]Checksum verification failed for {os.path.basename(file_path)} after {max_retries} attempts[/red]")
                        return False
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    console.print(f"[yellow]Error calculating checksum for {os.path.basename(file_path)}: {e}, retrying in {wait_time}s...[/yellow]")
                    time.sleep(wait_time)
                else:
                    console.print(f"[red]Failed to calculate checksum for {os.path.basename(file_path)}: {e}[/red]")
                    return False
        
        return False
    
    def _download_and_verify_file(self, file_url: str, local_file_path: str, expected_checksum: Optional[str] = None, skip_checksum: bool = False) -> bool:
        """Download file and verify checksum with atomic operation"""
        temp_file_path = local_file_path + ".tmp"
        
        try:
            # Download to temporary file
            response = requests.get(file_url, headers=self.headers)
            response.raise_for_status()
            
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            # Verify checksum if provided and not skipped
            if expected_checksum and not skip_checksum:
                if not self._verify_checksum_with_retry(temp_file_path, expected_checksum):
                    # Remove temporary file on failure
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    return False
            
            # Atomic move: rename temp file to final location
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            os.rename(temp_file_path, local_file_path)
            
            return True
            
        except Exception as e:
            # Clean up temp file on any error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            console.print(f"[red]Failed to download {os.path.basename(local_file_path)}: {e}[/red]")
            return False
    
    def install(self, package_name: str, skip_checksum: bool = False):
        """Install a package with beautiful progress display"""
        # Block installation of original PaxD client
        if package_name == "com.mralfiem591.paxd":
            console.print("[red]Installation of the original PaxD client via PaxD Improved is blocked.[/red]")
            console.print("[yellow]This prevents potential conflicts between the two package managers.[/yellow]")
            console.print("[cyan]Use the original PaxD client or the 'switchback' command if needed.[/cyan]")
            return
            
        console.print(f"\n[bold cyan]Installing package: [yellow]{package_name}[/yellow][/bold cyan]")
        
        try:
            # Read and resolve repository URL
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            
            # Validate repository
            paxd_url = f"{repo_url}/paxd"
            self._fetch_with_progress(paxd_url, "Validating repository...")
            
            # Check if already installed
            package_install_path = os.path.join(self.local_app_data, package_name)
            if os.path.exists(package_install_path):
                if not Confirm.ask(f"[yellow]Package '{package_name}' is already installed. Reinstall?[/yellow]"):
                    console.print("[yellow]Installation cancelled[/yellow]")
                    return
                
                # Remove existing installation
                self.log_verbose(f"Removing existing installation: {package_install_path}")
                shutil.rmtree(package_install_path)
            
            # Fetch package metadata
            package_data, source_file = self._fetch_package_metadata(repo_url, package_name)
            pkg_info = package_data.get('pkg_info', {})
            
            # Display package info
            info_table = Table(show_header=False, box=None)
            info_table.add_row("[bold]Name:[/bold]", pkg_info.get('pkg_name', package_name))
            info_table.add_row("[bold]Author:[/bold]", pkg_info.get('pkg_author', 'Unknown'))
            info_table.add_row("[bold]Version:[/bold]", pkg_info.get('pkg_version', 'Unknown'))
            info_table.add_row("[bold]Description:[/bold]", pkg_info.get('pkg_description', 'No description'))
            
            package_panel = Panel(
                info_table,
                title="[bold green]Package Information[/bold green]",
                border_style="green"
            )
            console.print(package_panel)
            
            # Install dependencies
            deps = package_data.get("install", {}).get("depend", [])
            if deps:
                console.print(f"\n[bold blue]Installing {len(deps)} dependencies...[/bold blue]")
                for dep in deps:
                    if dep.startswith("pip:"):
                        pip_pkg = dep[4:]
                        console.print(f"[dim]  Installing pip package: {pip_pkg}[/dim]")
                        os.system(f"pip install {pip_pkg} -q")
                    elif dep.startswith("paxd:"):
                        paxd_pkg = dep[5:]
                        if not self.is_installed(paxd_pkg):
                            console.print(f"[dim]  Installing PaxD package: {paxd_pkg}[/dim]")
                            self.install(paxd_pkg, skip_checksum)
            
            # Install files with checksum verification
            include_files = package_data.get("install", {}).get("include", [])
            checksums = package_data.get("install", {}).get("checksum", {})
            
            if include_files:
                console.print(f"\n[bold green]Installing {len(include_files)} files...[/bold green]")
                
                os.makedirs(package_install_path, exist_ok=True)
                installed_files = []  # Track successfully installed files for rollback
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    file_task = progress.add_task("Installing files...", total=len(include_files))
                    
                    for file in include_files:
                        file_url = f"{repo_url}/packages/{package_name}/{file}"
                        local_file_path = os.path.join(package_install_path, file)
                        
                        # Create directories if needed
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        
                        # Get expected checksum for this file
                        expected_checksum = checksums.get(file)
                        
                        if expected_checksum and not skip_checksum:
                            console.print(f"[dim]  Downloading and verifying {file}...[/dim]")
                        else:
                            console.print(f"[dim]  Downloading {file}...[/dim]")
                        
                        # Download and verify file
                        if self._download_and_verify_file(file_url, local_file_path, expected_checksum, skip_checksum):
                            installed_files.append(local_file_path)
                            progress.advance(file_task)
                        else:
                            # Checksum verification failed - rollback all installed files
                            console.print(f"[red]Installation failed due to checksum verification failure for {file}[/red]")
                            console.print("[yellow]Rolling back installation...[/yellow]")
                            
                            for installed_file in installed_files:
                                try:
                                    if os.path.exists(installed_file):
                                        os.remove(installed_file)
                                except Exception as e:
                                    self.log_verbose(f"Failed to remove {installed_file} during rollback: {e}")
                            
                            # Remove package directory if it was created
                            try:
                                if os.path.exists(package_install_path) and not os.listdir(package_install_path):
                                    os.rmdir(package_install_path)
                            except Exception as e:
                                self.log_verbose(f"Failed to remove package directory during rollback: {e}")
                            
                            raise Exception(f"Checksum verification failed for {file}")
                
                # If we get here, all files were successfully installed and verified
                console.print(f"[green]All files installed and verified successfully[/green]")
            
            # Create bat file if mainfile is specified
            mainfile = package_data.get("install", {}).get("mainfile")
            if mainfile:
                alias = package_data.get("install", {}).get("alias", mainfile.split(".")[0])
                self.log_verbose(f"Creating batch file with alias: {alias}")
                
                # Use original PaxD's bin directory
                original_paxd_bin = os.path.join(self.local_app_data, "com.mralfiem591.paxd", "bin")
                os.makedirs(original_paxd_bin, exist_ok=True)
                bat_file_path = os.path.join(original_paxd_bin, f"{alias}.bat")
                
                if not os.path.exists(bat_file_path):
                    self.log_verbose("Creating new batch file")
                    with open(bat_file_path, 'w') as f:
                        f.write("@echo off\n")
                        f.write(f'"{sys.executable}" "{os.path.join(self.local_app_data, "com.mralfiem591.paxd", "run_pkg.py")}" "{os.path.join(package_install_path, mainfile)}" %*\n')
                    console.print(f"[green]Created batch file: {alias}.bat[/green]")
                else:
                    console.print(f"[red]Batch file conflict detected for alias '{alias}'![/red]")
                    console.print("[yellow]A package already uses this alias. Choose an option:[/yellow]")
                    console.print("  1. Replace existing batch file")
                    console.print("  2. Cancel installation")
                    console.print("  3. Resolve manually (press Enter when done)")
                    
                    choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="2")
                    
                    if choice == "1":
                        with open(bat_file_path, 'w') as f:
                            f.write("@echo off\n")
                            f.write(f'"{sys.executable}" "{os.path.join(self.local_app_data, "com.mralfiem591.paxd", "run_pkg.py")}" "{os.path.join(package_install_path, mainfile)}" %*\n')
                        console.print(f"[yellow]Replaced existing batch file for {alias}[/yellow]")
                    elif choice == "2":
                        console.print("[red]Installation cancelled due to batch file conflict[/red]")
                        # Clean up installed files
                        if os.path.exists(package_install_path):
                            shutil.rmtree(package_install_path)
                        return
                    elif choice == "3":
                        console.print("[yellow]Resolve the conflict manually, then press Enter to continue...[/yellow]")
                        input()
                        with open(bat_file_path, 'w') as f:
                            f.write("@echo off\n")
                            f.write(f'"{sys.executable}" "{os.path.join(self.local_app_data, "com.mralfiem591.paxd", "run_pkg.py")}" "{os.path.join(package_install_path, mainfile)}" %*\n')
                        console.print(f"[green]Created batch file after manual resolution[/green]")
            
            # Save version info
            version_file = os.path.join(package_install_path, ".VERSION")
            with open(version_file, 'w') as f:
                f.write(pkg_info.get('pkg_version', 'Unknown'))
            
            # Mark as user installed
            user_file = os.path.join(package_install_path, ".USER_INSTALLED")
            with open(user_file, 'w') as f:
                f.write("true")
            
            console.print(f"\n[bold green]Successfully installed {pkg_info.get('pkg_name', package_name)} v{pkg_info.get('pkg_version', 'Unknown')}![/bold green]")
            
        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
            raise
    
    def uninstall(self, package_name: str):
        """Uninstall a package with confirmation"""
        # Block uninstallation of original PaxD client
        if package_name == "com.mralfiem591.paxd":
            console.print("[red]Uninstallation of the original PaxD client via PaxD Improved is blocked.[/red]")
            console.print("[yellow]This prevents potential system conflicts and ensures PaxD functionality.[/yellow]")
            console.print("[cyan]Use the 'switchback' command if you need to return to the original client.[/cyan]")
            return
            
        package_install_path = os.path.join(self.local_app_data, package_name)
        
        if not os.path.exists(package_install_path):
            console.print(f"[red]Package '{package_name}' is not installed[/red]")
            return
        
        # Get package info if available
        try:
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            package_data, _ = self._fetch_package_metadata(repo_url, package_name)
            pkg_info = package_data.get('pkg_info', {})
            display_name = pkg_info.get('pkg_name', package_name)
        except:
            display_name = package_name
        
        if not Confirm.ask(f"[red]Are you sure you want to uninstall '{display_name}'?[/red]"):
            console.print("[yellow]Uninstallation cancelled[/yellow]")
            return

        console.print(f"\n[bold red]Uninstalling {display_name}...[/bold red]")
        
        # Get package metadata for bat file cleanup
        try:
            package_data, _ = self._fetch_package_metadata(repo_url, package_name)
            mainfile = package_data.get("install", {}).get("mainfile")
            if mainfile:
                alias = package_data.get("install", {}).get("alias", mainfile.split(".")[0])
                # Remove bat file from original PaxD's bin directory
                original_paxd_bin = os.path.join(self.local_app_data, "com.mralfiem591.paxd", "bin")
                bat_file_path = os.path.join(original_paxd_bin, f"{alias}.bat")
                if os.path.exists(bat_file_path):
                    os.remove(bat_file_path)
                    console.print(f"[yellow]Removed batch file: {alias}.bat[/yellow]")
        except Exception as e:
            self.log_verbose(f"Could not clean up bat file: {e}")
        
        try:
            # Remove package directory
            shutil.rmtree(package_install_path)
            console.print(f"[bold green]Successfully uninstalled {display_name}![/bold green]")
        
        except Exception as e:
            console.print(f"[red]Uninstallation failed: {e}[/red]")
    
    def update(self, package_name: str, force: bool = False, skip_checksum: bool = False):
        """Update a package to the latest version"""
        # Block updates of original PaxD client
        if package_name == "com.mralfiem591.paxd":
            console.print("[red]Updates of the original PaxD client via PaxD Improved are blocked.[/red]")
            console.print("[yellow]This prevents potential conflicts between the two package managers.[/yellow]")
            console.print("[cyan]Use the original PaxD client for self-updates if needed.[/cyan]")
            console.print("[blue]Assuming you want to update com.mralfiem591.paxd-imp, continuing with that...[/blue]")
            package_name = "com.mralfiem591.paxd-imp"
            
        package_install_path = os.path.join(self.local_app_data, package_name)
        
        if not os.path.exists(package_install_path):
            console.print(f"[red]Package '{package_name}' is not installed[/red]")
            return
        
        try:
            # Get current version
            version_file = os.path.join(package_install_path, ".VERSION")
            current_version = "Unknown"
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    current_version = f.read().strip()
            
            # Fetch latest metadata
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            package_data, _ = self._fetch_package_metadata(repo_url, package_name)
            
            pkg_info = package_data.get('pkg_info', {})
            latest_version = pkg_info.get('pkg_version', 'Unknown')
            display_name = pkg_info.get('pkg_name', package_name)
            
            # Version comparison table
            version_table = Table(show_header=True)
            version_table.add_column("Current", style="red")
            version_table.add_column("Latest", style="green")
            version_table.add_row(current_version, latest_version)
            
            console.print(f"\n[bold blue]Checking updates for {display_name}[/bold blue]")
            console.print(version_table)
            
            if current_version == latest_version and not force:
                console.print("[green]Package is already up to date![/green]")
                return
            
            console.print(f"\n[bold yellow]Updating {display_name}...[/bold yellow]")
            
            # Atomic update with backup and restore
            backup_dir = None
            try:
                # Create backup directory
                backup_dir = package_install_path + ".backup"
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.copytree(package_install_path, backup_dir)
                self.log_verbose(f"Created backup at: {backup_dir}")
                
                # Get files and checksums for new version
                include_files = package_data.get("install", {}).get("include", [])
                checksums = package_data.get("install", {}).get("checksum", {})
                
                if include_files:
                    console.print(f"[bold blue]Updating {len(include_files)} files...[/bold blue]")
                    
                    updated_files = []  # Track updated files for rollback
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        console=console
                    ) as progress:
                        file_task = progress.add_task("Updating files...", total=len(include_files))
                        
                        for file in include_files:
                            file_url = f"{repo_url}/packages/{package_name}/{file}"
                            local_file_path = os.path.join(package_install_path, file)
                            
                            # Create directories if needed
                            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                            
                            # Get expected checksum for this file
                            expected_checksum = checksums.get(file)
                            
                            if expected_checksum and not skip_checksum:
                                console.print(f"[dim]  Downloading and verifying {file}...[/dim]")
                            else:
                                console.print(f"[dim]  Downloading {file}...[/dim]")
                            
                            # Download and verify file
                            if self._download_and_verify_file(file_url, local_file_path, expected_checksum, skip_checksum):
                                updated_files.append(local_file_path)
                                progress.advance(file_task)
                            else:
                                # Update failed - restore from backup
                                console.print(f"[red]Update failed due to checksum verification failure for {file}[/red]")
                                console.print("[yellow]Restoring from backup...[/yellow]")
                                
                                # Remove package directory and restore from backup
                                if os.path.exists(package_install_path):
                                    shutil.rmtree(package_install_path)
                                shutil.copytree(backup_dir, package_install_path)
                                
                                # Clean up backup
                                if os.path.exists(backup_dir):
                                    shutil.rmtree(backup_dir)
                                
                                raise Exception(f"Update failed: checksum verification failed for {file}")
                    
                    console.print(f"[green]All files updated and verified successfully[/green]")
                    
                    # Update version file
                    version_file = os.path.join(package_install_path, ".VERSION")
                    with open(version_file, 'w') as f:
                        f.write(latest_version)
                    
                    # Update bat file if mainfile exists
                    mainfile = package_data.get("install", {}).get("mainfile")
                    if mainfile:
                        alias = package_data.get("install", {}).get("alias", mainfile.split(".")[0])
                        # Update bat file in original PaxD's bin directory
                        original_paxd_bin = os.path.join(self.local_app_data, "com.mralfiem591.paxd", "bin")
                        os.makedirs(original_paxd_bin, exist_ok=True)
                        bat_file_path = os.path.join(original_paxd_bin, f"{alias}.bat")
                        
                        with open(bat_file_path, 'w') as f:
                            f.write("@echo off\n")
                            f.write(f'"{sys.executable}" "{os.path.join(self.local_app_data, "com.mralfiem591.paxd", "run_pkg.py")}" "{os.path.join(package_install_path, mainfile)}" %*\n')
                        console.print(f"[green]Updated batch file: {alias}.bat[/green]")
                    
                    # Clean up backup on success
                    if os.path.exists(backup_dir):
                        shutil.rmtree(backup_dir)
                        self.log_verbose("Backup cleaned up after successful update")
                    
                    console.print(f"[bold green]Successfully updated {display_name} to version {latest_version}[/bold green]")
                
            except Exception as update_error:
                # Ensure backup is cleaned up even on error
                if backup_dir and os.path.exists(backup_dir):
                    try:
                        shutil.rmtree(backup_dir)
                    except Exception as cleanup_error:
                        self.log_verbose(f"Failed to clean up backup: {cleanup_error}")
                raise update_error
            
        except Exception as e:
            console.print(f"[red]Update failed: {e}[/red]")
    
    def list_installed(self):
        """List all installed packages in a beautiful table"""
        if not os.path.exists(self.local_app_data):
            console.print("[yellow]No packages installed yet[/yellow]")
            return
        
        packages = []
        for item in os.listdir(self.local_app_data):
            item_path = os.path.join(self.local_app_data, item)
            if os.path.isdir(item_path):
                version_file = os.path.join(item_path, ".VERSION")
                version = "Unknown"
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        version = f.read().strip()
                
                user_installed = os.path.exists(os.path.join(item_path, ".USER_INSTALLED"))
                packages.append((item, version, user_installed))
        
        if not packages:
            console.print("[yellow]No packages installed yet[/yellow]")
            return
        
        # Create beautiful table
        table = Table(title="[bold cyan]Installed Packages[/bold cyan]")
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("Type", style="yellow")
        
        for pkg, version, user_installed in sorted(packages):
            pkg_type = "User" if user_installed else "Dependency"
            table.add_row(pkg, version, pkg_type)
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(packages)} packages installed[/dim]")
    
    def search(self, search_term: str, limit: Optional[int] = None):
        """Search for packages in the repository"""
        console.print(f"\n[bold cyan]Searching for: [yellow]{search_term}[/yellow][/bold cyan]")
        
        try:
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            
            # Fetch search index
            search_url = f"{repo_url}/searchindex.csv"
            response = self._fetch_with_progress(search_url, "Searching packages...")
            
            results = []
            lines = response.text.strip().split('\n')
            
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                
                parts = line.split(',', 4)  # Split into max 5 parts
                if len(parts) >= 5:
                    pkg_id, name, author, version, description = parts
                    
                    # Simple search matching
                    search_lower = search_term.lower()
                    if (search_lower in name.lower() or 
                        search_lower in pkg_id.lower() or 
                        search_lower in description.lower() or
                        search_lower in author.lower()):
                        
                        results.append({
                            'id': pkg_id,
                            'name': name,
                            'author': author,
                            'version': version,
                            'description': description
                        })
            
            if not results:
                console.print("[yellow]No packages found matching your search[/yellow]")
                return
            
            # Limit results if specified
            if limit and len(results) > limit:
                results = results[:limit]
                console.print(f"[dim]Showing first {limit} results[/dim]")
            
            # Display results in a table
            table = Table(title=f"[bold cyan]Search Results for '{search_term}'[/bold cyan]")
            table.add_column("Package", style="cyan")
            table.add_column("Name", style="green", no_wrap=True)
            table.add_column("Author", style="yellow")
            table.add_column("Version", style="blue")
            table.add_column("Description", style="white")
            
            for result in results:
                table.add_row(
                    result['id'],
                    result['name'],
                    result['author'],
                    result['version'],
                    result['description'][:50] + ("..." if len(result['description']) > 50 else "")
                )
            
            console.print(table)
            console.print(f"\n[dim]Found {len(results)} packages[/dim]")
            
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
    
    def info(self, package_name: str):
        """Display detailed package information"""
        console.print(f"\n[bold cyan]Package Information: [yellow]{package_name}[/yellow][/bold cyan]")
        
        try:
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            package_data, source = self._fetch_package_metadata(repo_url, package_name)
            
            pkg_info = package_data.get('pkg_info', {})
            install_info = package_data.get('install', {})
            
            # Check if installed
            package_install_path = os.path.join(self.local_app_data, package_name)
            is_installed = os.path.exists(package_install_path)
            
            installed_version = None
            if is_installed:
                version_file = os.path.join(package_install_path, ".VERSION")
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        installed_version = f.read().strip()
            
            # Create info panel
            info_text = f"""[bold]Name:[/bold] {pkg_info.get('pkg_name', 'Unknown')}
[bold]ID:[/bold] {package_name}
[bold]Author:[/bold] {pkg_info.get('pkg_author', 'Unknown')}
[bold]Version:[/bold] {pkg_info.get('pkg_version', 'Unknown')}
[bold]License:[/bold] {pkg_info.get('pkg_license', 'Unknown')}
[bold]Description:[/bold] {pkg_info.get('pkg_description', 'No description available')}

[bold]Installation Status:[/bold]"""
            
            if is_installed:
                status_color = "green" if installed_version == pkg_info.get('pkg_version') else "yellow"
                info_text += f" [{status_color}]Installed (v{installed_version or 'Unknown'})[/{status_color}]"
            else:
                info_text += " [red]Not installed[/red]"
            
            # Dependencies
            deps = install_info.get('depend', [])
            if deps:
                info_text += f"\n\n[bold]Dependencies:[/bold] {len(deps)}"
                for dep in deps[:5]:  # Show first 5
                    info_text += f"\n  • {dep}"
                if len(deps) > 5:
                    info_text += f"\n  ... and {len(deps) - 5} more"
            
            # Files
            files = install_info.get('include', [])
            if files:
                info_text += f"\n\n[bold]Files included:[/bold] {len(files)}"
                for file in files[:5]:  # Show first 5
                    info_text += f"\n  • {file}"
                if len(files) > 5:
                    info_text += f"\n  ... and {len(files) - 5} more"
            
            package_panel = Panel(
                info_text,
                title=f"[bold green]{pkg_info.get('pkg_name', package_name)}[/bold green]",
                border_style="green",
                padding=(1, 2)
            )
            console.print(package_panel)
            
        except Exception as e:
            console.print(f"[red]Failed to get package info: {e}[/red]")
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        package_install_path = os.path.join(self.local_app_data, package_name)
        return os.path.exists(package_install_path)
    
    def first_time_setup(self):
        """Interactive first-time setup"""
        console.print("\n[bold magenta]Welcome to PaxD Improved![/bold magenta]")
        console.print("Let's get you set up with this beautiful package manager.\n")
        
        # Create directory structure
        os.makedirs(self.local_app_data, exist_ok=True)
        
        # Show repository info
        try:
            repo_url = self._read_repository_url()
            repo_url = self._resolve_repository_url(repo_url)
            console.print(f"[green]Repository configured: [cyan]{repo_url}[/cyan][/green]")
        except:
            console.print("[red]Repository not configured properly[/red]")
            return
        
        console.print("\n[bold green]Setup complete! You're ready to use PaxD Improved.[/bold green]")
        console.print("\n[dim]Try these commands to get started:[/dim]")
        console.print("[dim]  • [cyan]paxd-imp search python[/cyan] - Search for packages[/dim]")
        console.print("[dim]  • [cyan]paxd-imp list[/cyan] - List installed packages[/dim]") 
        console.print("[dim]  • [cyan]paxd-imp info <package>[/cyan] - Get package information[/dim]")
    
    def switchback(self):
        """Switch back to the original PaxD client by updating paxd.bat"""
        console.print("\n[bold yellow]Switching back to original PaxD client...[/bold yellow]")
        
        # Check if original PaxD is installed
        original_paxd_path = os.path.join(self.local_app_data, "com.mralfiem591.paxd")
        if not os.path.exists(original_paxd_path):
            console.print("[red]Original PaxD client not found![/red]")
            console.print("[yellow]Please install the original PaxD client first.[/yellow]")
            return
        
        # Check if paxd.py exists in original installation
        paxd_py_path = os.path.join(original_paxd_path, "paxd.py")
        if not os.path.exists(paxd_py_path):
            console.print("[red]Original PaxD paxd.py not found![/red]")
            console.print(f"[yellow]Expected at: {paxd_py_path}[/yellow]")
            return
        
        # Create/update paxd.bat in original PaxD's bin directory
        bin_dir = os.path.join(original_paxd_path, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bat_file_path = os.path.join(bin_dir, "paxd.bat")
        
        try:
            with open(bat_file_path, 'w') as f:
                f.write("@echo off\n")
                f.write(f'"{sys.executable}" "%LOCALAPPDATA%\\PaxD\\com.mralfiem591.paxd\\paxd.py" %*\n')
            
            console.print(f"[bold green]Successfully created paxd.bat pointing to original client![/bold green]")
            console.print(f"[cyan]Location: {bat_file_path}[/cyan]")
            console.print("\n[yellow]Make sure this directory is in your PATH to use 'paxd' command.[/yellow]")
            console.print("[dim]You can now use 'paxd' to run the original PaxD client.[/dim]")
            
        except Exception as e:
            console.print(f"[red]Failed to create paxd.bat: {e}[/red]")


def create_argument_parser():
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        prog='paxd',
        description='PaxD Improved - Modern Package Manager with Beautiful Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--version', action='version', version=f'PaxD Improved {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install a package')
    install_parser.add_argument('package_name', help='Name of the package to install')
    install_parser.add_argument('--skip-checksum', '-sc', action='store_true', help='Skip checksum verification')
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall a package')
    uninstall_parser.add_argument('package_name', help='Name of the package to uninstall')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update a package')
    update_parser.add_argument('package_name', help='Name of the package to update')
    update_parser.add_argument('--force', '-f', action='store_true', help='Force update')
    update_parser.add_argument('--skip-checksum', '-sc', action='store_true', help='Skip checksum verification')
    
    # List command
    subparsers.add_parser('list', help='List installed packages')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for packages')
    search_parser.add_argument('search_term', help='Term to search for')
    search_parser.add_argument('--limit', '-l', type=int, help='Limit number of results')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show package information')
    info_parser.add_argument('package_name', help='Name of the package')
    
    # Setup command
    subparsers.add_parser('setup', help='Run first-time setup')
    
    # Switchback command
    subparsers.add_parser('switchback', help='Switch back to original PaxD client')
    
    return parser


def main():
    """Main entry point"""

    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create PaxD instance
    paxd = PaxDImproved(verbose=args.verbose)

    if os.path.exists(os.path.join(os.getenv('LOCALAPPDATA', ''), "PaxD", "com.mralfiem591.paxd-imp", ".FIRSTRUN")):
        paxd.first_time_setup()
        os.remove(os.path.join(os.getenv('LOCALAPPDATA', ''), "PaxD", "com.mralfiem591.paxd-imp", ".FIRSTRUN"))

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return
    
    # Show welcome message for major commands
    if args.command in ['install', 'search', 'setup']:
        paxd.show_welcome()
    
    # Execute commands
    try:
        if args.command == 'install':
            paxd.install(args.package_name, skip_checksum=args.skip_checksum)
        
        elif args.command == 'uninstall':
            paxd.uninstall(args.package_name)
        
        elif args.command == 'update':
            paxd.update(args.package_name, force=args.force, skip_checksum=args.skip_checksum)
        
        elif args.command == 'list':
            paxd.list_installed()
        
        elif args.command == 'search':
            paxd.search(args.search_term, limit=args.limit)
        
        elif args.command == 'info':
            paxd.info(args.package_name)
        
        elif args.command == 'setup':
            paxd.first_time_setup()
        
        elif args.command == 'switchback':
            paxd.switchback()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An error occurred: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")

main()