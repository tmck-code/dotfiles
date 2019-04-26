#!/bin/bash

set -euxo pipefail

if [ -z "${1:-}" ]; then
  echo "Must provide an OS as \$1"
  exit 1
fi

OS="${1}"

mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc file found! Nothing to back up here"

general_dotfiles=(
  gitconfig
  rubocop.yml
  tmux.conf
  vimrc
)

linux_dotfiles=(
  bash_aliases
  bash_profile
  bashrc
  inputrc
  tmux.conf
)

function install_general() {
  for dotfile in ${general_dotfiles[@]}; do
    ln -svf "$PWD/general/${dotfile}" "$HOME/.${dotfile}" 
  done
}

function install_linux() {
  for dotfile in ${linux_dotfiles[@]}; do
    ln -svf "$PWD/linux/${dotfile}" "$HOME/.${dotfile}" 
  done
}

install_general
install_linux

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

