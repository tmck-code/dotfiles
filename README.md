# dotfiles

This is the ragtag collection of my various dotfiles. Use at your peril!

**Dotfiles included:**

  - [X] ~/.tmux_conf
  - [X] ~/.bashrc
  - [X] ~/.bash_aliases
  - [ ] ~/.zshrc
  - [X] ~/.vimrc
  - [X] ~/.gitconfig

## Extras

### Fstab

These are some good options when using a shared partition between Windows &
Linux for a Steam installation

- The uid/gid need to be set to avoid everything being root-owned

```
UUID=XXXXXX /mnt/X/ ntfs defaults,uid=1000,gid=1000,errors=remount-ro 0 0 
```
