#!/bin/bash

set -euo pipefail

function install_homedir() {
  local os=$1
  cd "${os}"
  echo -e "\n- Installing ${os} dotfiles"

  for i in $(find ./ -maxdepth 1 -type f | cut -c3-); do
    ln -svf "$PWD/$i" "$HOME/"
  done

  for i in $(find . -mindepth 1 -type d | cut -c3-); do
    echo "-- creating directory $i"
    mkdir -p "$HOME/$i"
    for j in $(find $i -type f); do
      ln -svf "$PWD/$j" "$HOME/$i/"
    done
  done
  cd -
}

function install_os() {
  local os=$1
  echo "- Installing dotfiles for OS: '${os}'"

  mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc, skipping backup!"
  install_homedir general
  install_homedir $os
  install_homedir bin
}

case ${1:-} in
  linux|termux|osx ) install_os $1 ;;
  wsl )              install_os linux ; install_os $1 ;;
  * )                echo "must choose linux/osx/termux" ; exit 1;;
esac
