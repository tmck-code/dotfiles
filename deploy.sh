#!/bin/bash

set -euo pipefail

function install_homedir() {
  local os=$1
  echo "- Installing ${os} dotfiles"
  cd "${os}"
  for i in $(find ./ -maxdepth 1 -type f | cut -c3-); do
    ln -svf "$PWD/$i" "$HOME/"
  done
  for i in $(find -mindepth 2 -type d | cut -c3-); do
    mkdir -p "$HOME/$i"
    echo "creating directory $i"
    for j in $(find $i -type f);
      do ln -svf "$PWD/$j" "$HOME/$i/"
    done
  done
  cd -
}

function install_os() {
  local os=$1
  install_homedir $os
  install_homedir general
  install_homedir bin
}

if [ -z "${1:-}" ]; then
  echo "- Must provide an OS as \$1"
  exit 1
fi

OS="${1}"
echo "- Installing dotfiles for OS: '${OS}'"

mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc file found! Nothing to back up here"

case ${1:-} in
  "linux" )  install_os linux  ;;
  "termux" ) install_os termux ;;
  "osx" )    install_os osx    ;;
  * )        echo "must choose linux/osx/termux" ;;
esac
