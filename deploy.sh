#!/bin/bash

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "- Must provide an OS as \$1"
  exit 1
fi

OS="${1}"
echo "- Installing dotfiles for OS: '${OS}'"

mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc file found! Nothing to back up here"

general_dotfiles="
gitconfig
rubocop.yml
tmux.conf
vimrc"

linux_dotfiles="
bash_aliases
bash_profile
bashrc
inputrc
tmux.conf"

termux_dotfiles="
bash_aliases"

osx_kitty_dotfiles="
kitty.conf
kitty.light-gruvbox.conf
"

function install_general() {
  echo "- Installing 'general' dotfiles"
  for d in $(echo "${general_dotfiles}"); do
    ln -svf "$(pwd)/general/${d}" "$HOME/.${d}"
  done
}

function install_linux() {
  echo "- Installing linux dotfiles"
  for d in $(echo "${linux_dotfiles}"); do
    ln -svf "$(pwd)/linux/${d}" "$HOME/.${d}"
  done
}

function install_osx() {
  echo "- Installing osx dotfiles"
  for d in $(echo "${osx_dotfiles}"); do
    ln -svf "$(pwd)/osx/${d}" "$HOME/.${d}"
  done
}

function install_termux() {
  echo "- Installing termux dotfiles"
  for d in $(echo "${termux_dotfiles}"); do
    ln -svf "$(pwd)/termux/${d}" "$HOME/.${d}"
  done
}

install_general
install_linux

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

