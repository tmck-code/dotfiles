#!/bin/bash

set -euo pipefail

# The .claude tree is routed to Claude Code's config dir so that e.g.
# `CLAUDE_CONFIG_DIR=~/.claude.personal ./deploy.sh osx` installs it there.
# Everything else installs under $HOME.
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR%/}"

# Map a repo-relative path to its install destination.
function dest_for() {
  case "$1" in
    .claude )    echo "$CLAUDE_CONFIG_DIR" ;;
    .claude/* )  echo "${CLAUDE_CONFIG_DIR}/${1#.claude/}" ;;
    * )          echo "$HOME/$1" ;;
  esac
}

function install_homedir() {
  local os=$1
  cd "home/${os}"
  echo "- Installing ${os} dotfiles"

  for i in $(find ./ -maxdepth 1 -type f | cut -c3-); do
    ln -svfn "$PWD/$i" "$(dest_for "$i")"
  done

  for i in $(find . -mindepth 1 -type d | cut -c3-); do
    local dest; dest=$(dest_for "$i")
    echo "-- creating directory $dest"
    mkdir -p "$dest"
    for j in $(find "$i" -maxdepth 1 -type f); do
      ln -svfn "$PWD/$j" "$(dest_for "$j")"
    done
  done
  cd -
}

function install_general() {
  mv -v "$HOME/.bashrc" "$HOME/.bashrc.bak" || echo "- No bashrc, skipping backup!"
  install_homedir general
  install_homedir bin
}

function install_os() {
  local os=$1
  echo "- Installing dotfiles for OS: '${os}'"

  install_homedir "$os"
}

case ${1:-} in
  linux|termux|osx ) install_general ; install_os "$1" ;;
  bin )              install_homedir bin ;;
  wsl )              install_general ; install_os linux ; install_os "$1" ;;
  * )                echo "must choose linux/osx/termux/wsl/bin" ; exit 1;;
esac
