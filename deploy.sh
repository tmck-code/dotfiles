#!/bin/bash

set -euxo pipefail

mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc file found! Nothing to back up here"

home_dotfiles=(
  bash_aliases
  bash_profile
  bashrc
  inputrc
  tmux.conf
)

for dotfile in ${home_dotfiles[@]}; do
  ln -svf "$PWD/linux/${dotfile}" "$HOME/.${dotfile}" 
done

ln -svf "$PWD/general/vimrc" "$HOME/.vimrc"
ln -svf "$PWD/general/gitconfig" "$HOME/.gitconfig"

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

